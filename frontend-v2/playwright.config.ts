import { defineConfig,devices } from '@playwright/test'
export default defineConfig({testDir:'./e2e',use:{baseURL:'http://127.0.0.1:18000',locale:'zh-CN',trace:'retain-on-failure'},projects:[{name:'desktop',use:{...devices['Desktop Chrome']}},{name:'mobile',use:{...devices['Pixel 5']}}]})
