/* STEP21-D WebApp integration test: V1.3 mode + V1.2 regression. */
const puppeteer = require('puppeteer-core')
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
;(async () => {
  const b = await puppeteer.launch({ executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox', '--enable-unsafe-swiftshader'] })
  const p = await b.newPage()
  await p.setViewport({ width: 1366, height: 900 })
  const errs = []
  p.on('pageerror', (e) => errs.push(String(e)))
  await p.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle0', timeout: 30000 })
  await p.waitForFunction(() => document.body.innerText.includes('开始预测'), { timeout: 15000 })
  const pass = (n, c) => console.log(`[${c ? 'PASS' : 'FAIL'}] ${n}`)
  // V1.2 regression: default mode still works
  await p.waitForFunction(() => document.body.innerText.includes('最大 CEEQ'), { timeout: 20000 })
  pass('V1.2 默认模式渲染', true)
  // switch to V1.3
  await p.evaluate(() => {
    const btns = [...document.querySelectorAll('.v13tab')]
    btns.find((x) => x.textContent.includes('多物理场')).click()
  })
  await p.waitForFunction(() => document.body.innerText.includes('域状态'), { timeout: 20000 })
  pass('V1.3 模式切换 + 预测', true)
  const info = await p.evaluate(() => ({
    domain: document.querySelector('.domain')?.innerText || '',
    cards: document.querySelectorAll('.right .card').length,
    canvas: document.querySelectorAll('.view3d canvas').length,
    fieldOpts: document.querySelectorAll('.v13field option').length,
  }))
  pass('域状态显示: ' + info.domain, /安全域|外推警告|超出/.test(info.domain))
  pass('结果卡片=4', info.cards === 4)
  pass('3D canvas=1', info.canvas === 1)
  pass('场选项=8', info.fieldOpts === 8)
  // switch field -> CEEQ
  await p.evaluate(() => {
    const s = document.querySelector('.v13field')
    s.value = 'CEEQ'; s.dispatchEvent(new Event('change', { bubbles: true }))
  })
  await new Promise((r) => setTimeout(r, 800))
  const ceeqCard = await p.evaluate(() => document.querySelector('.right .card b')?.innerText || '')
  pass('CEEQ 场切换 + 摘要更新', /e[-+]\d+/.test(ceeqCard))
  // EXT case -> warning (native setter for React controlled inputs)
  await p.evaluate(() => {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
    const inputs = [...document.querySelectorAll('.left input[type=number]')]
    const vals = ['700', '20', '100', '120', '25', '3']
    inputs.forEach((x, i) => { setter.call(x, vals[i]); x.dispatchEvent(new Event('input', { bubbles: true })) })
  })
  await new Promise((r) => setTimeout(r, 300))
  await p.evaluate(() => {
    const btns = [...document.querySelectorAll('.mode button')]
    btns.find((x) => x.textContent.includes('重新预测')).click()
  })
  await p.waitForFunction(() => {
    const d = document.querySelector('.domain')
    return d && /警告|超出/.test(d.innerText)
  }, { timeout: 20000 })
  pass('EXT case 域警告显示', true)
  // back to V1.2 mode regression
  await p.evaluate(() => {
    const btns = [...document.querySelectorAll('.v13tab')]
    btns.find((x) => x.textContent.includes('CEEQ 场')).click()
  })
  await p.waitForFunction(() => document.body.innerText.includes('时间演化'), { timeout: 15000 })
  pass('V1.2 模式恢复', true)
  console.log('JS errors:', errs.length ? errs.slice(0, 3) : 'NONE')
  await b.close()
})().catch((e) => { console.error('FATAL', String(e).slice(0, 400)); process.exit(1) })
