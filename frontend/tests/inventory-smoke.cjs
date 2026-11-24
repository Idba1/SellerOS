// Exercises the approved inventory transport shapes with isolated localhost mocks.
const { chromium } = require('playwright')
const { spawn } = require('node:child_process')
const assert = require('node:assert/strict')
const path = require('node:path')

const unit = {
  id: '00000000-0000-4000-8000-000000000201', product_id: '00000000-0000-4000-8000-000000000101', product_name: 'Canvas tote',
  variant_id: null, variant_name: null, quantity_on_hand: 3, low_stock_threshold: 5, is_low_stock: true, updated_at: '2026-01-01T08:00:00Z',
}
const movement = {
  id: '00000000-0000-4000-8000-000000000301', stock_unit_id: unit.id, movement_type: 'MANUAL_ADJUSTMENT', quantity_delta: 3,
  reason: 'Opening count', created_by_id: '00000000-0000-4000-8000-000000000001', reversal_of_id: null, occurred_at: '2026-01-01T08:00:00Z',
}

;(async () => {
  const root = path.resolve(__dirname, '..'); const port = '18772'; const apiBase = `http://127.0.0.1:${port}/api/v1/`
  const server = spawn(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', port, '--strictPort'], { cwd: root, stdio: 'pipe', windowsHide: true, env: { ...process.env, VITE_API_BASE_URL: apiBase } })
  let output = ''; server.stdout.on('data', chunk => { output += chunk }); server.stderr.on('data', chunk => { output += chunk })
  let browser
  try {
    let ready = false
    for (let attempt = 0; attempt < 60; attempt++) { try { ready = (await fetch(`http://127.0.0.1:${port}/inventory`)).ok } catch {} if (ready) break; await new Promise(resolve => setTimeout(resolve, 250)) }
    assert.ok(ready, `Inventory test server starts. ${output}`)
    browser = await chromium.launch({ channel: 'msedge', headless: true }); const page = await browser.newPage(); const errors = []
    page.on('pageerror', error => errors.push(error.message)); page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })
    await page.goto(`http://127.0.0.1:${port}/inventory`)
    assert.equal(await page.getByRole('heading', { name: 'Sign in to view inventory' }).count(), 1)
    await page.route('**/api/v1/inventory/**', async route => {
      const request = route.request(); const url = new URL(request.url())
      if (request.method() === 'GET' && url.pathname.endsWith('/inventory/')) return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ count: 1, next: null, previous: null, results: [unit] }) })
      if (request.method() === 'GET' && url.pathname.endsWith('/movements/')) return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ count: 1, next: null, previous: null, results: [movement] }) })
      if (request.method() === 'POST' && url.pathname.endsWith('/adjustments/')) return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ ...movement, id: '00000000-0000-4000-8000-000000000302', quantity_delta: -1, reason: 'Count correction' }) })
      throw new Error(`Unexpected ${request.method()} ${request.url()}`)
    })
    await page.addInitScript(() => window.sessionStorage.setItem('selleros.auth.session.v1', JSON.stringify({ account: { id: '00000000-0000-4000-8000-000000000001', email: 'seller@example.test' }, token: 'not-a-real-token' })))
    await page.goto(`http://127.0.0.1:${port}/inventory`)
    await page.getByRole('heading', { name: '1 stock unit' }).waitFor()
    assert.equal(await page.getByText('Low stock', { exact: true }).count(), 1)
    await page.getByRole('button', { name: 'Review' }).click()
    await page.getByRole('heading', { name: 'Canvas tote' }).last().waitFor()
    assert.equal(await page.getByText('Opening count').count(), 1)
    await page.getByRole('button', { name: 'Manual adjustment' }).click()
    await page.getByLabel('Quantity change').fill('-1'); await page.getByLabel('Reason').fill('Count correction')
    await page.getByRole('button', { name: 'Record adjustment' }).click()
    await page.getByRole('heading', { name: '1 stock unit' }).waitFor()
    for (const width of [375, 1280]) { await page.setViewportSize({ width, height: 800 }); await page.goto(`http://127.0.0.1:${port}/inventory`); await page.getByRole('heading', { name: '1 stock unit' }).waitFor(); const mainFits = await page.locator('main').evaluate(element => element.scrollWidth === element.clientWidth); assert.equal(mainFits, true, `App layout fits at ${width}px`) }
    assert.deepEqual(errors, [])
    console.log('PASS: inventory signed-out, live list, movement history, adjustment, and responsive states')
  } finally {
    if (browser) await browser.close()
    if (server.exitCode === null) { const exited = new Promise(resolve => server.once('exit', resolve)); server.kill(); await exited }
  }
})().catch(error => { console.error(error); process.exitCode = 1 })
