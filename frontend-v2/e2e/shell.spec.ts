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
