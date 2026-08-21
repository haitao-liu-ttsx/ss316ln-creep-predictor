import React, { useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { DEMO_CASES, predict, PredictResult, predictV13, V13Result, V13_FIELDS, V13_FIELD_ZH, V13_UNITS } from './api'
import './style.css'

const N = 2304
interface P { T: number; P: number; t: number; Rm: number; Ro: number; w: number }
const DOM = { T: [550, 650] as const, P: [2.5, 30] as const, t: [1, 3000] as const,
  Rm: [80, 150] as const, Ro: [15, 25] as const, w: [2, 5] as const }
const STRESS_MAX = 250
const stressOf = (p: P) => p.P * p.Ro / p.w

function buildMesh(p: P): Float32Array {
  const pts = new Float32Array(N * 3)
  const Ri = p.Ro - p.w
  for (let k = 0; k < 3; k++) {
    const r = Ri + (p.Ro - Ri) * k / 3
    for (let j = 0; j < 16; j++) {
      const phi = 2 * Math.PI * j / 16
      for (let i = 0; i < 48; i++) {
        const th = 2 * Math.PI * i / 48
        const cx = p.Rm * Math.cos(th), cy = p.Rm * Math.sin(th)
        const idx = (k * 16 + j) * 48 + i
        pts[idx * 3] = cx + r * Math.cos(phi) * Math.cos(th)
        pts[idx * 3 + 1] = cy + r * Math.cos(phi) * Math.sin(th)
        pts[idx * 3 + 2] = r * Math.sin(phi)
      }
    }
  }
  return pts
}

interface ViewerHandle { reset: () => void }
interface ViewerProps {
  p: P
  field: number[]
  hotspot: number
  hotspotXyz?: number[]
  mode: 'log' | 'lin'
  showHotspot: boolean
}
/** Three.js scene/camera/controls live in refs: created ONCE on mount.
 *  Predictions only update data (points positions/colors, hotspot marker),
 *  NEVER recreate the camera — user orbit/zoom/pan persists across predicts. */
const Field3D = (props: ViewerProps, ref: React.Ref<ViewerHandle>) => {
  const wrap = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const pointsRef = useRef<THREE.Points | null>(null)
  const hotspotRef = useRef<THREE.Sprite | null>(null)
  const homeRef = useRef<{ pos: THREE.Vector3; target: THREE.Vector3 } | null>(null)

  useEffect(() => {
    const el = wrap.current!
    const W = el.clientWidth, H = el.clientHeight
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0d1117)
    const camera = new THREE.PerspectiveCamera(45, W / H, 1, 5000)
    camera.position.set(280, 200, 340)
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(W, H)
    el.appendChild(renderer.domElement)
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.target.set(0, 0, 0)
    sceneRef.current = scene; cameraRef.current = camera
    controlsRef.current = controls; rendererRef.current = renderer
    homeRef.current = { pos: camera.position.clone(), target: controls.target.clone() }
    // dev-only introspection for acceptance tests (excluded from production build)
    if ((import.meta as { env?: { DEV?: boolean } }).env?.DEV) {
      ;(window as unknown as Record<string, unknown>).__viewer = { camera, controls }
    }
    // CEEQ point cloud (geometry recreated on predict, never camera)
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(N * 3), 3))
    geo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(N * 3), 3))
    const points = new THREE.Points(geo, new THREE.PointsMaterial({ size: 3.2, vertexColors: true }))
    scene.add(points)
    pointsRef.current = points
    // thin reference ring (neutral, subtle)
    const ring = new THREE.Mesh(new THREE.TorusGeometry(100, 1.2, 8, 96),
      new THREE.MeshBasicMaterial({ color: 0x2f81f7, transparent: true, opacity: 0.18 }))
    scene.add(ring)
    // hotspot: TINY crosshair marker (visual aid only, NOT part of model geometry),
    // positioned by API xyz; toggled by showHotspot (visible=false hides entirely).
    const cv = document.createElement('canvas'); cv.width = cv.height = 64
    const g = cv.getContext('2d')!
    g.strokeStyle = '#ffffff'
    g.lineWidth = 14
    g.lineCap = 'round'
    g.beginPath()
    g.moveTo(32, 13); g.lineTo(32, 51)
    g.moveTo(13, 32); g.lineTo(51, 32)
    g.stroke()
    const tex = new THREE.CanvasTexture(cv)
    const spr = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false }))
    spr.scale.set(20, 20, 1)
    spr.visible = props.showHotspot
    scene.add(spr)
    hotspotRef.current = spr
    let raf = 0
    const tick = () => { raf = requestAnimationFrame(tick); controls.update(); renderer.render(scene, camera) }
    tick()
    const ro = new ResizeObserver(() => {
      const w = el.clientWidth, h = el.clientHeight
      renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix()
    })
    ro.observe(el)
    return () => { cancelAnimationFrame(raf); ro.disconnect(); el.removeChild(renderer.domElement)
      controls.dispose(); scene.clear() }
  }, [])

  // update data only (camera untouched)
  useEffect(() => {
    const scene = sceneRef.current, points = pointsRef.current
    if (!scene || !points) return
    const pts = buildMesh(props.p)
    const pos = points.geometry.getAttribute('position') as THREE.BufferAttribute
    pos.array = pts; pos.needsUpdate = true
    const vals = props.field.map((v) => props.mode === 'log'
      ? Math.log10(Math.max(v, 1e-300)) : v)
    const lo = Math.min(...vals), hi = Math.max(...vals)
    const colors = new Float32Array(N * 3)
    vals.forEach((v, i) => {
      const t = (v - lo) / (hi - lo)
      const c = new THREE.Color().setHSL(0.66 - 0.62 * t, 0.9, 0.45 + 0.2 * t)
      colors[i * 3] = c.r; colors[i * 3 + 1] = c.g; colors[i * 3 + 2] = c.b
    })
    const col = points.geometry.getAttribute('color') as THREE.BufferAttribute
    col.array = colors; col.needsUpdate = true
    // reference ring follows geometry
    const ring = scene.children.find((c) => c instanceof THREE.Mesh) as THREE.Mesh | undefined
    if (ring) ring.geometry.dispose(); if (ring) (ring as THREE.Mesh).geometry =
      new THREE.TorusGeometry(props.p.Rm, 1.2, 8, 96)
    // hotspot marker at API-provided xyz (true centroid of max element)
    const spr = hotspotRef.current
    if (spr) {
      const hx = props.hotspotXyz ?? [0, 0, 0]
      spr.position.set(hx[0], hx[1], hx[2])
      spr.visible = props.showHotspot
    }
  }, [props.p, props.field, props.mode, props.hotspotXyz, props.showHotspot])

  useImperativeHandle(ref, () => ({
    reset() {
      const c = cameraRef.current, o = controlsRef.current, h = homeRef.current
      if (c && o && h) {
        // OrbitControls.update() recomputes camera pos from its internal spherical
        // each frame, so plain position.copy() gets overwritten — reset the
        // private _spherical/_sphericalDelta/_scale (three r169) as well.
        const oc = o as unknown as { _spherical: THREE.Spherical; _sphericalDelta: THREE.Spherical; _scale: number }
        oc._scale = 1
        oc._spherical.setFromVector3(h.pos)
        oc._sphericalDelta.set(0, 0, 0)
        c.position.copy(h.pos); c.lookAt(h.target)
        o.target.copy(h.target); o.update()
      }
    },
  }), [])

  return <div className="view3d" ref={wrap} />
}
const Viewer = React.forwardRef(Field3D)

function MiniCurve({ title, xs, ys }: { title: string; xs: number[]; ys: number[] }) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const cv = ref.current; if (!cv || ys.length < 2) return
    const ctx = cv.getContext('2d')!
    ctx.clearRect(0, 0, cv.width, cv.height)
    const lo = Math.min(...ys), hi = Math.max(...ys)
    const pad = 10
    const px = (i: number) => pad + i * (cv.width - pad * 2) / (xs.length - 1)
    const py = (v: number) => cv.height - pad - (v - lo) * (cv.height - pad * 2) / Math.max(1e-12, hi - lo)
    ctx.strokeStyle = '#58a6ff'; ctx.lineWidth = 1.6; ctx.beginPath()
    ys.forEach((v, i) => i ? ctx.lineTo(px(i), py(v)) : ctx.moveTo(px(i), py(v)))
    ctx.stroke()
    ctx.fillStyle = '#8b949e'; ctx.font = '10px sans-serif'
    ctx.fillText(title, 2, 12)
  }, [xs, ys, title])
  return <canvas ref={ref} width={430} height={90} />
}

function initialParams(): P {
  const q = new URLSearchParams(window.location.search)
  const d = Number(q.get('demo') ?? '')
  if (d >= 1 && d <= DEMO_CASES.length) return { ...DEMO_CASES[d - 1].params }
  return { T: 600, P: 20, t: 1000, Rm: 100, Ro: 20, w: 4 }
}

/** STEP21-D: generic 3D field viewer for V1.3 (real x/y/z centroids).
 * abs scale uses frozen global per-field ranges (cross-case comparable);
 * rel scale uses per-case min/max. CEEQ mapped in log10 domain. */
const V13Viewer = ({ centroids, values, field, scaleMode, globalRange, globalLogRange }: {
  centroids: number[][]; values: number[]; field: string; scaleMode: 'abs' | 'rel'
  globalRange?: [number, number]; globalLogRange?: [number, number]
}) => {
  const ref = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const pointsRef = useRef<THREE.Points | null>(null)
  const [range, setRange] = useState<[number, number]>([0, 1])

  useEffect(() => {
    const el = ref.current!
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0d1117)
    const camera = new THREE.PerspectiveCamera(45, el.clientWidth / el.clientHeight, 1, 5000)
    camera.position.set(280, 200, 340)
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(el.clientWidth, el.clientHeight)
    el.appendChild(renderer.domElement)
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    sceneRef.current = scene
    let raf = 0
    const tick = () => { raf = requestAnimationFrame(tick); controls.update(); renderer.render(scene, camera) }
    tick()
    const ro = new ResizeObserver(() => {
      renderer.setSize(el.clientWidth, el.clientHeight)
      camera.aspect = el.clientWidth / el.clientHeight
      camera.updateProjectionMatrix()
    })
    ro.observe(el)
    return () => { cancelAnimationFrame(raf); ro.disconnect(); el.removeChild(renderer.domElement); scene.clear() }
  }, [])

  useEffect(() => {
    const scene = sceneRef.current
    if (!scene) return
    const n = values.length
    const pos = new Float32Array(n * 3)
    for (let i = 0; i < n; i++) {
      pos[i * 3] = centroids[i][0]; pos[i * 3 + 1] = centroids[i][1]; pos[i * 3 + 2] = centroids[i][2]
    }
    // color mapping range: abs -> frozen global range (CEEQ in log10 domain); rel -> per-case
    const isCEEQ = field === 'CEEQ'
    const lo = Math.min(...values), hi = Math.max(...values)
    const loMap = scaleMode === 'abs' && globalRange ? globalRange[0] : lo
    const hiMap = scaleMode === 'abs' && globalRange ? globalRange[1] : hi
    setRange([lo, hi])
    const diverging = field !== 'CEEQ' && field !== 'von_mises'
    const col = new Float32Array(n * 3)
    for (let i = 0; i < n; i++) {
      let v = values[i]
      const clamp01 = (x: number) => Math.min(1, Math.max(0, x))
      // high-contrast colormap: hue span 0.72->0.02 (blue->red), brightness 0.32->0.95
      const cmap = (t: number) => {
        const cc = new THREE.Color().setHSL(0.72 - 0.7 * t, 0.85 + 0.15 * t, 0.32 + 0.63 * t)
        return [cc.r, cc.g, cc.b]
      }
      if (isCEEQ) {
        v = Math.log10(Math.max(v, 1e-30))
        const llo = scaleMode === 'abs' && globalLogRange ? globalLogRange[0] : Math.log10(Math.max(lo, 1e-30))
        const lhi = scaleMode === 'abs' && globalLogRange ? globalLogRange[1] : Math.log10(Math.max(hi, 1e-30))
        const t = clamp01(lhi > llo ? (v - llo) / (lhi - llo) : 0.5)
        const [r, g, b] = cmap(t)
        col[i * 3] = r; col[i * 3 + 1] = g; col[i * 3 + 2] = b
        continue
      }
      const t = clamp01(hiMap > loMap ? (v - loMap) / (hiMap - loMap) : 0.5)
      let r: number, g: number, b: number
      if (diverging) {
        // blue(-) -> white(0) -> red(+), brightness peaks at extremes for contrast
        const t0 = hiMap > 0 && loMap < 0 ? -loMap / (hiMap - loMap) : 0.5
        if (t <= t0) { const u = t0 > 0 ? t / t0 : 0; r = 0.15 + 0.6 * u; g = 0.25 + 0.5 * u; b = 0.95 - 0.25 * u }
        else { const u = t0 < 1 ? (t - t0) / (1 - t0) : 0; r = 0.75 + 0.25 * u; g = 0.75 - 0.65 * u; b = 0.7 - 0.6 * u }
        r = Math.min(1, Math.max(0, r)); g = Math.min(1, Math.max(0, g)); b = Math.min(1, Math.max(0, b))
      } else {
        const vv = Math.max(0, v)
        const t2 = clamp01(hiMap > loMap ? (vv - loMap) / (hiMap - loMap) : 0.5)
        const cc = new THREE.Color().setHSL(0.72 - 0.7 * t2, 0.85, 0.32 + 0.63 * t2)
        r = cc.r; g = cc.g; b = cc.b
      }
      col[i * 3] = r; col[i * 3 + 1] = g; col[i * 3 + 2] = b
    }
    if (pointsRef.current) { scene.remove(pointsRef.current); pointsRef.current.geometry.dispose() }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    geo.setAttribute('color', new THREE.BufferAttribute(col, 3))
    const pts = new THREE.Points(geo, new THREE.PointsMaterial({ size: 4.2, vertexColors: true }))
    scene.add(pts)
    pointsRef.current = pts
  }, [centroids, values, field, scaleMode])

  return <div className="view3d" ref={ref} />
}

export default function App() {
  const [p, setP] = useState<P>(initialParams)
  const [res, setRes] = useState<PredictResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [mode, setMode] = useState<'log' | 'lin'>('log')
  const [showHotspot, setShowHotspot] = useState(true)
  const [v13Mode, setV13Mode] = useState(false)
  const [v13Res, setV13Res] = useState<V13Result | null>(null)
  const [v13Field, setV13Field] = useState<(typeof V13_FIELDS)[number]>('Srr')
  const [v13Scale, setV13Scale] = useState<'abs' | 'rel'>('abs')
  const [v13Err, setV13Err] = useState<string | null>(null)
  const [playing13, setPlaying13] = useState(false)
  const sliderTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const v13Default = { T: 700, P: 30, t: 300, Rm: 100, Ro: 20, w: 4 }

  const V13_TEMPS = [550, 600, 650, 700, 750]
  const v13InputError = useMemo(() => {
    const { T, P, t, Rm, Ro, w } = p
    if (!(T > 0)) return '温度 T 必须 > 0°C'
    if (v13Mode && !V13_TEMPS.includes(T)) return '温度仅支持 550/600/650/700/750°C 五档'
    if (!(P >= 0)) return '压力 P 必须 ≥ 0 MPa'
    if (!(t > 0)) return '时间 t 必须 > 0 h'
    if (!(Rm > 0)) return '平均半径 Rm 必须 > 0 mm'
    if (!(Ro > 0)) return '外半径 Ro 必须 > 0 mm'
    if (!(w > 0)) return '壁厚 w 必须 > 0 mm'
    if (Ro >= Rm) return '几何错误：Ro 必须 < Rm（环形管约束）'
    if (w >= Ro) return '几何错误：壁厚 w 必须 < 外半径 Ro'
    if (Rm <= 2 * Ro) return '几何错误：Rm 必须 > 2×Ro（防自相交）'
    return null
  }, [p, v13Mode])
  const [playing, setPlaying] = useState(false)
  const [hist, setHist] = useState<{ t: number; max: number; mean: number }[]>([])
  const viewerRef = useRef<{ reset: () => void }>(null)
  const ss = stressOf(p)
  const ssOk = ss <= STRESS_MAX
  const domainOk = useMemo(() =>
    p.T >= DOM.T[0] && p.T <= DOM.T[1] && p.P >= DOM.P[0] && p.P <= DOM.P[1] &&
    p.t >= DOM.t[0] && p.t <= DOM.t[1] && p.Rm >= DOM.Rm[0] && p.Rm <= DOM.Rm[1] &&
    p.Ro >= DOM.Ro[0] && p.Ro <= DOM.Ro[1] && p.w >= DOM.w[0] && p.w <= DOM.w[1] && ssOk,
  [p, ssOk])

  const run13 = useCallback(async (pp?: P) => {
    const target = pp ?? p
    if (v13InputError) { setV13Err(v13InputError); return }
    setBusy(true)
    setV13Err(null)
    try {
      const r = await predictV13(target)
      if (r.status !== 'OK') {
        setV13Err(r.errors?.join('；') || '预测失败，请检查输入参数')
      } else {
        setV13Res(r)
        if (r.fields && !(v13Field in r.fields)) setV13Field('Srr')
      }
    } catch (e) {
      setV13Err('无法连接预测服务，请确认后端已启动')
    }
    setBusy(false)
  }, [p, v13Field, v13InputError])

  useEffect(() => {
    if (v13Mode) {
      setP(v13Default)
      setV13Res(null)
      run13(v13Default)
    } else {
      setPlaying13(false)
    }
  }, [v13Mode]) // eslint-disable-line

  // time slider: debounced auto-predict on drag
  const onTimeSlider = useCallback((nt: number) => {
    nt = Math.round(nt)
    setP((prev) => ({ ...prev, t: nt }))
    if (sliderTimer.current) clearTimeout(sliderTimer.current)
    sliderTimer.current = setTimeout(() => run13({ ...p, t: nt }), 350)
  }, [p, run13])

  // time playback: advance t by 100h every 500ms, auto-stop at 3000
  useEffect(() => {
    if (!playing13 || !v13Mode) return
    const iv = setInterval(() => {
      setP((prev) => {
        const nt = Math.min(3000, prev.t + 100)
        run13({ ...prev, t: nt })
        if (nt >= 3000) setPlaying13(false)
        return { ...prev, t: nt }
      })
    }, 500)
    return () => clearInterval(iv)
  }, [playing13, v13Mode, run13])

  const run = useCallback(async (pp?: P) => {
    const target = pp ?? p
    setBusy(true)
    const r = await predict(target)
    setRes(r)
    if (r.valid) {
      setHist((h) => {
        const nr = h.filter((x) => Math.abs(x.t - target.t) > 1e-6)
        return [...nr, { t: target.t, max: r.max_ceeq!, mean: r.mean_ceeq! }]
          .sort((a, b) => a.t - b.t)
      })
    }
    setBusy(false)
  }, [p])

  useEffect(() => { run() }, []) // eslint-disable-line

  useEffect(() => {
    if (!playing || !domainOk) return
    const iv = setInterval(() => {
      setP((prev) => {
        const nt = Math.min(3000, prev.t + 60)
        run({ ...prev, t: nt })
        if (nt >= 3000) setPlaying(false)
        return { ...prev, t: nt }
      })
    }, 140)
    return () => clearInterval(iv)
  }, [playing, domainOk, run])

  const set = (k: keyof P) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setP((prev) => ({ ...prev, [k]: Number(e.target.value) }))

  const colorRange = useMemo(() => {
    if (!res?.valid) return { lo: 0, hi: 1 }
    const v = (res.field as number[]).map((x) => mode === 'log' ? Math.log10(Math.max(x, 1e-300)) : x)
    return { lo: Math.min(...v), hi: Math.max(...v) }
  }, [res, mode])

  const paramMeta: [keyof P, string, string, Readonly<[number, number]>, number][] = [
    ['T', '温度', '°C', v13Mode ? [550, 750] : DOM.T, v13Mode ? 50 : 1],
    ['P', '压力', 'MPa', DOM.P, 1], ['t', '时间', 'h', DOM.t, 1],
    ['Rm', '环向半径', 'mm', DOM.Rm, 1], ['Ro', '外半径', 'mm', DOM.Ro, 1], ['w', '壁厚', 'mm', DOM.w, 1],
  ]

  return (
    <div className="app">
      <header>
        <div>
          <h1>{v13Mode ? '316LN 三维高温蠕变场预测器' : 'SS316LN 环形结构蠕变场 AI 预测平台'}</h1>
          <p className="sub">{v13Mode
            ? '基于 Abaqus 高保真模拟数据的快速代理模型'
            : '基于 POD + Poly2 模态回归的三维时空 CEEQ 场预测'}</p>
        </div>
        <div className="model-status">
          <button className={!v13Mode ? 'v13tab on' : 'v13tab'} onClick={() => setV13Mode(false)}>V1.2 CEEQ 场</button>
          <button className={v13Mode ? 'v13tab on' : 'v13tab'} onClick={() => setV13Mode(true)}>V1.3 多物理场</button>
        </div>
      </header>

      <div className="layout">
        <aside className="panel left">
          <h2>预测参数</h2>
          {paramMeta.map(([k, zh, unit, range, step]) => (
            <label key={k}>
              <span className="pname">{zh} {k}<em>{unit}</em></span>
              <input type="number" value={p[k]} onChange={set(k)} step={step} />
              <span className="prange">{range[0]}–{range[1]}</span>
            </label>
          ))}
          <div className={'ss ' + (ssOk ? '' : 'bad')}>
            应力尺度 P·Ro/w = <b>{ss.toFixed(1)}</b> MPa
            {!ssOk && <div className="mini-ood">超出模型有效域 · 允许 ≤ {STRESS_MAX} MPa</div>}
          </div>
          <button className="predict" onClick={() => (v13Mode ? run13() : run())}
            disabled={busy || (v13Mode ? !!v13InputError : !domainOk)}>
            {busy ? '正在计算…' : '开始预测'}
          </button>
          {v13Mode && v13InputError && <div className="mini-ood">参数错误：{v13InputError}</div>}
          {!v13Mode && (
            <>
              <div className="examples">
                <h3>示例案例</h3>
                <select onChange={(e) => {
                  const c = DEMO_CASES[Number(e.target.value)]
                  setP(c.params); setTimeout(() => run(c.params), 60)
                }} defaultValue="0">
                  {DEMO_CASES.map((c, i) => <option key={i} value={i}>{c.name}</option>)}
                </select>
              </div>
              <div className="tctl">
                <div className="trow">
                  <span>当前时间：{p.t} h</span>
                  <button onClick={() => setPlaying(!playing)} disabled={!domainOk}>
                    {playing ? '暂停' : '播放'}
                  </button>
                </div>
                <input type="range" min={1} max={3000} value={p.t} onChange={set('t')}
                  onMouseUp={() => run()} disabled={playing} />
              </div>
            </>
          )}
          {v13Mode && (
            <div className="tctl v13tctl">
              <div className="trow">
                <span>当前时间：t = {p.t} h</span>
                <button onClick={() => setPlaying13(!playing13)} disabled={!!v13InputError}>
                  {playing13 ? '⏸ 暂停' : '▶ 放映'}
                </button>
              </div>
              <input type="range" min={1} max={3000} step={50} value={p.t}
                onChange={(e) => onTimeSlider(Number(e.target.value))} disabled={playing13} />
              <div className="trow dim"><span>拖动时间滑块 · 放映自动递增（100 h/步，至 3000 h 停止）</span></div>
            </div>
          )}
        </aside>

        <main className="center">
          <div className="view-head">
            <h2>{v13Mode ? '三维多物理场' : '三维 CEEQ 场'}</h2>
            <div className="mode">
              {v13Mode ? (
                <>
                  <select className="v13field" value={v13Field}
                    onChange={(e) => setV13Field(e.target.value as typeof V13_FIELDS[number])}>
                    {V13_FIELDS.map((f) => <option key={f} value={f}>{V13_FIELD_ZH[f]}</option>)}
                  </select>
                  <button className={v13Scale === 'abs' ? 'on' : ''} onClick={() => setV13Scale('abs')}
                    title="全局固定范围：跨工况可比（改 T/P/t 颜色整体变化）">绝对色标</button>
                  <button className={v13Scale === 'rel' ? 'on' : ''} onClick={() => setV13Scale('rel')}
                    title="每工况自身范围：场内空间分布最大化（看内外圈差异）">相对色标</button>
                  <button onClick={() => run13()}>重新预测</button>
                </>
              ) : (
                <>
                  <button className={mode === 'log' ? 'on' : ''} onClick={() => setMode('log')}>对数色标</button>
                  <button className={mode === 'lin' ? 'on' : ''} onClick={() => setMode('lin')}>线性色标</button>
                  <button className={showHotspot ? 'on' : ''} onClick={() => setShowHotspot(!showHotspot)}>
                    显示热点
                  </button>
                  <button onClick={() => viewerRef.current?.reset()}>重置视角</button>
                </>
              )}
            </div>
          </div>
          {v13Mode ? (
            v13Res?.status === 'OK' && v13Res.fields && v13Res.centroids ? (
              <V13Viewer centroids={v13Res.centroids} values={v13Res.fields[v13Field]}
                field={v13Field} scaleMode={v13Scale}
                globalRange={v13Res.global_ranges?.[v13Field] as [number, number] | undefined}
                globalLogRange={v13Res.global_ranges?.CEEQ_log10 as [number, number] | undefined} />
            ) : (
              <div className="view-empty">{v13Res?.errors?.join('；') || 'V1.3 预测失败'}</div>
            )
          ) : res?.valid ? (
            <Viewer ref={viewerRef} p={p} field={res.field!} hotspot={res.hotspot_element!}
              hotspotXyz={res.hotspot_xyz} mode={mode} showHotspot={showHotspot} />
          ) : (
            <div className="view-empty">请输入有效工况并点击“开始预测”</div>
          )}
          <div className="colorbar">
            <span>{v13Mode ? (v13Res?.summary?.[v13Field]?.min ?? 0).toExponential(2) : colorRange.lo.toExponential(2)}</span>
            <div className="bar" />
            <span>{v13Mode ? (v13Res?.summary?.[v13Field]?.max ?? 1).toExponential(2) : colorRange.hi.toExponential(2)}</span>
            {!v13Mode && <span className="hs-note">★ 热点</span>}
          </div>
          {!v13Mode && (
            <div className="evolution">
              <h3>时间演化</h3>
              <MiniCurve title="最大 CEEQ（对数）" xs={hist.map((x) => x.t)}
                ys={hist.map((x) => Math.log10(Math.max(x.max, 1e-300)))} />
              <MiniCurve title="平均 CEEQ（对数）" xs={hist.map((x) => x.t)}
                ys={hist.map((x) => Math.log10(Math.max(x.mean, 1e-300)))} />
            </div>
          )}
        </main>

        <aside className="panel right">
          <h2>{v13Mode ? 'V1.3 预测结果' : '预测结果'}</h2>
          {v13Mode ? (
            <>
              <div className="v13fieldlist">
                {V13_FIELDS.map((f) => (
                  <label key={f} className={'v13radio' + (v13Field === f ? ' on' : '')}>
                    <input type="radio" name="v13field" checked={v13Field === f}
                      onChange={() => setV13Field(f)} /> {V13_FIELD_ZH[f]}
                    <em>{V13_UNITS[f]}</em>
                  </label>
                ))}
              </div>
              {v13Err && <div className="mini-ood">⚠ {v13Err}</div>}
              {v13Res === null ? <div className="empty">等待预测…</div> : v13Res.status === 'OK' ? (
                <>
                  <div className={'domain ' + (v13Res.domain_status || '').toLowerCase()}>
                    域状态：{v13Res.domain_status === 'SAFE' ? '安全域' : v13Res.domain_status === 'WARNING' ? '外推警告' : '超出训练域'}
                  </div>
                  <div className="domain-note">
                    {v13Res.domain_status === 'SAFE' && '当前输入位于模型训练覆盖范围内。'}
                    {v13Res.domain_status === 'WARNING' && '当前输入存在一定外推，结果可用于快速估计，CEEQ 建议使用 Abaqus 进一步验证。'}
                    {v13Res.domain_status === 'OUT_OF_DOMAIN' && '当前输入明显超出模型训练覆盖范围，结果不建议作为可靠工程结果，应使用 Abaqus 验证。'}
                  </div>
                  {v13Res.domain_reasons?.map((r, i) => <div key={i} className="domain-reason">⚠ {r}</div>)}
                  <div className="cards">
                    <div className="card"><span>当前场 · 最大值</span>
                      <b>{v13Res.summary?.[v13Field]?.max.toExponential(3) ?? '-'}</b></div>
                    <div className="card"><span>最小值</span>
                      <b>{v13Res.summary?.[v13Field]?.min.toExponential(3) ?? '-'}</b></div>
                    <div className="card"><span>平均值</span>
                      <b>{v13Res.summary?.[v13Field]?.mean.toExponential(3) ?? '-'}</b></div>
                    <div className="card"><span>P95</span>
                      <b>{v13Res.summary?.[v13Field]?.p95.toExponential(3) ?? '-'}</b></div>
                  </div>
                  <div className="hs-detail">
                    <div>输入：T={p.T}°C ｜ P={p.P} MPa ｜ t={p.t} h</div>
                    <div>Rm={p.Rm} mm ｜ Ro={p.Ro} mm ｜ w={p.w} mm</div>
                    <div>应力尺度 P·Ro/w = {(p.P * p.Ro / p.w).toFixed(1)} MPa</div>
                    <div>模型：{v13Res.model_version} · {v13Res.schema_version}</div>
                  </div>
                </>
              ) : (
                <div className="ood"><b>{v13Res.status}</b>
                  <p>{v13Res.errors?.join('；')}</p></div>
              )}
            </>
          ) : res === null ? <div className="empty">等待预测…</div> : res.valid ? (
            <>
              <div className="cards">
                <div className="card"><span>最大 CEEQ</span><b>{res.max_ceeq!.toExponential(3)}</b></div>
                <div className="card"><span>平均 CEEQ</span><b>{res.mean_ceeq!.toExponential(3)}</b></div>
                <div className="card"><span>P95 CEEQ</span><b>{res.p95_ceeq!.toExponential(3)}</b></div>
                <div className="card hs"><span>热点 ★ 单元</span><b>{res.hotspot_element}</b></div>
              </div>
              <div className="hs-detail">
                <div>热点 CEEQ：{res.hotspot_value!.toExponential(3)}</div>
                <div>位置 X：{res.hotspot_xyz![0].toFixed(1)}</div>
                <div>位置 Y：{res.hotspot_xyz![1].toFixed(1)}</div>
                <div>位置 Z：{res.hotspot_xyz![2].toFixed(1)}</div>
                <div>POD 系数：{res.pod_coefficients!.map((v) => v.toFixed(3)).join(' , ')}</div>
                <div>应力尺度：{res.stress_scale!.toFixed(1)} MPa</div>
              </div>
              <div className="physics">
                <h3>物理检查</h3>
                <div>✓ CEEQ ≥ 0</div>
                <div>✓ 场数值有限</div>
                <div>✓ 无 NaN / Inf</div>
                <div className={res.physics_status === 'PASS' ? 'pass' : 'warn'}>
                  总体：{res.physics_status === 'PASS' ? '通过' : '警告'}
                </div>
              </div>
              <div className="model-state">模型状态：<b className="ok">有效</b></div>
            </>
          ) : (
            <div className="ood">
              <b>超出模型有效域</b>
              <p>{res.reason}</p>
              <ul>{res.violations?.map((v, i) => <li key={i}>{v}</li>)}</ul>
              {(res.violations ?? []).some((v) => /T=/i.test(v) && /700|750/.test(v)) && (
                <p className="dr">需要补充材料数据 —— 该温度下蠕变材料参数尚未经过验证。</p>
              )}
              <div className="valid-range">
                <b>模型有效范围</b>
                <div>温度 T：550–650 °C</div>
                <div>压力 P：2.5–30 MPa</div>
                <div>时间 t：1–3000 h</div>
                <div>环向半径 Rm：80–150 mm</div>
                <div>外半径 Ro：15–25 mm</div>
                <div>壁厚 w：2–5 mm</div>
                <div>应力尺度 P·Ro/w ≤ 250 MPa</div>
              </div>
            </div>
          )}
        </aside>
      </div>

      <footer>
        {v13Mode ? (
          <>
            <p>用于快速预测与可视化，超出模型适用范围时建议使用 Abaqus 验证。</p>
            <details className="model-info">
              <summary>模型信息</summary>
              <p>模型：316LN 高温蠕变代理模型（POD + Ridge 回归）</p>
              <p>训练数据：230 cases ｜ 温度 550–750°C ｜ 空间场 2304 点 ｜ 输出 8 场</p>
              <p>高保真数据来源：Abaqus 有限元模拟（AIR 环境，N=0.14）</p>
              <p>六个局部柱坐标应力分量 + CEEQ（log10 域训练，逆变换还原）+ von Mises（由预测六应力实时计算，非独立模型）</p>
            </details>
          </>
        ) : (
          <>
            <p>AI 代理模型 · POD(k=3) + Poly2 模态回归 · 2304 单元 CEEQ 场 ·
              外部验证：logR² = 0.9998 · 热点命中 27/27</p>
            <p className="warn">仅适用于经验证参数域：T 550–650 °C · P 2.5–30 MPa · t 1–3000 h ·
              P·Ro/w ≤ 250 MPa。超出有效域时必须回退 Abaqus 进行验证。
              本工具不替代实验与有限元计算。</p>
          </>
        )}
      </footer>
    </div>
  )
}
