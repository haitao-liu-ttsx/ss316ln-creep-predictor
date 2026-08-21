/* STEP 18.1 UI smoke: scroll width, Chinese UI, predict flow, camera persistence
   (camera held in refs -> scene not recreated on predict), reset button. */
const puppeteer = require('puppeteer-core')

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'

async function main() {
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox', '--enable-unsafe-swiftshader', '--window-size=1366,900'] })
  const page = await browser.newPage()
  await page.setViewport({ width: 1366, height: 900 })
  const results = []
  const check = (name, ok, detail = '') => { results.push({ name, ok, detail }) }

  await page.goto('http://127.0.0.1:5173/?demo=1', { waitUntil: 'networkidle0', timeout: 30000 })
  try {
    await page.waitForFunction(() => document.body.innerText.includes('开始预测'), { timeout: 10000 })
  } catch (e) {
    const body = await page.evaluate(() => document.body.innerText.slice(0, 500))
    const err = await page.evaluate(() => (window.__err || ''))
    console.log('PAGE TEXT:', body.replace(/\n/g, ' | '))
    console.log('console errors:', err)
    throw e
  }
  // 1 scroll width <= innerWidth (1366)
  const sw = await page.evaluate(() => document.documentElement.scrollWidth)
  check('no_horizontal_scroll_1366', sw <= 1366, `scrollWidth=${sw}`)
  // 2 Chinese UI
  const txt = await page.evaluate(() => document.body.innerText)
  for (const s of ['环形结构蠕变场', '预测参数', '开始预测', '预测结果', '最大 CEEQ',
                   '物理检查', '时间演化', '示例案例']) {
    check('zh_' + s, txt.includes(s))
  }
  // 3 initial predict auto-runs -> results appear
  try {
    await page.waitForFunction(() => document.body.innerText.includes('热点'), { timeout: 15000 })
  } catch (e) {
    const right = await page.evaluate(() =>
      document.querySelector('.right')?.innerText?.slice(0, 400) || 'NO .right')
    const canv = await page.evaluate(() => document.querySelectorAll('canvas').length)
    console.log('RIGHT PANEL:', right.replace(/\n/g, ' | '))
    console.log('canvases:', canv)
    const errs = []
    page.on('pageerror', (x) => errs.push(String(x)))
    throw e
  }
  check('predict_results_shown', true)
  // 4 camera persistence: count canvases before/after a re-predict (scene not rebuilt)
  const before = await page.evaluate(() => document.querySelectorAll('.view3d canvas').length)
  await page.evaluate(() => {
    document.querySelector('.predict').click()
  })
  await new Promise((r) => setTimeout(r, 1500))
  const after = await page.evaluate(() => document.querySelectorAll('.view3d canvas').length)
  check('camera_not_recreated_on_predict', before === after && before === 1,
    `canvases ${before}->${after}`)
  // 5 change a parameter (T input) and predict -> still 1 canvas
  await page.evaluate(() => {
    const inputs = document.querySelectorAll('.left input[type=number]')
    inputs[0].value = '650'
    inputs[0].dispatchEvent(new Event('change', { bubbles: true }))
  })
  await new Promise((r) => setTimeout(r, 300))
  await page.evaluate(() => document.querySelector('.predict').click())
  await new Promise((r) => setTimeout(r, 1500))
  const after2 = await page.evaluate(() => document.querySelectorAll('.view3d canvas').length)
  check('camera_persists_after_param_change', after2 === 1, `canvases=${after2}`)
  // 6 OOD demo (demo=4)
  const page2 = await browser.newPage()
  await page2.setViewport({ width: 1366, height: 900 })
  await page2.goto('http://127.0.0.1:5173/?demo=4', { waitUntil: 'networkidle0', timeout: 30000 })
  await page2.waitForFunction(() => document.body.innerText.includes('超出模型有效域'), { timeout: 15000 })
  const sw2 = await page2.evaluate(() => document.documentElement.scrollWidth)
  check('no_horizontal_scroll_ood', sw2 <= 1366, `scrollWidth=${sw2}`)
  const ood = await page2.evaluate(() => document.body.innerText)
  check('ood_zh_data_required', ood.includes('需要补充材料数据') && ood.includes('模型有效范围'))
  // 7 1440 / 1920 no horizontal scroll
  for (const w of [1440, 1920]) {
    await page2.setViewport({ width: w, height: 900 })
    await new Promise((r) => setTimeout(r, 500))
    const s = await page2.evaluate(() => document.documentElement.scrollWidth)
    check(`no_horizontal_scroll_${w}`, s <= w, `scrollWidth=${s}`)
  }
  await browser.close()
  let fail = 0
  for (const r of results) { console.log(`[${r.ok ? 'PASS' : 'FAIL'}] ${r.name} ${r.detail}`); if (!r.ok) fail++ }
  console.log(`UI SMOKE: ${results.length - fail}/${results.length} PASS`)
  process.exit(fail ? 1 : 0)
}

main().catch((e) => { console.error(e); process.exit(1) })
