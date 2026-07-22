import { expect, test } from '@playwright/test'
import { accessToken } from './support'

test('new shell and Vue login route render', async ({ page }) => {
  const token = accessToken()
  await page.addInitScript(value => localStorage.setItem('trpg_access_token', value), token)
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '游戏总览' })).toBeVisible()
  await page.goto('/#/login')
  await expect(page.getByRole('heading', { name: 'DiceFrame' })).toBeVisible()
})

test('direct share route follows browser locale and exposes a language switch', async ({ browser }) => {
  const context = await browser.newContext({ locale: 'en-US' })
  const page = await context.newPage()
  await page.goto('/#/join?game=missing&share=1')

  const locale = page.locator('.join-actions select')
  await expect(locale).toHaveValue('en')
  await locale.selectOption('zh-CN')
  await expect(locale).toHaveValue('zh-CN')
  await context.close()
})
