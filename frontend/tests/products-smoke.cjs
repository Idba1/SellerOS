// Exercises real product-route shapes with isolated transport mocks; no demo catalogue is used.
const { chromium } = require('playwright')
const { spawn } = require('node:child_process')
const assert = require('node:assert/strict')
const path = require('node:path')

const product = {
  id: '00000000-0000-4000-8000-000000000101', name: 'Canvas tote', category: 'Accessories',
  selling_price: '120.00', unit_cost: '45.00', has_variants: false, is_active: true,
  created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
}

;(async () => {
  const root = path.resolve(__dirname, '..')
  const port = '18771'
  const apiBase = `http://127.0.0.1:${port}/api/v1/`
  const server = spawn(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', port, '--strictPort'], { cwd: root, stdio: 'pipe', windowsHide: true, env: { ...process.env, VITE_API_BASE_URL: apiBase } })
  let output = ''; server.stdout.on('data', chunk => { output += chunk }); server.stderr.on('data', chunk => { output += chunk })
  let browser
  try {
    let ready = false
    for (let attempt = 0; attempt < 60; attempt++) { try { ready = (await fetch(`http://127.0.0.1:${port}/products`)).ok } catch {} if (ready) break; await new Promise(resolve => setTimeout(resolve, 250)) }
    assert.ok(ready, `Products test server starts. ${output}`)
    browser = await chromium.launch({ channel: 'msedge', headless: true })
    const page = await browser.newPage()
    const errors = []
    page.on('pageerror', error => errors.push(error.message)); page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })
    await page.goto(`http://127.0.0.1:${port}/products`)
    assert.equal(await page.getByRole('heading', { name: 'Sign in to view products' }).count(), 1)

    await page.route('**/api/v1/products/**', async route => {
      const request = route.request(); const url = new URL(request.url())
      if (request.method() === 'GET' && url.pathname.endsWith('/products/')) return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ count: 1, next: null, previous: null, results: [product] }) })
      if (request.method() === 'GET') return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ...product, variants: [] }) })
      if (request.method() === 'POST') return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ ...product, id: '00000000-0000-4000-8000-000000000102', name: 'New tote' }) })
      throw new Error(`Unexpected ${request.method()} ${request.url()}`)
    })
    await page.addInitScript(() => window.sessionStorage.setItem('selleros.auth.session.v1', JSON.stringify({ account: { id: '00000000-0000-4000-8000-000000000001', email: 'seller@example.test' }, token: 'not-a-real-token' })))
    await page.goto(`http://127.0.0.1:${port}/products`)
    await page.getByRole('heading', { name: '1 product' }).waitFor()
    assert.equal(await page.getByRole('rowheader', { name: 'Canvas tote' }).count(), 1)
    await page.getByRole('button', { name: 'View' }).click()
    await page.getByRole('heading', { name: 'Canvas tote' }).last().waitFor()
    assert.equal(await page.getByText('Standalone product').count(), 1)
    await page.getByRole('button', { name: 'Add product' }).first().click()
    await page.getByLabel('Product name').fill('New tote')
    await page.getByLabel('Selling price (BDT)').fill('200')
    await page.getByRole('button', { name: 'Create product' }).click()
    await page.getByRole('heading', { name: '1 product' }).waitFor()
    for (const width of [375, 1280]) { await page.setViewportSize({ width, height: 800 }); await page.goto(`http://127.0.0.1:${port}/products`); await page.getByRole('heading', { name: '1 product' }).waitFor(); const layout = await page.evaluate(() => { const main = document.querySelector('main'); const table = document.querySelector('.products-table-card .table-wrap'); return { mainFits: main?.scrollWidth === main?.clientWidth, tableHasContainedOverflow: table !== null && table.scrollWidth >= table.clientWidth } }); assert.equal(layout.mainFits, true, `App layout fits at ${width}px`); assert.equal(layout.tableHasContainedOverflow, true, `Table stays inside its horizontal-scroll container at ${width}px`) }
    assert.deepEqual(errors, [])
    console.log('PASS: products signed-out, live list, detail, create, and responsive states')
  } finally {
    if (browser) await browser.close()
    if (server.exitCode === null) { const exited = new Promise(resolve => server.once('exit', resolve)); server.kill(); await exited }
  }
})().catch(error => { console.error(error); process.exitCode = 1 })
