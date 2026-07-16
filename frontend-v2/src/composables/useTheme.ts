import { computed, ref } from 'vue'
import { darkTheme, type GlobalTheme } from 'naive-ui'
import { api } from '@/api/client'
import type { PluginTheme, PluginThemesResponse } from '@/api/types'
import { darkThemeOverrides, lightThemeOverrides } from '@/styles/theme'

export type ThemeName = 'dark' | 'light'

const STORAGE_KEY = 'trpg_theme'
const PLUGIN_THEME_KEY = 'diceframe_plugin_theme'

function readInitial(): ThemeName {
  if (typeof localStorage === 'undefined') return 'dark'
  return localStorage.getItem(STORAGE_KEY) === 'light' ? 'light' : 'dark'
}

const current = ref<ThemeName>(readInitial())
const pluginThemes = ref<PluginTheme[]>([])
const pluginThemeId = ref(typeof localStorage === 'undefined' ? '' : localStorage.getItem(PLUGIN_THEME_KEY) || '')
const appliedPluginVars = new Set<string>()

function applyBodyClass(name: ThemeName) {
  document.body.classList.toggle('light', name === 'light')
}
if (typeof document !== 'undefined') applyBodyClass(current.value)

function clearPluginVars() {
  if (typeof document === 'undefined') return
  const style = document.documentElement.style
  for (const key of appliedPluginVars) style.removeProperty(key)
  appliedPluginVars.clear()
}

function applyPluginVars(theme: PluginTheme | undefined) {
  clearPluginVars()
  if (!theme?.tokens || typeof document === 'undefined') return
  const values = {
    ...(theme.tokens.base || {}),
    ...(current.value === 'dark' ? theme.tokens.dark || {} : theme.tokens.light || {}),
  }
  const style = document.documentElement.style
  for (const [key, value] of Object.entries(values)) {
    if (!key.startsWith('--')) continue
    style.setProperty(key, value)
    appliedPluginVars.add(key)
  }
}

export function useTheme() {
  const naiveTheme = computed<GlobalTheme | null>(() => (current.value === 'dark' ? darkTheme : null))
  const overrides = computed(() => (current.value === 'dark' ? darkThemeOverrides : lightThemeOverrides))
  function apply(name: ThemeName) {
    current.value = name
    applyBodyClass(name)
    localStorage.setItem(STORAGE_KEY, name)
    applyPluginVars(pluginThemes.value.find(theme => theme.id === pluginThemeId.value))
  }
  function toggle() {
    apply(current.value === 'dark' ? 'light' : 'dark')
  }
  async function loadPluginThemes() {
    const response = await api<PluginThemesResponse>('/plugins/themes')
    pluginThemes.value = response.themes || []
    const selected = pluginThemes.value.find(theme => theme.id === pluginThemeId.value)
    if (selected) {
      applyPluginVars(selected)
    } else if (pluginThemeId.value) {
      clearPluginTheme()
    }
  }
  function applyPluginTheme(id: string | null) {
    const next = id || ''
    pluginThemeId.value = next
    if (next) localStorage.setItem(PLUGIN_THEME_KEY, next)
    else localStorage.removeItem(PLUGIN_THEME_KEY)
    applyPluginVars(pluginThemes.value.find(theme => theme.id === next))
  }
  function clearPluginTheme() {
    pluginThemeId.value = ''
    localStorage.removeItem(PLUGIN_THEME_KEY)
    clearPluginVars()
  }
  return {
    current,
    naiveTheme,
    overrides,
    pluginThemes,
    pluginThemeId,
    apply,
    toggle,
    loadPluginThemes,
    applyPluginTheme,
    clearPluginTheme,
  }
}
