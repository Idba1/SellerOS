// Uses the same externally supplied Playwright runtime as the existing shell smoke check.
const { chromium } = require('playwright')
const { spawn } = require('node:child_process')
const assert = require('node:assert/strict')
const path = require('node:path')

;(async () => {
  const root = path.resolve(__dirname, '..')
  const port = '18768'
  const server = spawn(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', port, '--strictPort'], { cwd: root, stdio: 'pipe', windowsHide: true })
  let serverOutput = ''
  server.stdout.on('data', chunk => { serverOutput += chunk })
  server.stderr.on('data', chunk => { serverOutput += chunk })
  let browser
  try {
    let ready = false
    for (let attempt = 0; attempt < 60; attempt++) {
      if (server.exitCode !== null) throw new Error(`Authentication test server exited before it became ready. ${serverOutput}`)
      try { ready = (await fetch(`http://127.0.0.1:${port}/login`)).ok } catch {}
      if (ready) break
      await new Promise(resolve => setTimeout(resolve, 250))
    }
    assert.ok(ready, `Authentication test server starts. ${serverOutput}`)
    browser = await chromium.launch({ channel: 'msedge', headless: true })
    const page = await browser.newPage()
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })

    await page.goto(`http://127.0.0.1:${port}/login`)
    assert.equal(await page.getByRole('heading', { name: 'Welcome back' }).count(), 1)
    assert.equal(await page.locator('.app-shell').count(), 0)
    const submitButton = page.locator('form').getByRole('button', { name: 'Sign in' })
    assert.equal(await submitButton.isDisabled(), false)
    await submitButton.click()
    assert.equal(await page.getByText('Enter your email address.', { exact: true }).count(), 1)
    assert.equal(await page.getByText('Enter your password.', { exact: true }).count(), 1)
    await page.getByLabel('Email address').fill('seller@example.test')
    await page.getByLabel('Password').fill('not-a-real-password')
    assert.equal(await submitButton.isDisabled(), false)
    await submitButton.click()
    assert.equal(await page.getByRole('alert').count(), 1)
    assert.ok((await page.getByRole('alert').textContent()).includes('unavailable'))

    await page.getByRole('button', { name: 'Create account' }).click()
    assert.equal(await page.getByRole('heading', { name: 'Create your account' }).count(), 1)
    assert.ok((await page.getByText('Use at least 12 characters.', { exact: false }).count()) > 0)
    await page.goto(`http://127.0.0.1:${port}/forgot-password`)
    assert.equal(await page.getByRole('heading', { name: 'Forgot your password?' }).count(), 1)
    assert.equal(await page.locator('input').count(), 0)
    await page.goto(`http://127.0.0.1:${port}/reset-password`)
    assert.equal(await page.getByRole('heading', { name: 'Set a new password' }).count(), 1)

    for (const width of [375, 1280]) {
      await page.setViewportSize({ width, height: 800 })
      await page.goto(`http://127.0.0.1:${port}/login`)
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `No horizontal overflow at ${width}px`)
    }
    assert.deepEqual(errors, [])
    console.log('PASS: authentication routes, validation feedback, unavailable recovery state, and responsive layout')
  } finally {
    if (browser) await browser.close()
    if (server.exitCode === null) {
      const exited = new Promise(resolve => server.once('exit', resolve))
      server.kill()
      await exited
    }
  }
})().catch(error => { console.error(error); process.exitCode = 1 })
