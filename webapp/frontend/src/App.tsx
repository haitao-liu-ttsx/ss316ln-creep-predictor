import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { predictV13, V13Result, V13_FIELDS, V13_FIELD_ZH, V13_UNITS } from './api'
import './style.css'

const V13_TEMPS = [550, 600, 650, 700, 750]
const DEFAULT_P = { T: 700, P: 30, t: 300, Rm: 100, Ro: 20, w: 4 }
const DOM = { P: [2.5, 30] as const, t: [1, 3000] as const, Rm: [80, 150] as const,
  Ro: [15, 25] as const, w: [2, 5] as const }

/** Generic 3D field viewer: real x/y/z centroids, abs(global)/rel color scale. */
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
    const isCEEQ = field === 'CEEQ'
    const lo = Math.min(...values), hi = Math.max(...values)
    const loMap = scaleMode === 'abs' && globalRange ? globalRange[0] : lo
    const hiMap = scaleMode === 'abs' && globalRange ? globalRange[1] : hi
    setRange([lo, hi])
    const diverging = field !== 'CEEQ' && field !== 'von_mises'
    const col = new Float32Array(n * 3)
    const clamp01 = (x: number) => Math.min(1, Math.max(0, x))
    const cmap = (t: number) => {
      const cc = new THREE.Color().setHSL(0.72 - 0.7 * t, 0.85 + 0.15 * t, 0.32 + 0.63 * t)
      return [cc.r, cc.g, cc.b]
    }
    for (let i = 0; i < n; i++) {
      let v = values[i]
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
  }, [centroids, values, field, scaleMode, globalRange, globalLogRange])

  return <div className="view3d" ref={ref} />
}

export default function App() {
  const [p, setP] = useState(DEFAULT_P)
  const [res, setRes] = useState<V13Result | null>(null)
  const [field, setField] = useState<(typeof V13_FIELDS)[number]>('Srr')
  const [scale, setScale] = useState<'abs' | 'rel'>('abs')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [playing, setPlaying] = useState(false)
  const sliderTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const inputError = useMemo(() => {
    const { T, P, t, Rm, Ro, w } = p
    if (!(T > 0)) return '温度 T 必须 > 0°C'
    if (!V13_TEMPS.includes(T)) return '温度仅支持 550/600/650/700/750°C 五档'
    if (!(P >= 0)) return '压力 P 必须 ≥ 0 MPa'
    if (!(t > 0)) return '时间 t 必须 > 0 h'
    if (!(Rm > 0)) return '平均半径 Rm 必须 > 0 mm'
    if (!(Ro > 0)) return '外半径 Ro 必须 > 0 mm'
    if (!(w > 0)) return '壁厚 w 必须 > 0 mm'
    if (Ro >= Rm) return '几何错误：Ro 必须 < Rm（环形管约束）'
    if (w >= Ro) return '几何错误：壁厚 w 必须 < 外半径 Ro'
    if (Rm <= 2 * Ro) return '几何错误：Rm 必须 > 2×Ro（防自相交）'
    return null
  }, [p])

  const run = useCallback(async (pp?: typeof DEFAULT_P) => {
    const target = pp ?? p
    if (inputError) { setErr(inputError); return }
    setBusy(true); setErr(null)
    try {
      const r = await predictV13(target)
      if (r.status !== 'OK') {
        setErr(r.errors?.join('；') || '预测失败，请检查输入参数')
      } else {
        setRes(r)
        if (r.fields && !(field in r.fields)) setField('Srr')
      }
    } catch {
      setErr('无法连接预测服务，请确认后端已启动')
    }
    setBusy(false)
  }, [p, field, inputError])

  useEffect(() => { run() }, []) // eslint-disable-line

  const onTimeSlider = useCallback((nt: number) => {
    nt = Math.round(nt)
    setP((prev) => ({ ...prev, t: nt }))
    if (sliderTimer.current) clearTimeout(sliderTimer.current)
    sliderTimer.current = setTimeout(() => run({ ...p, t: nt }), 350)
  }, [p, run])

  useEffect(() => {
    if (!playing) return
    const iv = setInterval(() => {
      setP((prev) => {
        const nt = Math.min(3000, prev.t + 100)
        run({ ...prev, t: nt })
        if (nt >= 3000) setPlaying(false)
        return { ...prev, t: nt }
      })
    }, 500)
    return () => clearInterval(iv)
  }, [playing, run])

  const set = (k: keyof typeof DEFAULT_P) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setP((prev) => ({ ...prev, [k]: Number(e.target.value) }))

  const paramMeta: [keyof typeof DEFAULT_P, string, string, Readonly<[number, number]>, number][] = [
    ['T', '温度', '°C', [550, 750], 50], ['P', '压力', 'MPa', DOM.P, 1], ['t', '时间', 'h', DOM.t, 1],
    ['Rm', '环向半径', 'mm', DOM.Rm, 1], ['Ro', '外半径', 'mm', DOM.Ro, 1], ['w', '壁厚', 'mm', DOM.w, 1],
  ]

  const s = p.P * p.Ro / p.w

  return (
    <div className="app">
      <header>
        <div>
          <h1>316LN 三维高温蠕变场预测器</h1>
          <p className="sub">基于 Abaqus 高保真模拟数据的快速代理模型</p>
        </div>
        <div className="model-status"><span className="dot" /> 模型就绪 · V1.3</div>
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
          <div className={'ss ' + (s <= 250 ? '' : 'bad')}>
            应力尺度 P·Ro/w = <b>{s.toFixed(1)}</b> MPa
          </div>
          <button className="predict" onClick={() => run()} disabled={busy || !!inputError}>
            {busy ? '正在计算…' : '开始预测'}
          </button>
          {inputError && <div className="mini-ood">参数错误：{inputError}</div>}
          {!inputError && err && <div className="mini-ood">⚠ {err}</div>}
          <div className="tctl v13tctl">
            <div className="trow">
              <span>当前时间：t = {p.t} h</span>
              <button onClick={() => setPlaying(!playing)} disabled={!!inputError}>
                {playing ? '⏸ 暂停' : '▶ 放映'}
              </button>
            </div>
            <input type="range" min={50} max={3000} step={50} value={p.t}
              onChange={(e) => onTimeSlider(Number(e.target.value))} disabled={playing} />
            <div className="trow dim"><span>拖动时间滑块 · 放映自动递增（100 h/步，至 3000 h 停止）</span></div>
          </div>
        </aside>

        <main className="center">
          <div className="view-head">
            <h2>三维多物理场</h2>
            <div className="mode">
              <button className={scale === 'abs' ? 'on' : ''} onClick={() => setScale('abs')}
                title="全局固定范围：跨工况可比（改 T/P/t 颜色整体变化）">绝对色标</button>
              <button className={scale === 'rel' ? 'on' : ''} onClick={() => setScale('rel')}
                title="每工况自身范围：场内空间分布最大化（看内外圈差异）">相对色标</button>
              <button onClick={() => run()}>重新预测</button>
            </div>
          </div>
          {res?.status === 'OK' && res.fields && res.centroids ? (
            <V13Viewer centroids={res.centroids} values={res.fields[field]} field={field}
              scaleMode={scale}
              globalRange={res.global_ranges?.[field] as [number, number] | undefined}
              globalLogRange={res.global_ranges?.CEEQ_log10 as [number, number] | undefined} />
          ) : (
            <div className="view-empty">请输入有效工况并点击“开始预测”</div>
          )}
          <div className="colorbar">
            <span>{res?.summary?.[field]?.min.toExponential(2) ?? '0.00e+0'}</span>
            <div className="bar" />
            <span>{res?.summary?.[field]?.max.toExponential(2) ?? '1.00e+0'}</span>
          </div>
        </main>

        <aside className="panel right">
          <h2>预测结果</h2>
          <div className="v13fieldlist">
            {V13_FIELDS.map((f) => (
              <label key={f} className={'v13radio' + (field === f ? ' on' : '')}>
                <input type="radio" name="v13field" checked={field === f}
                  onChange={() => setField(f)} /> {V13_FIELD_ZH[f]}
                <em>{V13_UNITS[f]}</em>
              </label>
            ))}
          </div>
          {res === null ? <div className="empty">等待预测…</div> : res.status === 'OK' ? (
            <>
              <div className={'domain ' + (res.domain_status || '').toLowerCase()}>
                域状态：{res.domain_status === 'SAFE' ? '安全域' : res.domain_status === 'WARNING' ? '外推警告' : '超出训练域'}
              </div>
              <div className="domain-note">
                {res.domain_status === 'SAFE' && '当前输入位于模型训练覆盖范围内。'}
                {res.domain_status === 'WARNING' && '当前输入存在一定外推，结果可用于快速估计，CEEQ 建议使用 Abaqus 进一步验证。'}
                {res.domain_status === 'OUT_OF_DOMAIN' && '当前输入明显超出模型训练覆盖范围，结果不建议作为可靠工程结果，应使用 Abaqus 验证。'}
              </div>
              {res.domain_reasons?.map((r, i) => <div key={i} className="domain-reason">⚠ {r}</div>)}
              <div className="cards">
                <div className="card"><span>当前场 · 最大值</span>
                  <b>{res.summary?.[field]?.max.toExponential(3) ?? '-'}</b></div>
                <div className="card"><span>最小值</span>
                  <b>{res.summary?.[field]?.min.toExponential(3) ?? '-'}</b></div>
                <div className="card"><span>平均值</span>
                  <b>{res.summary?.[field]?.mean.toExponential(3) ?? '-'}</b></div>
                <div className="card"><span>P95</span>
                  <b>{res.summary?.[field]?.p95.toExponential(3) ?? '-'}</b></div>
              </div>
              <div className="hs-detail">
                <div>输入：T={p.T}°C ｜ P={p.P} MPa ｜ t={p.t} h</div>
                <div>Rm={p.Rm} mm ｜ Ro={p.Ro} mm ｜ w={p.w} mm</div>
                <div>应力尺度 P·Ro/w = {s.toFixed(1)} MPa</div>
                <div>模型：{res.model_version} · {res.schema_version}</div>
              </div>
            </>
          ) : (
            <div className="ood"><b>{res.status}</b>
              <p>{res.errors?.join('；')}</p></div>
          )}
        </aside>
      </div>

      <footer>
        <p>用于快速预测与可视化，超出模型适用范围时建议使用 Abaqus 验证。</p>
        <details className="model-info">
          <summary>模型信息</summary>
          <p>模型：316LN 高温蠕变代理模型（POD + Ridge 回归）</p>
          <p>训练数据：230 cases ｜ 温度 550–750°C ｜ 空间场 2304 点 ｜ 输出 8 场</p>
          <p>高保真数据来源：Abaqus 有限元模拟（AIR 环境）</p>
          <p>六个局部柱坐标应力分量 + CEEQ（log10 域训练，逆变换还原）+ von Mises（由预测六应力实时计算）</p>
          <p>已知局限：700/750°C 材料参数源自 FZKA 文献（N=0.08 炉次），CEEQ 预测偏快（保守）；时间 t 为 Abaqus 分析时间单位约定</p>
        </details>
      </footer>
    </div>
  )
}
