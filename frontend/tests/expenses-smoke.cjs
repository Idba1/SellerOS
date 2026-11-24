const { chromium } = require('playwright')
const { spawn } = require('node:child_process')
const assert = require('node:assert/strict')
const path = require('node:path')
const expense = { id: '00000000-0000-4000-8000-000000000701', description: 'Courier packaging', category: 'Packaging', amount: '250.00', incurred_on: '2026-01-02', created_at: '2026-01-02T00:00:00Z', updated_at: '2026-01-02T00:00:00Z' }
;(async () => {
  const root = path.resolve(__dirname, '..'), port = '18775', base = `http://127.0.0.1:${port}/api/v1/`
  const server = spawn(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', port, '--strictPort'], { cwd: root, stdio: 'pipe', windowsHide: true, env: { ...process.env, VITE_API_BASE_URL: base } })
  let browser
  try {
    let ready = false; for (let i = 0; i < 60; i++) { try { ready = (await fetch(`http://127.0.0.1:${port}/expenses`)).ok } catch {} if (ready) break; await new Promise(r => setTimeout(r, 250)) }; assert.ok(ready)
    browser = await chromium.launch({ channel: 'msedge', headless: true }); const page = await browser.newPage(), errors = []
    page.on('pageerror', e => errors.push(e.message)); page.on('console', m => { if (m.type() === 'error') errors.push(m.text()) })
    await page.goto(`http://127.0.0.1:${port}/expenses`); assert.equal(await page.getByRole('heading', { name: 'Sign in to view expenses' }).count(), 1)
    await page.route('**/api/v1/expenses/**', async route => { const req = route.request(), url = new URL(req.url()); if (req.method() === 'GET' && url.pathname.endsWith('/expenses/')) return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ count: 1, next: null, previous: null, results: [expense] }) }); if (req.method() === 'POST') return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(expense) }); throw new Error(req.url()) })
    await page.addInitScript(() => sessionStorage.setItem('selleros.auth.session.v1', JSON.stringify({ account: { id: '00000000-0000-4000-8000-000000000001', email: 'seller@example.test' }, token: 'not-real' })))
    await page.goto(`http://127.0.0.1:${port}/expenses`); await page.getByRole('heading', { name: '1 expense' }).waitFor(); await page.getByRole('button', { name: 'Add expense' }).first().click()
    const form = page.locator('.expense-form'); await form.getByLabel('Description').fill('Courier packaging'); await form.getByLabel('Category').fill('Packaging'); await form.getByLabel('Amount (BDT)').fill('250'); await form.getByLabel('Incurred on').fill('2026-01-02'); await form.getByRole('button', { name: 'Add expense' }).click(); await page.getByRole('heading', { name: '1 expense' }).waitFor()
    for (const width of [375, 1280]) { await page.setViewportSize({ width, height: 800 }); await page.goto(`http://127.0.0.1:${port}/expenses`); await page.getByRole('heading', { name: '1 expense' }).waitFor(); assert.equal(await page.locator('main').evaluate(e => e.scrollWidth === e.clientWidth), true) }
    assert.deepEqual(errors, []); console.log('PASS: expenses signed-out, list, create, responsive states')
  } finally { if (browser) await browser.close(); if (server.exitCode === null) { const exited = new Promise(r => server.once('exit', r)); server.kill(); await exited } }
})().catch(error => { console.error(error); process.exitCode = 1 })
