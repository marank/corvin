import { defineStore } from 'pinia'
import { ref } from 'vue'
import { settingsApi } from '../api'

export const useFormattingStore = defineStore('formatting', () => {
  const dateFormat = ref('DD.MM.YYYY')
  const timeFormat = ref('HH:mm')
  const decimalSeparator = ref(',')
  const thousandsSeparator = ref('.')
  const currency = ref('EUR')
  const currencyDisplay = ref<'symbol' | 'code'>('symbol')
  const currencyPosition = ref<'before' | 'after'>('after')
  const currencySpace = ref(true)
  const loaded = ref(false)

  function apply(settings: Record<string, unknown>) {
    dateFormat.value = String(settings.date_format || 'DD.MM.YYYY')
    timeFormat.value = String(settings.time_format || 'HH:mm')
    decimalSeparator.value = String(settings.decimal_separator || ',')
    thousandsSeparator.value = String(settings.thousands_separator || '.')
    currency.value = String(settings.currency || 'EUR')
    currencyDisplay.value = settings.currency_display === 'code' ? 'code' : 'symbol'
    currencyPosition.value = settings.currency_position === 'before' ? 'before' : 'after'
    currencySpace.value = settings.currency_space !== false
    loaded.value = true
  }

  async function load() {
    if (loaded.value) return
    apply(await settingsApi.get())
  }

  return {
    dateFormat, timeFormat, decimalSeparator, thousandsSeparator,
    currency, currencyDisplay, currencyPosition, currencySpace,
    loaded, apply, load,
  }
})
