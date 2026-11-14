import { test, expect } from '@playwright/test'
const pdf = { name: 'proposal.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-fixture') }
const finding = { text: 'A cycle lane is proposed.', evidence: [{ page: 1, quote: 'A cycle lane is proposed.' }] }
const result = { document_title: 'Transportation proposal', summary: finding, proposed_changes: [finding], affected_groups: [], potential_benefits: [], potential_tradeoffs: [], participation: [], unknowns: ['No consultation deadline is stated.'] }

test('upload, evidence, focus and responsive results', async ({ page }, testInfo) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/')
  const submit = page.getByRole('button', { name: 'Explore this proposal' })
  const input = page.getByLabel('Choose a municipal PDF')
  await expect(submit).toBeDisabled()
  await testInfo.attach('upload', { body: await page.screenshot({ fullPage: true }), contentType: 'image/png' })
  await input.setInputFiles({ name: 'bad.txt', mimeType: 'text/plain', buffer: Buffer.from('bad') })
  await expect(page.getByRole('alert')).toContainText('Choose a PDF')
  await input.setInputFiles(pdf)
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/analyze', async route => { await gate; await route.fulfill({ json: result }) })
  await submit.click()
  await expect(input).toBeDisabled()
  await expect(page.getByRole('status')).toContainText('checking supporting excerpts')
  release()
  await expect(page.getByRole('heading', { name: result.document_title })).toBeFocused()
  await page.locator('summary').first().click()
  await expect(page.getByRole('link', { name: 'PDF page 1' }).first()).toHaveAttribute('href', /blob:.*#page=1$/)
  await expect(page.getByText('No consultation deadline is stated.')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await testInfo.attach('results', { body: await page.screenshot({ fullPage: true }), contentType: 'image/png' })
  await input.setInputFiles({ ...pdf, name: 'second.pdf' })
  await expect(page.getByRole('heading', { name: result.document_title })).toHaveCount(0)
  expect(errors).toEqual([])
})

test('malformed response, provider error and cancellation recover', async ({ page }) => {
  await page.goto('/')
  const input = page.getByLabel('Choose a municipal PDF')
  const submit = page.getByRole('button', { name: 'Explore this proposal' })
  await input.setInputFiles(pdf)
  await page.route('**/api/analyze', route => route.fulfill({ json: { wrong: 'shape' } }))
  await submit.click()
  await expect(page.getByRole('alert')).toContainText('incomplete analysis')
  await page.unroute('**/api/analyze')
  await page.route('**/api/analyze', route => route.fulfill({ status: 503, json: { detail: 'Service unavailable. Please retry.' } }))
  await submit.click()
  await expect(page.getByRole('alert')).toContainText('Service unavailable')
  await page.unroute('**/api/analyze')
  await page.route('**/api/analyze', () => {})
  await submit.click()
  await page.getByRole('button', { name: 'Cancel', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('cancelled')
  await expect(input).toBeEnabled()
})
