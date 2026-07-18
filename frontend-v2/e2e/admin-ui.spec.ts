import { expect, test } from '@playwright/test'
import { accessToken } from './support'

const token = accessToken

test('settings status summary and destructive confirmations are explicit', async ({ page }) => {
  await page.addInitScript(value => localStorage.setItem('trpg_access_token', value), token())

  await page.goto('/#/settings')
  const statusCards = page.locator('.system-status-card')
  await expect(statusCards.filter({ hasText: '主模型' })).toBeVisible()
  await expect(statusCards.filter({ hasText: '备用回退' })).toBeVisible()
  await expect(statusCards.filter({ hasText: '向量记忆' })).toBeVisible()
  await expect(statusCards.filter({ hasText: '访问控制' })).toBeVisible()

  await page.goto('/')
  await page.getByRole('button', { name: '删除' }).first().click()
  await expect(page.getByText('删除存档').first()).toBeVisible()
  await expect(page.getByRole('button', { name: '删除存档' })).toBeVisible()
  await page.getByRole('button', { name: '取消' }).click()
})
test('rules page exposes structured editing for copied rules', async ({ page }) => {
  await page.addInitScript(value => localStorage.setItem('trpg_access_token', value), token())
  await page.goto('/#/rules')
  await page.getByRole('button', { name: '复制并编辑' }).first().click()
  await expect(page.getByRole('heading', { name: '复制并编辑规则' })).toBeVisible()
  await expect(page.getByLabel('规则 ID')).toBeVisible()
  await expect(page.getByLabel('规则名称')).toBeVisible()
  await expect(page.locator('.rule-editor-section').filter({ hasText: '属性' })).toBeVisible()
  await expect(page.getByText('高级 JSON')).toBeVisible()
  await page.getByRole('button', { name: '取消' }).click()
})
