// Exercises approved customer profile and purchase-history transport with localhost mocks.
const { chromium } = require('playwright')
const { spawn } = require('node:child_process')
const assert = require('node:assert/strict')
const path = require('node:path')

const customer = { id: '00000000-0000-4000-8000-000000000401', display_name: 'Avery Customer', phone: '+8801700000000', email: 'avery@example.test', created_at: '2026-01-02T00:00:00Z', updated_at: '2026-01-02T00:00:00Z' }
const history = { purchase_count: 2, last_purchase_at: '2026-01-10T00:00:00Z', total_spend: '780.00' }

;(async () => {
  const root = path.resolve(__dirname, '..'); const port = '18773'; const apiBase = `http://127.0.0.1:${port}/api/v1/`
  const server = spawn(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', port, '--strictPort'], { cwd: root, stdio: 'pipe', windowsHide: true, env: { ...process.env, VITE_API_BASE_URL: apiBase } })
  let output = ''; server.stdout.on('data', chunk => { output += chunk }); server.stderr.on('data', chunk => { output += chunk })
  let browser
  try {
    let ready = false
    for (let attempt = 0; attempt < 60; attempt++) { try { ready = (await fetch(`http://127.0.0.1:${port}/customers`)).ok } catch {} if (ready) break; await new Promise(resolve => setTimeout(resolve, 250)) }
    assert.ok(ready, `Customers test server starts. ${output}`)
    browser = await chromium.launch({ channel: 'msedge', headless: true }); const page = await browser.newPage(); const errors = []
    page.on('pageerror', error => errors.push(error.message)); page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })
    await page.goto(`http://127.0.0.1:${port}/customers`)
    assert.equal(await page.getByRole('heading', { name: 'Sign in to view customers' }).count(), 1)
    await page.route('**/api/v1/customers/**', async route => {
      const request = route.request(); const url = new URL(request.url())
      if (request.method() === 'GET' && url.pathname.endsWith('/customers/')) return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ count: 1, next: null, previous: null, results: [customer] }) })
      if (request.method() === 'GET' && url.pathname.endsWith('/purchase-history/')) return route.fulfill({ contentType: 'application/json', body: JSON.stringify(history) })
      if (request.method() === 'GET') return route.fulfill({ contentType: 'application/json', body: JSON.stringify(customer) })
      if (request.method() === 'POST') return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ ...customer, id: '00000000-0000-4000-8000-000000000402', display_name: 'New customer' }) })
      if (request.method() === 'PATCH') return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ...customer, display_name: 'Updated customer' }) })
      throw new Error(`Unexpected ${request.method()} ${request.url()}`)
    })
    await page.addInitScript(() => window.sessionStorage.setItem('selleros.auth.session.v1', JSON.stringify({ account: { id: '00000000-0000-4000-8000-000000000001', email: 'seller@example.test' }, token: 'not-a-real-token' })))
    await page.goto(`http://127.0.0.1:${port}/customers`)
    await page.getByRole('heading', { name: '1 customer' }).waitFor()
    await page.getByRole('button', { name: 'Review' }).click()
    await page.getByRole('heading', { name: 'Avery Customer' }).last().waitFor()
    assert.equal(await page.getByText('Eligible purchases').count(), 1)
    assert.equal(await page.getByText('BDT 780.00').count(), 1)
    await page.getByRole('button', { name: 'Add customer' }).first().click()
    await page.getByLabel('Customer name').fill('New customer')
    await page.getByRole('button', { name: 'Add customer' }).last().click()
    await page.getByRole('heading', { name: '1 customer' }).waitFor()
    for (const width of [375, 1280]) { await page.setViewportSize({ width, height: 800 }); await page.goto(`http://127.0.0.1:${port}/customers`); await page.getByRole('heading', { name: '1 customer' }).waitFor(); const mainFits = await page.locator('main').evaluate(element => element.scrollWidth === element.clientWidth); assert.equal(mainFits, true, `App layout fits at ${width}px`) }
    assert.deepEqual(errors, [])
    console.log('PASS: customers signed-out, live list, history, create, and responsive states')
  } finally {
    if (browser) await browser.close()
    if (server.exitCode === null) { const exited = new Promise(resolve => server.once('exit', resolve)); server.kill(); await exited }
  }
})().catch(error => { console.error(error); process.exitCode = 1 })
