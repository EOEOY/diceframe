<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { errorMessage, setAccessToken, validateAccessToken } from '@/api/client'
import BrandLogo from '@/components/BrandLogo.vue'

const route = useRoute()
const token = ref('')
const busy = ref(false)
const error = ref('')
const redirect = computed(() => String(route.query.redirect || '/'))

async function submit() {
  const value = token.value.trim()
  if (!value) { error.value = '请输入访问密码'; return }
  busy.value = true
  error.value = ''
  try {
    await validateAccessToken(value)
    setAccessToken(value)
    location.href = redirect.value || '/'
  } catch (e: unknown) {
    error.value = errorMessage(e) || '验证失败'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-card">
      <BrandLogo :size="56" :with-text="false" class="login-emblem" />
      <h1>DiceFrame</h1>
      <p class="muted">输入访问密码进入游戏桌。</p>
      <form @submit.prevent="submit">
        <label>访问密码<input v-model="token" type="password" autocomplete="current-password" autofocus placeholder="Access token"></label>
        <button class="primary submit" :disabled="busy">{{ busy ? '验证中' : '进入' }}</button>
      </form>
      <p v-if="error" class="error-banner">{{ error }}</p>
      <p class="hint muted">首次启动密码会显示在控制台，并写入 <code>data/access_token.txt</code>；设置密码后将只保存安全凭证。</p>
      <details class="forgot-password">
        <summary>忘记密码？</summary>
        <p>在数据目录新建 <code>reset_access_password.txt</code>，写入新密码并重启 DiceFrame。重置成功后该文件会自动删除。</p>
      </details>
    </section>
  </main>
</template>
