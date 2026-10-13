// Uses an externally supplied Playwright installation; no project dependency added.
const { chromium } = require('playwright')
const { spawn } = require('node:child_process')
const assert = require('node:assert/strict')
const path = require('node:path')

;(async () => {
  const root = path.resolve(__dirname, '..')
  const server = spawn(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '18767', '--strictPort'], { cwd: root, stdio: 'pipe', windowsHide: true })
  let browser
  try {
    let ready = false
    for (let attempt = 0; attempt < 60; attempt++) {
      if (server.exitCode !== null) throw new Error('Test server exited')
      try { ready = (await fetch('http://127.0.0.1:18767/')).ok } catch {}
      if (ready) break
      await new Promise(resolve => setTimeout(resolve, 250))
    }
    assert.ok(ready, 'Test server starts')
    browser = await chromium.launch({ channel: 'msedge', headless: true })
    const page = await browser.newPage()
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })
    await page.goto('http://127.0.0.1:18767/')
    const links = await page.locator('nav a').evaluateAll(items => items.map(item => ({ path: item.getAttribute('href'), title: item.textContent })))
    assert.equal(links.length, 13)
    for (const link of links) {
      await page.goto(`http://127.0.0.1:18767${link.path}`)
      assert.equal(await page.locator('h1').textContent(), link.title)
      assert.equal(await page.locator('nav a[aria-current="page"]').count(), 1)
      assert.equal(await page.title(), `${link.title} | SellerOS`)
    }
    await page.goto('http://127.0.0.1:18767/products/?example=1')
    assert.equal(await page.locator('h1').textContent(), 'Products')
    await page.goto('http://127.0.0.1:18767/missing-page')
    assert.equal(await page.locator('h1').textContent(), 'Page not found')
    assert.equal(await page.locator('nav a[aria-current]').count(), 0)
    await page.getByRole('link', { name: 'Return to dashboard' }).click()
    assert.equal(await page.locator('h1').textContent(), 'Dashboard')
    await page.goto('http://127.0.0.1:18767/')
    await page.keyboard.press('Tab')
    assert.equal(await page.locator(':focus').textContent(), 'Skip to main content')
    await page.keyboard.press('Enter')
    assert.equal(await page.locator(':focus').getAttribute('id'), 'main-content')
    await page.goto('http://127.0.0.1:18767/')
    await page.keyboard.press('Tab') // skip link
    await page.keyboard.press('Tab') // brand
    await page.keyboard.press('Tab') // dashboard
    await page.keyboard.press('Tab') // products
    assert.equal(await page.locator(':focus').textContent(), 'Products')
    await page.keyboard.press('Enter')
    await page.waitForURL('**/products')
    assert.equal(await page.locator('h1').textContent(), 'Products')
    for (const width of [375, 1280]) {
      await page.setViewportSize({ width, height: 800 })
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `No horizontal overflow at ${width}`)
    }
    assert.deepEqual(errors, [])
    console.log('PASS: 13 routes, direct URLs, trailing slash, 404 recovery, keyboard skip/navigation, mobile/desktop overflow, and console checks')
  } finally {
    if (browser) await browser.close()
    if (server.exitCode === null) {
      const exited = new Promise(resolve => server.once('exit', resolve))
      server.kill()
      await exited
    }
  }
})().catch(error => { console.error(error); process.exitCode = 1 })
