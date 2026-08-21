/* STEP18.1 acceptance screenshots: main (demo=1), OOD (demo=4),
   re-predict view (param change), + hotspot_xyz geometry sanity print */
const puppeteer = require('puppeteer-core')
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const OUT = 'D:/harness_work/ss316ln_toroidal_tube/docs/figures/webapp/'
;(async () => {
  const b = await puppeteer.launch({ executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox', '--enable-unsafe-swiftshader'] })
  // 1. main page (demo=1: T600 baseline)
  const p = await b.newPage()
  await p.setViewport({ width: 1366, height: 900 })
  await p.goto('http://127.0.0.1:5173/?demo=1', { waitUntil: 'networkidle0', timeout: 30000 })
  await p.waitForFunction(() => document.body.innerText.includes('热点'), { timeout: 15000 })
  await new Promise((r) => setTimeout(r, 2500))
  await p.screenshot({ path: OUT + 'webapp_main_181.png' })
  // hotspot geometry sanity: must lie on torus wall (Rm±Ro ring), not at origin
  const hs = await p.evaluate(() => {
    const m = document.querySelectorAll('.hs-detail div')
    const el = [...m].map((x) => x.textContent)
    return el
  })
  console.log('HS DETAIL:', JSON.stringify(hs))
  // 2. OOD page (demo=4: T700)
  const p2 = await b.newPage()
  await p2.setViewport({ width: 1366, height: 900 })
  await p2.goto('http://127.0.0.1:5173/?demo=4', { waitUntil: 'networkidle0', timeout: 30000 })
  await p2.waitForFunction(() => document.body.innerText.includes('超出模型有效域'), { timeout: 15000 })
  await new Promise((r) => setTimeout(r, 1500))
  await p2.screenshot({ path: OUT + 'webapp_ood_181.png' })
  // 3. re-predict view: change T 600->650 & predict; camera must persist (same canvas)
  await p.evaluate(() => {
    const inputs = document.querySelectorAll('.left input[type=number]')
    inputs[0].value = '650'
    inputs[0].dispatchEvent(new Event('change', { bubbles: true }))
  })
  await new Promise((r) => setTimeout(r, 300))
  const c1 = await p.evaluate(() => document.querySelectorAll('.view3d canvas').length)
  await p.evaluate(() => document.querySelector('.predict').click())
  await new Promise((r) => setTimeout(r, 2000))
  const c2 = await p.evaluate(() => document.querySelectorAll('.view3d canvas').length)
  await p.screenshot({ path: OUT + 'webapp_repredict_181.png' })
  console.log('REPREDICT canvases:', c1, '->', c2)
  await b.close()
  console.log('SCREENSHOTS DONE')
})().catch((e) => { console.error('FATAL:', String(e).slice(0, 500)); process.exit(1) })
