/* STEP18.2 acceptance screenshots:
   A) default field, hotspot OFF -> clean model
   B) hotspot ON -> tiny crosshair at API hotspot xyz
   C) after drag + param change + re-predict -> camera NOT reset (view persists)
   Also prints hotspot screen bbox via pixel-free proxy: none (image analysis in PS). */
const puppeteer = require('puppeteer-core')
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const OUT = 'D:/harness_work/ss316ln_toroidal_tube/docs/figures/webapp/'
;(async () => {
  const b = await puppeteer.launch({ executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox', '--enable-unsafe-swiftshader'] })
  const p = await b.newPage()
  await p.setViewport({ width: 1366, height: 900 })
  await p.goto('http://127.0.0.1:5173/?demo=1', { waitUntil: 'networkidle0', timeout: 30000 })
  await p.waitForFunction(() => document.body.innerText.includes('热点'), { timeout: 15000 })
  await new Promise((r) => setTimeout(r, 2500))
  const hs = await p.evaluate(() => {
    const m = document.querySelectorAll('.hs-detail div')
    return [...m].map((x) => x.textContent)
  })
  console.log('HS:', JSON.stringify(hs))
  const v = await p.evaluate(() => {
    const r = document.querySelector('.view3d').getBoundingClientRect()
    return { x: r.left, y: r.top, w: r.width, h: r.height }
  })
  console.log('VIEW3D:', JSON.stringify(v))
  // B: hotspot ON (default) - small crosshair visible
  await p.screenshot({ path: OUT + 'webapp_182_hotspot_on.png' })
  // A: toggle hotspot OFF -> clean model
  await p.evaluate(() => {
    const btns = [...document.querySelectorAll('.mode button')]
    const b = btns.find((x) => x.textContent.includes('显示热点'))
    b.click()
  })
  await new Promise((r) => setTimeout(r, 800))
  await p.screenshot({ path: OUT + 'webapp_182_clean.png' })
  // C: drag to orbit, then change param + re-predict -> camera must persist
  const cx = v.x + v.w / 2, cy = v.y + v.h / 2
  await p.mouse.move(cx, cy)
  await p.mouse.down()
  await p.mouse.move(cx + 180, cy + 90, { steps: 12 })
  await p.mouse.up()
  await new Promise((r) => setTimeout(r, 1200)) // damping settle
  await p.screenshot({ path: OUT + 'webapp_182_dragged.png' })
  await p.evaluate(() => {
    const inputs = document.querySelectorAll('.left input[type=number]')
    inputs[0].value = '650'
    inputs[0].dispatchEvent(new Event('change', { bubbles: true }))
  })
  await new Promise((r) => setTimeout(r, 300))
  const c1 = await p.evaluate(() => document.querySelectorAll('.view3d canvas').length)
  await p.evaluate(() => document.querySelector('.predict').click())
  await new Promise((r) => setTimeout(r, 2200))
  const c2 = await p.evaluate(() => document.querySelectorAll('.view3d canvas').length)
  await p.screenshot({ path: OUT + 'webapp_182_repredict.png' })
  console.log('CANVASES after param re-predict:', c1, '->', c2)
  await b.close()
  console.log('DONE')
})().catch((e) => { console.error('FATAL:', String(e).slice(0, 500)); process.exit(1) })
