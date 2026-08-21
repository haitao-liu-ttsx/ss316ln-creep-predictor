/* STEP22-B: verify temp 5-step UI + absolute-scale color distinction.
   Predict T=550 vs T=750 (CEEQ field), screenshot both, compare pixel
   distributions in the 3D canvas (absolute scale must show clear difference). */
const puppeteer = require('puppeteer-core')
const fs = require('fs')
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const OUT = 'D:/harness_work/ss316ln_toroidal_tube/ml/v13/viz/'
;(async () => {
  const b = await puppeteer.launch({ executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox', '--enable-unsafe-swiftshader'] })
  const p = await b.newPage()
  await p.setViewport({ width: 1366, height: 900 })
  const errs = []
  p.on('pageerror', (e) => errs.push(String(e)))
  const check = (n, c, d = '') => console.log(`[${c ? 'PASS' : 'FAIL'}] ${n} ${d}`)
  const setInput = async (vals) => {
    await p.evaluate((vals) => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
      const inputs = [...document.querySelectorAll('.left input[type=number]')]
      inputs.forEach((x, i) => { setter.call(x, vals[i]); x.dispatchEvent(new Event('input', { bubbles: true })) })
    }, vals)
  }
  await p.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle0', timeout: 30000 })
  await p.waitForFunction(() => document.body.innerText.includes('开始预测'), { timeout: 15000 })
  await p.evaluate(() => [...document.querySelectorAll('.v13tab')].find((x) => x.textContent.includes('多物理场')).click())
  await p.waitForFunction(() => document.body.innerText.includes('域状态'), { timeout: 20000 })
  // 1) temp step check
  const tStep = await p.evaluate(() => document.querySelectorAll('.left input[type=number]')[0].step)
  check('温度 step=50', tStep === '50', 'step=' + tStep)
  const tRange = await p.evaluate(() => document.querySelectorAll('.left .prange')[0].innerText)
  check('温度范围 550-750', tRange === '550–750', tRange)
  // 2) non-calibrated temp rejected
  await setInput(['575', '30', '300', '100', '20', '4'])
  await new Promise((r) => setTimeout(r, 400))
  check('575°C 被阻止（仅五档）', await p.evaluate(() => document.body.innerText.includes('仅支持')))
  // 3) color distinction: T=550 vs T=750 CEEQ, absolute scale
  await setInput(['550', '30', '300', '100', '20', '4'])
  await new Promise((r) => setTimeout(r, 400))
  await p.evaluate(() => [...document.querySelectorAll('.mode button')].find((x) => x.textContent.includes('重新预测')).click())
  await new Promise((r) => setTimeout(r, 2500))
  await p.evaluate(() => {
    const labels = [...document.querySelectorAll('.v13radio')]
    labels[6].querySelector('input').click() // CEEQ
  })
  await new Promise((r) => setTimeout(r, 600))
  await p.screenshot({ path: OUT + 'color_T550_abs.png' })
  // T=750
  await setInput(['750', '30', '300', '100', '20', '4'])
  await new Promise((r) => setTimeout(r, 400))
  await p.evaluate(() => [...document.querySelectorAll('.mode button')].find((x) => x.textContent.includes('重新预测')).click())
  await new Promise((r) => setTimeout(r, 2500))
  await p.screenshot({ path: OUT + 'color_T750_abs.png' })
  // rel scale for comparison
  await p.evaluate(() => [...document.querySelectorAll('.mode button')].find((x) => x.textContent.includes('相对色标')).click())
  await new Promise((r) => setTimeout(r, 800))
  await p.screenshot({ path: OUT + 'color_T750_rel.png' })
  check('无 JS 错误', errs.length === 0, errs.slice(0, 2).join(' | '))
  console.log('SCREENSHOTS: color_T550_abs.png / color_T750_abs.png / color_T750_rel.png')
  await b.close()
})().catch((e) => { console.error('FATAL', String(e).slice(0, 400)); process.exit(1) })
