<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { errorMessage } from '@/api/client'
import { useUpdateCheck } from '@/composables/useUpdateCheck'
import { useToast } from '@/composables/useToast'

const route = useRoute()
const toast = useToast()
const { checkForUpdates } = useUpdateCheck()
let notified = false

function shouldSkipCurrentRoute(): boolean {
  if (route.name === 'login' || route.name === 'join') return true
  if (route.name === 'play' && (route.query.user || route.query.share)) return true
  return false
}

async function checkOnce() {
  if (shouldSkipCurrentRoute()) return
  try {
    const result = await checkForUpdates()
    if (!notified && result?.ok && result.update_available) {
      notified = true
      const version = result.latest?.tag_name || result.latest?.version || '新版'
      toast.info(`DiceFrame ${version} 已发布，可在设置-关于里查看。`)
    }
  } catch (e: unknown) {
    console.debug('DiceFrame update check skipped:', errorMessage(e))
  }
}

onMounted(checkOnce)
watch(() => [route.name, route.query.user, route.query.share], checkOnce)
</script>

<template></template>
