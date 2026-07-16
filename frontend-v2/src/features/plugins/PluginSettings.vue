<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  NButton, NCheckbox, NCollapse, NCollapseItem, NIcon, NInput, NInputNumber,
  NSelect, NSpin, NSwitch, NTabPane, NTabs, NTag,
} from 'naive-ui'
import {
  AddOutline, ChevronDown, ChevronUp, CloudDownloadOutline, CreateOutline,
  ExtensionPuzzleOutline, RefreshOutline, TrashOutline,
} from '@vicons/ionicons5'
import { api, errorMessage } from '@/api/client'
import { useToast } from '@/composables/useToast'
import type {
  PluginField, PluginInfo, PluginMarketplaceItem, PluginMarketplaceResponse,
  PluginMirror, PluginMirrorsResponse, PluginMirrorTestResponse,
} from '@/api/types'
import NapcatGuide from '@/components/plugins/NapcatGuide.vue'

const toast = useToast()
const plugins = ref<PluginInfo[]>([])
const marketplace = ref<PluginMarketplaceItem[]>([])
const mirrors = ref<PluginMirror[]>([])
const mirrorTests = ref<Record<string, string>>({})
const marketplaceSource = ref<PluginMarketplaceResponse['source'] | null>(null)
const expandedPluginNames = ref<string[]>([])
const loading = ref(false)
const marketLoading = ref(false)
const mirrorLoading = ref(false)
const busy = ref('')
const installFile = ref<File | null>(null)
const overwriteInstall = ref(false)
const marketKeyword = ref('')
const newMirror = reactive<PluginMirror>({
  id: '',
  name: '',
  raw_prefix: '',
  clone_prefix: '',
  enabled: true,
  priority: 1,
})

const filteredMarketplace = computed(() => {
  const keyword = marketKeyword.value.trim().toLowerCase()
  if (!keyword) return marketplace.value
  return marketplace.value.filter(item => [
    item.id, item.name, item.description, item.repository_url, ...(item.tags || []),
  ].some(value => String(value || '').toLowerCase().includes(keyword)))
})

async function load() {
  loading.value = true
  try {
    const r = await api<{ plugins: PluginInfo[] }>('/plugins')
    plugins.value = r.plugins || []
    if (!expandedPluginNames.value.length) expandedPluginNames.value = plugins.value.map(p => p.id)
  } catch (e: unknown) {
    toast.error(errorMessage(e))
  } finally {
    loading.value = false
  }
}

async function loadMarketplace() {
  marketLoading.value = true
  try {
    const r = await api<PluginMarketplaceResponse>('/plugins/marketplace')
    if (!r.ok) throw new Error(r.error || '插件商店读取失败')
    marketplace.value = r.plugins || []
    marketplaceSource.value = r.source || null
  } catch (e: unknown) {
    toast.error(errorMessage(e))
  } finally {
    marketLoading.value = false
  }
}

async function loadMirrors() {
  mirrorLoading.value = true
  try {
    const r = await api<PluginMirrorsResponse>('/plugins/mirrors')
    mirrors.value = r.mirrors || []
  } catch (e: unknown) {
    toast.error(errorMessage(e))
  } finally {
    mirrorLoading.value = false
  }
}

function ordered(p: PluginInfo): [string, PluginField][] {
  return Object.entries(p.schema?.properties || {}).sort((a, b) => (a[1].ui?.order || 0) - (b[1].ui?.order || 0))
}
function value(p: PluginInfo, key: string, field: PluginField): unknown {
  const v = p.config?.[key]
  return typeof v === 'object' && field.ui?.sensitive ? '' : v ?? field.default ?? ''
}
function textValue(p: PluginInfo, key: string, field: PluginField): string {
  const v = value(p, key, field)
  return typeof v === 'string' ? v : v === undefined || v === null ? '' : String(v)
}
function selectValue(p: PluginInfo, key: string, field: PluginField): string | number | null {
  const v = value(p, key, field)
  return typeof v === 'string' || typeof v === 'number' ? v : null
}
function numberValue(p: PluginInfo, key: string, field: PluginField): number | null {
  const v = value(p, key, field)
  return typeof v === 'number' ? v : v === '' || v === null || v === undefined ? null : Number(v)
}
function set(p: PluginInfo, key: string, v: unknown) {
  if (!p.config) p.config = {}
  p.config[key] = v
}
function listValue(p: PluginInfo, key: string, field: PluginField): string[] {
  const v = value(p, key, field)
  return Array.isArray(v) ? v : []
}
function secretPlaceholder(p: PluginInfo, key: string, field: PluginField): string {
  const v = p.config?.[key] as { configured?: boolean; masked?: string } | undefined
  return field.ui?.sensitive && v?.configured ? `已配置 ${v.masked}，留空不修改` : ''
}
function showGroup(fields: [string, PluginField][], index: number): boolean {
  const group = fields[index][1].ui?.group
  return !!group && (index === 0 || fields[index - 1][1].ui?.group !== group)
}
function parseList(input: string): string[] {
  return Array.from(new Set(input.split(/[\n,]+/).map(x => x.trim()).filter(Boolean)))
}
function validate(p: PluginInfo): string {
  for (const [key, field] of ordered(p)) {
    const v = value(p, key, field)
    if (field.type === 'number' || field.type === 'integer') {
      const n = Number(v)
      if (field.exclusiveMinimum !== undefined && n <= field.exclusiveMinimum) return `${field.title || key} 必须大于 ${field.exclusiveMinimum}`
      if (field.minimum !== undefined && n < field.minimum) return `${field.title || key} 不能小于 ${field.minimum}`
      if (field.maximum !== undefined && n > field.maximum) return `${field.title || key} 不能大于 ${field.maximum}`
    }
    if (field.type === 'string') {
      const s = String(v || '')
      if (field.minLength !== undefined && s.length > 0 && s.length < field.minLength) return `${field.title || key} 至少 ${field.minLength} 位`
      if (field.maxLength !== undefined && s.length > field.maxLength) return `${field.title || key} 最多 ${field.maxLength} 位`
    }
  }
  return ''
}
async function save(p: PluginInfo) {
  const err = validate(p)
  if (err) { toast.error(err); return }
  busy.value = p.id
  try {
    const payload: Record<string, unknown> = {}
    for (const [key, field] of ordered(p)) {
      const current = p.config?.[key]
      if (field.ui?.sensitive) {
        if (typeof current === 'string' && current.trim()) payload[key] = current
      } else if (current !== undefined) {
        payload[key] = current
      }
    }
    await api(`/plugins/${encodeURIComponent(p.id)}/config`, { method: 'PUT', body: JSON.stringify(payload) })
    toast.success(`${p.name} 已保存`)
    await load()
  } catch (e: unknown) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = ''
  }
}
async function restart(p: PluginInfo) {
  busy.value = p.id
  try {
    await api(`/plugins/${encodeURIComponent(p.id)}/restart`, { method: 'POST' })
    toast.success(`${p.name} 已请求重启`)
    await load()
  } catch (e: unknown) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = ''
  }
}
async function clearCardCache(p: PluginInfo) {
  if (!window.confirm('确定清理 QQ 卡片缓存吗？只会删除 data/bot/cards 里的临时 card_*.png。')) return
  busy.value = `${p.id}:card-cache`
  try {
    const r = await api<{ deleted?: number; bytes_deleted?: number }>(`/plugins/${encodeURIComponent(p.id)}/card-cache/clear`, { method: 'POST' })
    const deleted = r.deleted || 0
    const mb = ((r.bytes_deleted || 0) / 1024 / 1024).toFixed(2)
    toast.success(`已清理 ${deleted} 张卡片，释放 ${mb} MB`)
  } catch (e: unknown) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = ''
  }
}
async function toggleRunning(p: PluginInfo, on: boolean) {
  busy.value = p.id
  try {
    await api(`/plugins/${encodeURIComponent(p.id)}/${on ? 'start' : 'stop'}`, { method: 'POST' })
    toast.success(`${p.name} 已${on ? '启动' : '停止'}`)
    await load()
  } catch (e: unknown) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = ''
  }
}
function onPluginFile(event: Event) {
  const input = event.target as HTMLInputElement
  installFile.value = input.files?.[0] || null
}
async function installPlugin() {
  if (!installFile.value) {
    toast.error('请选择插件 zip 包')
    return
  }
  busy.value = 'install'
  try {
    const body = new FormData()
    body.append('file', installFile.value)
    body.append('overwrite', overwriteInstall.value ? 'true' : 'false')
    await api('/plugins/install', { method: 'POST', body })
    toast.success('插件已安装')
    installFile.value = null
    overwriteInstall.value = false
    await load()
    await loadMarketplace()
  } catch (e: unknown) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = ''
  }
}
async function installMarketPlugin(item: PluginMarketplaceItem) {
  busy.value = `market:${item.id}`
  try {
    await api('/plugins/marketplace/install', {
      method: 'POST',
      body: JSON.stringify({ plugin_id: item.id, overwrite: item.installed }),
    })
    toast.success(`${item.name} 已${item.installed ? '更新' : '安装'}`)
    await load()
    await loadMarketplace()
  } catch (e: unknown) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = ''
  }
}
async function updateInstalledPlugin(p: PluginInfo) {
  busy.value = `${p.id}:update`
  try {
    await api(`/plugins/${encodeURIComponent(p.id)}/update`, { method: 'POST' })
    toast.success(`${p.name} 已更新`)
    await load()
    await loadMarketplace()
  } catch (e: unknown) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = ''
  }
}
async function uninstallPlugin(p: PluginInfo) {
  const message = `确定卸载 ${p.name} 吗？默认会保留插件配置和运行数据。`
  if (!window.confirm(message)) return
  busy.value = `${p.id}:uninstall`
  try {
    await api(`/plugins/${encodeURIComponent(p.id)}`, { method: 'DELETE', body: JSON.stringify({ delete_data: false }) })
    toast.success(`${p.name} 已卸载`)
    await load()
    await loadMarketplace()
  } catch (e: unknown) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = ''
  }
}
async function addMirror() {
  busy.value = 'mirror:add'
  try {
    await api('/plugins/mirrors', { method: 'POST', body: JSON.stringify(newMirror) })
    toast.success('镜像源已添加')
    Object.assign(newMirror, { id: '', name: '', raw_prefix: '', clone_prefix: '', enabled: true, priority: mirrors.value.length + 1 })
    await loadMirrors()
  } catch (e: unknown) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = ''
  }
}
async function saveMirror(mirror: PluginMirror, patch: Partial<PluginMirror>) {
  busy.value = `mirror:${mirror.id}`
  try {
    await api(`/plugins/mirrors/${encodeURIComponent(mirror.id)}`, { method: 'PUT', body: JSON.stringify(patch) })
    await loadMirrors()
  } catch (e: unknown) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = ''
  }
}
async function deleteMirror(mirror: PluginMirror) {
  if (!window.confirm(`确定删除镜像源 ${mirror.name} 吗？`)) return
  busy.value = `mirror:${mirror.id}`
  try {
    await api(`/plugins/mirrors/${encodeURIComponent(mirror.id)}`, { method: 'DELETE' })
    toast.success('镜像源已删除')
    await loadMirrors()
  } catch (e: unknown) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = ''
  }
}
async function testMirror(mirror?: PluginMirror) {
  const key = mirror?.id || 'all'
  busy.value = `mirror-test:${key}`
  try {
    const r = await api<PluginMirrorTestResponse>('/plugins/mirrors/test', {
      method: 'POST',
      body: JSON.stringify({ mirror_id: mirror?.id || '' }),
    })
    for (const result of r.results || []) {
      const id = result.mirror_id || 'all'
      mirrorTests.value[id] = result.ok
        ? `可用，${result.elapsed_ms || 0} ms`
        : `失败：${result.error || result.status || '未知错误'}`
    }
    toast[r.ok ? 'success' : 'error'](r.ok ? '镜像测试完成' : (r.error || '所有镜像测试失败'))
  } catch (e: unknown) {
    toast.error(errorMessage(e))
  } finally {
    busy.value = ''
  }
}
function openUrl(url?: string) {
  if (url) window.open(url, '_blank', 'noopener')
}

onMounted(async () => {
  await load()
  await Promise.all([loadMarketplace(), loadMirrors()])
})
</script>

<template>
  <NTabs type="line" animated>
    <NTabPane name="installed" tab="已安装">
      <NSpin :show="loading">
        <section class="plugin-install">
          <div>
            <h3>安装插件</h3>
            <p class="muted">选择符合 DiceFrame 插件标准的 zip 包。</p>
          </div>
          <div class="install-controls">
            <input type="file" accept=".zip,application/zip" aria-label="插件 zip 包" @change="onPluginFile">
            <NCheckbox v-model:checked="overwriteInstall">覆盖同 ID 插件</NCheckbox>
            <NButton type="primary" :disabled="!installFile" :loading="busy === 'install'" @click="installPlugin">
              <template #icon><NIcon :component="CloudDownloadOutline" /></template>
              安装
            </NButton>
          </div>
        </section>

        <p v-if="!plugins.length" class="muted">暂无可用插件。</p>

        <NCollapse v-model:expanded-names="expandedPluginNames">
          <NCollapseItem v-for="p in plugins" :key="p.id" :name="p.id" class="plugin-collapsible">
            <template #header>
              <div class="plugin-head">
                <h3>{{ p.name }}</h3>
                <p class="muted">{{ p.description }}</p>
              </div>
            </template>
            <template #header-extra>
              <div class="plugin-extra" @click.stop>
                <NTag :type="p.running ? 'success' : 'default'" size="small">{{ p.status }}</NTag>
                <NSwitch :value="p.running" :disabled="busy === p.id" @update:value="toggleRunning(p, $event)" />
              </div>
            </template>

            <NTabs type="line" animated class="plugin-tabs">
              <NTabPane name="config" tab="配置">
                <div class="plugin-form-grid">
                  <template v-for="(entry, i) in ordered(p)" :key="entry[0]">
                    <h4 v-if="showGroup(ordered(p), i)" class="field-group">{{ entry[1].ui?.group }}</h4>
                    <div class="field" :class="{ 'field-wide': entry[1].type === 'array' }">
                      <label v-if="entry[1].type === 'boolean'" class="switch-label">
                        <NSwitch :value="!!value(p, entry[0], entry[1])" :aria-label="entry[1].title || entry[0]" @update:value="set(p, entry[0], $event)" />
                        <span>{{ entry[1].title || entry[0] }}</span>
                      </label>
                      <label v-else class="input-label">
                        <span class="field-title">{{ entry[1].title || entry[0] }}</span>
                        <NSelect
                          v-if="entry[1].enum"
                          :value="selectValue(p, entry[0], entry[1])"
                          :options="(entry[1].enum || []).map(x => ({ label: x, value: x }))"
                          @update:value="set(p, entry[0], $event)"
                        />
                        <NInput
                          v-else-if="entry[1].type === 'array'"
                          type="textarea"
                          :rows="4"
                          :input-props="{ 'aria-label': entry[1].title || entry[0] }"
                          :value="listValue(p, entry[0], entry[1]).join('\n')"
                          placeholder="每行一个，或用逗号分隔（自动去重）"
                          @update:value="set(p, entry[0], parseList($event))"
                        />
                        <NInput
                          v-else-if="entry[1].ui?.sensitive"
                          type="password"
                          show-password-on="click"
                          :placeholder="secretPlaceholder(p, entry[0], entry[1])"
                          :value="textValue(p, entry[0], entry[1])"
                          @update:value="set(p, entry[0], $event)"
                        />
                        <NInputNumber
                          v-else-if="entry[1].type === 'number' || entry[1].type === 'integer'"
                          :value="numberValue(p, entry[0], entry[1])"
                          @update:value="set(p, entry[0], $event)"
                        />
                        <NInput
                          v-else
                          :value="textValue(p, entry[0], entry[1])"
                          @update:value="set(p, entry[0], $event)"
                        />
                      </label>
                      <small v-if="entry[1].description" class="muted">{{ entry[1].description }}</small>
                    </div>
                  </template>
                </div>
              </NTabPane>
              <NTabPane v-if="p.id === 'qq-napcat'" name="guide" tab="说明文档">
                <NapcatGuide />
              </NTabPane>
            </NTabs>

            <div class="actions-row">
              <NButton type="primary" :loading="busy === p.id" @click="save(p)">保存配置</NButton>
              <NButton :loading="busy === p.id" @click="restart(p)">
                <template #icon><NIcon :component="RefreshOutline" /></template>
                重启插件
              </NButton>
              <NButton secondary :loading="busy === `${p.id}:update`" @click="updateInstalledPlugin(p)">
                <template #icon><NIcon :component="CloudDownloadOutline" /></template>
                从商店更新
              </NButton>
              <NButton v-if="p.id === 'qq-napcat'" secondary :loading="busy === `${p.id}:card-cache`" @click="clearCardCache(p)">清理卡片缓存</NButton>
              <NButton tertiary type="error" :loading="busy === `${p.id}:uninstall`" @click="uninstallPlugin(p)">
                <template #icon><NIcon :component="TrashOutline" /></template>
                卸载插件
              </NButton>
            </div>
            <p class="muted hint">修改令牌 / 连接参数后，需重启插件才会生效。</p>
          </NCollapseItem>
        </NCollapse>
      </NSpin>
    </NTabPane>

    <NTabPane name="marketplace" tab="插件商店">
      <section class="toolbar-row">
        <NInput v-model:value="marketKeyword" placeholder="搜索插件名称、ID、标签或仓库" clearable />
        <NButton :loading="marketLoading" @click="loadMarketplace">
          <template #icon><NIcon :component="RefreshOutline" /></template>
          刷新
        </NButton>
      </section>
      <p v-if="marketplaceSource?.mirror_name" class="muted source-line">
        来源：{{ marketplaceSource.mirror_name }}，{{ marketplaceSource.elapsed_ms || 0 }} ms
      </p>
      <NSpin :show="marketLoading">
        <div class="market-grid">
          <article v-for="item in filteredMarketplace" :key="item.id" class="market-card">
            <div class="market-title">
              <NIcon :component="ExtensionPuzzleOutline" />
              <div>
                <h3>{{ item.name }}</h3>
                <p class="muted">{{ item.id }} · {{ item.version || '未知版本' }}</p>
              </div>
            </div>
            <p class="market-desc">{{ item.description || '暂无介绍' }}</p>
            <div class="tag-row">
              <NTag v-if="item.installed" type="success" size="small">已安装 {{ item.installed_version }}</NTag>
              <NTag v-for="tag in item.tags || []" :key="tag" size="small">{{ tag }}</NTag>
            </div>
            <div class="market-actions">
              <NButton type="primary" :loading="busy === `market:${item.id}`" @click="installMarketPlugin(item)">
                <template #icon><NIcon :component="CloudDownloadOutline" /></template>
                {{ item.installed ? '更新' : '安装' }}
              </NButton>
              <NButton secondary :disabled="!item.repository_url && !item.homepage" @click="openUrl(item.repository_url || item.homepage)">
                打开仓库
              </NButton>
            </div>
          </article>
        </div>
        <p v-if="!filteredMarketplace.length" class="muted">插件商店暂无匹配项目。</p>
      </NSpin>
    </NTabPane>

    <NTabPane name="mirrors" tab="镜像源">
      <section class="toolbar-row">
        <NButton :loading="mirrorLoading" @click="loadMirrors">
          <template #icon><NIcon :component="RefreshOutline" /></template>
          刷新
        </NButton>
        <NButton :loading="busy === 'mirror-test:all'" @click="testMirror()">
          测试全部
        </NButton>
      </section>

      <div class="mirror-form">
        <NInput v-model:value="newMirror.id" placeholder="ID，例如 my-mirror" />
        <NInput v-model:value="newMirror.name" placeholder="名称" />
        <NInput v-model:value="newMirror.raw_prefix" placeholder="Raw 前缀" />
        <NInput v-model:value="newMirror.clone_prefix" placeholder="GitHub/下载前缀" />
        <NInputNumber v-model:value="newMirror.priority" :min="1" placeholder="优先级" />
        <NSwitch v-model:value="newMirror.enabled" />
        <NButton type="primary" :loading="busy === 'mirror:add'" @click="addMirror">
          <template #icon><NIcon :component="AddOutline" /></template>
          添加
        </NButton>
      </div>

      <NSpin :show="mirrorLoading">
        <div class="mirror-list">
          <article v-for="mirror in mirrors" :key="mirror.id" class="mirror-row">
            <div class="mirror-main">
              <div class="mirror-heading">
                <NSwitch :value="mirror.enabled" @update:value="saveMirror(mirror, { enabled: $event })" />
                <strong>{{ mirror.name }}</strong>
                <NTag size="small">{{ mirror.id }}</NTag>
                <NTag size="small">优先级 {{ mirror.priority }}</NTag>
              </div>
              <p class="muted">Raw：{{ mirror.raw_prefix }}</p>
              <div class="mirror-edit-grid">
                <NInput v-model:value="mirror.name" placeholder="名称" />
                <NInput v-model:value="mirror.raw_prefix" placeholder="Raw 前缀" />
                <NInput v-model:value="mirror.clone_prefix" placeholder="下载前缀" />
                <NInputNumber v-model:value="mirror.priority" :min="1" />
              </div>
              <p v-if="mirrorTests[mirror.id]" class="mirror-test">{{ mirrorTests[mirror.id] }}</p>
            </div>
            <div class="mirror-actions">
              <NButton size="small" :loading="busy === `mirror-test:${mirror.id}`" @click="testMirror(mirror)">测试</NButton>
              <NButton size="small" @click="saveMirror(mirror, { priority: Math.max(1, mirror.priority - 1) })">
                <template #icon><NIcon :component="ChevronUp" /></template>
              </NButton>
              <NButton size="small" @click="saveMirror(mirror, { priority: mirror.priority + 1 })">
                <template #icon><NIcon :component="ChevronDown" /></template>
              </NButton>
              <NButton size="small" @click="saveMirror(mirror, mirror)">
                <template #icon><NIcon :component="CreateOutline" /></template>
                保存
              </NButton>
              <NButton size="small" type="error" tertiary @click="deleteMirror(mirror)">
                <template #icon><NIcon :component="TrashOutline" /></template>
              </NButton>
            </div>
          </article>
        </div>
      </NSpin>
    </NTabPane>
  </NTabs>
</template>

<style scoped>
.plugin-head h3,
.market-card h3 {
  margin: 0;
}

.plugin-install,
.mirror-form,
.mirror-row,
.market-card {
  border: 1px solid var(--line-soft);
  border-radius: 8px;
  background: linear-gradient(180deg, var(--panel), var(--panel-2));
}

.plugin-install {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin-bottom: 16px;
  padding: 16px;
}

.plugin-install h3 {
  margin: 0;
  color: var(--gold-2);
}

.plugin-install p {
  margin: 4px 0 0;
}

.install-controls,
.plugin-extra,
.actions-row,
.toolbar-row,
.tag-row,
.market-actions,
.mirror-heading,
.mirror-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.install-controls {
  justify-content: flex-end;
}

.toolbar-row {
  margin-bottom: 14px;
}

.source-line {
  margin: -4px 0 14px;
}

.plugin-head p {
  margin: 4px 0 0;
}

.plugin-tabs {
  margin-top: 4px;
}

.plugin-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(260px, 1fr));
  gap: 14px 18px;
  align-items: start;
}

.field-group {
  grid-column: 1 / -1;
  margin: 10px 0 -2px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, .08);
  color: var(--gold-2, #d99b45);
  font-size: 14px;
}

.field-group:first-child {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
}

.field {
  min-width: 0;
}

.field-wide {
  grid-column: 1 / -1;
}

.input-label {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.switch-label {
  display: flex;
  gap: 10px;
  align-items: center;
  min-height: 34px;
}

.field-title {
  font-size: 13px;
  color: var(--text, #d7d1c5);
}

.field small {
  display: block;
  margin-top: 5px;
  line-height: 1.45;
}

.actions-row {
  margin-top: 16px;
}

.hint {
  margin-top: 8px;
}

.market-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.market-card {
  padding: 16px;
  min-width: 0;
}

.market-title {
  display: grid;
  grid-template-columns: 24px 1fr;
  gap: 10px;
  align-items: start;
}

.market-title p,
.market-desc {
  margin: 5px 0 0;
}

.market-desc {
  min-height: 42px;
  color: var(--text);
  line-height: 1.55;
}

.tag-row {
  margin: 12px 0;
}

.mirror-form {
  display: grid;
  grid-template-columns: 140px 160px minmax(220px, 1fr) minmax(220px, 1fr) 110px 60px auto;
  gap: 10px;
  align-items: center;
  margin-bottom: 14px;
  padding: 14px;
}

.mirror-list {
  display: grid;
  gap: 12px;
}

.mirror-row {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
  padding: 14px;
}

.mirror-main {
  min-width: 0;
}

.mirror-main p {
  margin: 6px 0 0;
  word-break: break-all;
}

.mirror-edit-grid {
  display: grid;
  grid-template-columns: 160px minmax(220px, 1fr) minmax(220px, 1fr) 100px;
  gap: 8px;
  margin-top: 10px;
}

.mirror-test {
  color: var(--gold-2);
}

.mirror-actions {
  justify-content: flex-end;
}

@media (max-width: 980px) {
  .mirror-form {
    grid-template-columns: 1fr;
  }

  .mirror-edit-grid {
    grid-template-columns: 1fr;
  }

  .mirror-row,
  .plugin-install {
    align-items: stretch;
    flex-direction: column;
  }

  .install-controls,
  .mirror-actions {
    justify-content: flex-start;
  }
}

@media (max-width: 860px) {
  .plugin-form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
