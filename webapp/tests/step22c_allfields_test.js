/* STEP22-C: all 8 fields - cross-case color distinction + in-field variance.
   For each field: predict T=550 & T=750 (absolute scale), screenshot, then
   analyze hue distribution (cross-case diff) and hue spread (in-field). */
const puppeteer = require('puppeteer-core')
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const OUT = 'D:/harness_work/ss316ln_toroidal_tube/ml/v13/viz/'
;(async () => {
  const b = await puppeteer.launch({ executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox', '--enable-unsafe-swiftshader'] })
  const p = await b.newPage()
  await p.setViewport({ width: 1366, height: 900 })
  const errs = []
  p.on('pageerror', (e) => errs.push(String(e)))
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
  // 8 fields, 2 temps each
  for (let fi = 0; fi < 8; fi++) {
    await p.evaluate((fi) => {
      const labels = [...document.querySelectorAll('.v13radio')]
      labels[fi].querySelector('input').click()
    }, fi)
    await new Promise((r) => setTimeout(r, 500))
    for (const T of [550, 750]) {
      await setInput([String(T), '30', '300', '100', '20', '4'])
      await new Promise((r) => setTimeout(r, 400))
      await p.evaluate(() => [...document.querySelectorAll('.mode button')].find((x) => x.textContent.includes('重新预测')).click())
      await new Promise((r) => setTimeout(r, 2200))
      await p.screenshot({ path: OUT + `f${fi}_T${T}.png` })
    }
  }
  check('无 JS 错误', errs.length === 0, errs.slice(0, 2).join(' | '))
  function check(n, c, d = '') { console.log(`[${c ? 'PASS' : 'FAIL'}] ${n} ${d}`) }
  console.log('SCREENSHOTS DONE: f0..f7 x T550/T750')
  await b.close()
})().catch((e) => { console.error('FATAL', String(e).slice(0, 400)); process.exit(1) })
