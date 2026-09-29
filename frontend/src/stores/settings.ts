import { defineStore } from 'pinia'
import { ref } from 'vue'
import { settingsApi } from '../api'

export const useSettingsStore = defineStore('settings', () => {
  const loaded = ref(false)
  const timerCountsDuringBreak = ref(false)

  function apply(settings: Record<string, unknown>) {
    timerCountsDuringBreak.value = settings.timer_counts_during_break === true
    loaded.value = true
  }

  async function load() {
    if (loaded.value) return
    apply(await settingsApi.get())
  }

  return {
    timerCountsDuringBreak,
    loaded,
    apply,
    load,
  }
})
