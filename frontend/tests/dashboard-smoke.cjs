// Uses the existing external Playwright runtime; the fixture never fabricates dashboard metrics.
const { chromium } = require('playwright')
const { spawn } = require('node:child_process')
const assert = require('node:assert/strict')
const path = require('node:path')

;(async () => {
  const root = path.resolve(__dirname, '..')
  const port = '18770'
  const server = spawn(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', port, '--strictPort'], { cwd: root, stdio: 'pipe', windowsHide: true })
  let serverOutput = ''
  server.stdout.on('data', chunk => { serverOutput += chunk })
  server.stderr.on('data', chunk => { serverOutput += chunk })
  let browser
  try {
    let ready = false
    for (let attempt = 0; attempt < 60; attempt++) {
      if (server.exitCode !== null) throw new Error(`Dashboard test server exited before it became ready. ${serverOutput}`)
      try { ready = (await fetch(`http://127.0.0.1:${port}/`)).ok } catch {}
      if (ready) break
      await new Promise(resolve => setTimeout(resolve, 250))
    }
    assert.ok(ready, `Dashboard test server starts. ${serverOutput}`)
    browser = await chromium.launch({ channel: 'msedge', headless: true })
    const page = await browser.newPage()
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })

    await page.goto(`http://127.0.0.1:${port}/`)
    assert.equal(await page.getByRole('heading', { name: 'Dashboard', exact: true }).count(), 1)
    assert.equal(await page.getByRole('heading', { name: 'Sign in to view your dashboard' }).count(), 1)
    assert.equal(await page.locator('.dashboard-kpi').count(), 0)

    await page.addInitScript(() => window.sessionStorage.setItem('selleros.auth.session.v1', JSON.stringify({ account: { id: '00000000-0000-4000-8000-000000000001', email: 'seller@example.test' }, token: 'not-a-real-token' })))
    await page.goto(`http://127.0.0.1:${port}/`)
    await page.getByLabel('From').fill('2026-01-31')
    await page.getByLabel('To').fill('2026-01-01')
    assert.equal(await page.getByRole('alert').count(), 1)
    await page.getByLabel('To').fill('2026-01-31')
    await page.locator('form').getByRole('button', { name: 'Load overview' }).click()
    assert.equal(await page.getByRole('heading', { name: 'Unable to load dashboard data' }).count(), 1)
    assert.ok((await page.getByText('frontend API URL is configured.', { exact: false }).count()) > 0)

    for (const width of [375, 1280]) {
      await page.setViewportSize({ width, height: 800 })
      await page.goto(`http://127.0.0.1:${port}/`)
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `No horizontal overflow at ${width}px`)
    }
    assert.deepEqual(errors, [])
    console.log('PASS: dashboard signed-out, validation, configuration-error, and responsive states')
  } finally {
    if (browser) await browser.close()
    if (server.exitCode === null) {
      const exited = new Promise(resolve => server.once('exit', resolve))
      server.kill()
      await exited
    }
  }
})().catch(error => { console.error(error); process.exitCode = 1 })
