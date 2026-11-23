import { defineStore } from 'pinia'
import { ref } from 'vue'
import { settingsApi } from '../api'

export const useSettingsStore = defineStore('settings', () => {
  const loaded = ref(false)
  const timerCountsDuringBreak = ref(false)
  const alwaysShowTimerWidget = ref(false)
  const openStoppedTimeEntry = ref<'ask' | 'yes' | 'no'>('ask')

  function apply(settings: Record<string, unknown>) {
    timerCountsDuringBreak.value = settings.timer_counts_during_break === true
    alwaysShowTimerWidget.value = settings.always_show_timer_widget === true
    const openBehavior = settings.open_stopped_time_entry
    openStoppedTimeEntry.value =
      openBehavior === 'yes' || openBehavior === 'no' ? openBehavior : 'ask'
    loaded.value = true
  }

  async function load() {
    if (loaded.value) return
    apply(await settingsApi.get())
  }

  return {
    timerCountsDuringBreak,
    alwaysShowTimerWidget,
    openStoppedTimeEntry,
    loaded,
    apply,
    load,
  }
})
