const { chromium } = require('playwright')
const { spawn } = require('node:child_process')
const assert = require('node:assert/strict')
const path = require('node:path')

;(async () => {
  const root = path.resolve(__dirname, '..')
  const server = spawn(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '18768', '--strictPort'], { cwd: root, stdio: 'pipe', windowsHide: true })
  let browser
  try {
    let ready = false
    for (let attempt = 0; attempt < 60; attempt++) {
      if (server.exitCode !== null) throw new Error('Form primitive test server exited')
      try { ready = (await fetch('http://127.0.0.1:18768/tests/form-fixture.html')).ok } catch {}
      if (ready) break
      await new Promise(resolve => setTimeout(resolve, 250))
    }
    assert.ok(ready, 'Form primitive test server starts')
    browser = await chromium.launch({ channel: 'msedge', headless: true })
    const page = await browser.newPage()
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })
    await page.goto('http://127.0.0.1:18768/tests/form-fixture.html')
    const productName = page.getByLabel('Product name *')
    await productName.focus()
    await page.keyboard.press('Tab')
    assert.equal(await page.locator(':focus').getAttribute('id'), 'category')
    await page.getByRole('button', { name: 'Validate field' }).click()
    assert.equal(await productName.getAttribute('aria-invalid'), 'true')
    assert.ok((await productName.getAttribute('aria-describedby')).includes('product-name-error'))
    assert.equal(await page.locator('#product-name-error').textContent(), 'Enter a product name.')
    await productName.fill('Canvas tote')
    await page.getByRole('button', { name: 'Validate field' }).click()
    assert.equal(await productName.getAttribute('aria-invalid'), null)
    await page.getByRole('button', { name: 'Open confirmation' }).focus()
    await page.keyboard.press('Enter')
    assert.equal(await page.locator('dialog[open]').count(), 1)
    assert.equal(await page.locator(':focus').textContent(), 'Cancel')
    await page.keyboard.press('Escape')
    assert.equal(await page.locator('dialog[open]').count(), 0)
    assert.equal(await page.getByTestId('confirmation-result').textContent(), 'Cancelled')
    await page.getByRole('button', { name: 'Open confirmation' }).click()
    await page.getByRole('button', { name: 'Confirm action' }).click()
    assert.equal(await page.getByTestId('confirmation-result').textContent(), 'Confirmed')
    assert.equal(await page.getByRole('heading', { name: 'Loading fixture' }).count(), 1)
    assert.equal(await page.locator('[aria-busy="true"]').count(), 1)
    await page.getByRole('button', { name: 'Retry fixture' }).focus()
    await page.keyboard.press('Enter')
    assert.equal(await page.getByTestId('retry-count').textContent(), 'Retries: 1')
    assert.deepEqual(errors, [])
    console.log('PASS: field labels/descriptions/errors, keyboard focus, confirmation Escape/confirm, and loading/empty/error states')
  } finally {
    if (browser) await browser.close()
    if (server.exitCode === null) {
      const exited = new Promise(resolve => server.once('exit', resolve))
      server.kill()
      await exited
    }
  }
})().catch(error => { console.error(error); process.exitCode = 1 })
