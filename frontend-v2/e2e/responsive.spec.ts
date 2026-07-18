import { expect, test } from '@playwright/test'
import { accessToken } from './support'

test('layout has no document overflow', async ({ page }) => {
  const token = accessToken()
  await page.addInitScript(value => localStorage.setItem('trpg_access_token', value), token)
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '游戏总览' })).toBeVisible()
  const sizes = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    client: document.documentElement.clientWidth,
  }))
  expect(sizes.scroll).toBe(sizes.client)
})

test('all required viewport widths remain contained', async ({ page }) => {
  const token = accessToken()
  await page.addInitScript(value => localStorage.setItem('trpg_access_token', value), token)
  for (const width of [360, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/')
    await expect(page.getByRole('heading', { name: '游戏总览' })).toBeVisible()
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow, `overflow at ${width}px`).toBe(0)
  }
})
