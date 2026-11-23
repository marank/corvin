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

  // One request for every store that needs the company settings (this one and
  // formatting): callers share it while it runs, and a failed one may be retried.
  let pending: Promise<Record<string, unknown>> | null = null
  function fetch(): Promise<Record<string, unknown>> {
    pending ??= settingsApi.get().then(
      (settings) => {
        apply(settings)
        return settings
      },
      (error: unknown) => {
        pending = null
        throw error
      },
    )
    return pending
  }

  async function load() {
    if (loaded.value) return
    await fetch()
  }

  return {
    timerCountsDuringBreak,
    alwaysShowTimerWidget,
    openStoppedTimeEntry,
    loaded,
    apply,
    fetch,
    load,
  }
})
