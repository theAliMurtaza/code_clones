// Run against the isolated preview documented in UI-AUTH-SETUP.md.
const { chromium } = require('playwright')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
;(async () => {
  const output = path.resolve(__dirname, '../.ui-checks')
  fs.mkdirSync(output, { recursive: true })
  const browser = await chromium.launch({ channel: 'chrome', headless: true })
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 960 } })
    const errors = []
    page.on('pageerror', e => errors.push(e.message))
    // Font CDN availability is unrelated to local UI behavior.
    await page.route('https://fonts.googleapis.com/**', route => route.abort())
    await page.goto(process.env.UI_PREVIEW_URL || 'http://127.0.0.1:5174/', { waitUntil: 'domcontentloaded' })
    await page.getByRole('button', { name: 'Sign In', exact: true }).click()
    await page.getByRole('heading', { name: 'Welcome back' }).waitFor()
    await page.getByText('Google sign-in is not available yet.', { exact: false }).waitFor()
    assert(await page.getByRole('button', { name: 'Continue with Google' }).isDisabled())
    await page.screenshot({ path: path.join(output, 'sign-in-desktop.png'), fullPage: true })
    await page.setViewportSize({ width: 390, height: 844 })
    assert(await page.evaluate(() => document.querySelector('.auth-screen').scrollWidth <= innerWidth))
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    assert(await page.evaluate(() => document.documentElement.scrollHeight <= innerHeight))
    await page.screenshot({ path: path.join(output, 'sign-in-mobile.png'), fullPage: true })
    await page.setViewportSize({ width: 1440, height: 960 })
    await page.getByRole('button', { name: 'Create an account', exact: true }).click()
    await page.getByLabel('Full name').fill('Preview User')
    await page.getByLabel('Email address').fill(`preview-${Date.now()}@example.com`)
    await page.getByLabel('Password', { exact: true }).fill('Local-preview-password-2026')
    await page.getByRole('button', { name: 'Show password' }).click()
    assert.equal(await page.getByLabel('Password', { exact: true }).getAttribute('type'), 'text')
    await page.route('**/api/auth/register', async route => { await new Promise(r => setTimeout(r, 700)); await route.continue() })
    await page.getByRole('button', { name: 'Create account', exact: true }).click()
    await page.getByRole('heading', { name: 'Creating your account…' }).waitFor()
    await page.screenshot({ path: path.join(output, 'loading.png') })
    await page.getByText('Welcome, Preview User', { exact: true }).waitFor()
    const feedback = page.locator('.feedback-card').filter({ hasText: 'Welcome, Preview User' })
    const box = await feedback.boundingBox()
    assert(Math.abs(box.x + box.width / 2 - 720) < 20)
    assert(Math.abs(box.y + box.height / 2 - 480) < 70)
    await page.screenshot({ path: path.join(output, 'success.png') })
    await page.getByRole('button', { name: 'Dismiss notification' }).click()
    await page.getByRole('button', { name: 'New Analysis', exact: true }).first().click()
    await page.locator('input[type=file]').first().setInputFiles([
      path.resolve(__dirname, '../../examples/all-types-demo/folder/original.py'),
      path.resolve(__dirname, '../../examples/all-types-demo/folder/nested/exact.py'),
    ])
    // Slow, controlled API milestones let us inspect stages that a small real
    // analysis can complete between two polls. The final result stays real.
    const stages = ['queued', 'extracting', 'tokenizing', 'structural', 'semantic', 'preparing']
    let milestone = 0
    await page.route('**/api/jobs/*', async route => {
      const response = await route.fetch()
      const result = await response.json()
      if (result.status === 'done' && milestone < stages.length) {
        const stage = stages[milestone++]
        await route.fulfill({ response, body: JSON.stringify({ ...result, status: stage === 'queued' ? 'queued' : 'running',
          analysis_info: { progress: { stage, skipped_stages: [] } } }) })
      } else await route.fulfill({ response })
    })
    await page.getByRole('button', { name: /Run Clone Detection/ }).click()
    const steps = page.getByRole('list', { name: 'Processing steps' })
    for (const label of ['Queued', 'Fragments', 'Tokenizing', 'Comparing', 'Model analysis', 'Results']) {
      await steps.locator('[aria-current="step"]').filter({ hasText: label }).waitFor({ timeout: 15000 })
      if (label === 'Model analysis') await page.screenshot({ path: path.join(output, 'processing-running.png') })
    }
    await page.getByRole('heading', { name: 'Analysis Complete', exact: true }).waitFor({ timeout: 60000 })
    assert.equal(await page.getByRole('list', { name: 'Processing steps' }).getByRole('listitem').count(), 7)
    assert.equal(await page.getByRole('progressbar').getAttribute('aria-valuenow'), '6')
    await page.screenshot({ path: path.join(output, 'processing-complete.png') })
    await page.getByRole('button', { name: 'View Clone Results' }).click()
    await page.getByRole('heading', { name: 'Analysis overview' }).waitFor({ timeout: 60000 })
    assert.equal(await page.getByText('Clone analysis coverage', { exact: true }).count(), 0)
    assert(await page.getByText('Type-4 · Not checked', { exact: true }).isVisible())
    const notices = page.getByRole('button', { name: 'Dismiss notification' })
    while (await notices.count()) await notices.first().click()
    await page.screenshot({ path: path.join(output, 'results.png'), fullPage: true })
    assert.deepEqual(errors, [])
    console.log('UI checks passed: responsive auth, Google unavailable state, registration, centered loading/success, analysis results; no browser errors.')
  } finally { await browser.close() }
})().catch(error => { console.error(error); process.exitCode = 1 })
