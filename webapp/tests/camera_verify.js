/* STEP18.2 numeric camera verification via window.__viewer (dev-only hook):
   1. initial pose           2. after drag (changed)
   3. after param change + re-predict (MUST equal drag pose)
   4. after Reset Camera (MUST equal initial pose) */
const puppeteer = require('puppeteer-core')
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
;(async () => {
  const b = await puppeteer.launch({ executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox', '--enable-unsafe-swiftshader'] })
  const p = await b.newPage()
  await p.setViewport({ width: 1366, height: 900 })
  await p.goto('http://127.0.0.1:5173/?demo=1', { waitUntil: 'networkidle0', timeout: 30000 })
  await p.waitForFunction(() => document.body.innerText.includes('热点'), { timeout: 15000 })
  await new Promise((r) => setTimeout(r, 2000))
  const read = async (label) => {
    const s = await p.evaluate(() => {
      const v = window.__viewer
      return { pos: [v.camera.position.x, v.camera.position.y, v.camera.position.z],
               q: [v.camera.quaternion.x, v.camera.quaternion.y, v.camera.quaternion.z, v.camera.quaternion.w],
               target: [v.controls.target.x, v.controls.target.y, v.controls.target.z] }
    })
    console.log(label, JSON.stringify(s.map ? s : s))
    return s
  }
  const eq = (a, b, tol = 1e-6) => a.pos.every((v, i) => Math.abs(v - b.pos[i]) < tol)
    && a.q.every((v, i) => Math.abs(v - b.q[i]) < tol)
  const initial = await read('INITIAL ')
  const v = await p.evaluate(() => {
    const r = document.querySelector('.view3d').getBoundingClientRect()
    return { x: r.left, y: r.top, w: r.width, h: r.height }
  })
  const cx = v.x + v.w / 2, cy = v.y + v.h / 2
  await p.mouse.move(cx, cy); await p.mouse.down()
  await p.mouse.move(cx + 180, cy + 90, { steps: 15 }); await p.mouse.up()
  await new Promise((r) => setTimeout(r, 5000)) // wait for damping to fully settle
  const dragged = await read('DRAGGED ')
  // param change + re-predict
  await p.evaluate(() => {
    const inputs = document.querySelectorAll('.left input[type=number]')
    inputs[0].value = '650'
    inputs[0].dispatchEvent(new Event('change', { bubbles: true }))
  })
  await new Promise((r) => setTimeout(r, 300))
  await p.evaluate(() => document.querySelector('.predict').click())
  await new Promise((r) => setTimeout(r, 5000)) // settle after re-predict
  const repred = await read('REPRED  ')
  // reset camera
  await p.evaluate(() => {
    const btns = [...document.querySelectorAll('.mode button')]
    btns.find((x) => x.textContent.includes('重置视角')).click()
  })
  await new Promise((r) => setTimeout(r, 1500))
  const reset = await read('RESET   ')
  const c1 = eq(dragged, repred) ? 'PASS' : 'FAIL'
  const c2 = eq(initial, reset) ? 'PASS' : 'FAIL'
  console.log(`CAMERA_PERSIST_AFTER_REPREDICT: ${c1}`)
  console.log(`CAMERA_RESET_EXACT: ${c2}`)
  await b.close()
  process.exit(c1 === 'PASS' && c2 === 'PASS' ? 0 : 1)
})().catch((e) => { console.error('FATAL:', String(e).slice(0, 400)); process.exit(1) })
