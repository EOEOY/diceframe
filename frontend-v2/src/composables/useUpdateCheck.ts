import { computed, ref } from 'vue'
import { api } from '@/api/client'
import type { UpdateCheckResponse } from '@/api/types'

const updateInfo = ref<UpdateCheckResponse | null>(null)
const updateChecking = ref(false)
const updateChecked = ref(false)
const updateAvailable = computed(() => Boolean(updateInfo.value?.ok && updateInfo.value.update_available))

async function checkForUpdates(force = false): Promise<UpdateCheckResponse | null> {
  if (updateChecking.value) return updateInfo.value
  if (updateChecked.value && !force) return updateInfo.value
  updateChecking.value = true
  updateChecked.value = true
  try {
    updateInfo.value = await api<UpdateCheckResponse>('/system/update-check')
    return updateInfo.value
  } finally {
    updateChecking.value = false
  }
}

export function useUpdateCheck() {
  return {
    updateInfo,
    updateChecking,
    updateChecked,
    updateAvailable,
    checkForUpdates,
  }
}
