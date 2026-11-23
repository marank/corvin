<script setup lang="ts">
import { computed } from 'vue'
import { useFormattingStore } from '../../stores/formatting'
import { getCurrencySymbol } from '../../currencies'

const props = withDefaults(
  defineProps<{
    value: number | string | null | undefined
    mode?: 'decimal' | 'currency' | 'percent'
    currency?: string
    minimumFractionDigits?: number
    maximumFractionDigits?: number
  }>(),
  {
    mode: 'decimal',
    currency: undefined,
    minimumFractionDigits: undefined,
    maximumFractionDigits: 2,
  },
)
const formatting = useFormattingStore()

function numberText(value: number): string {
  const parts = new Intl.NumberFormat('en-US', {
    useGrouping: true,
    minimumFractionDigits: props.minimumFractionDigits,
    maximumFractionDigits: props.maximumFractionDigits,
  }).formatToParts(value)
  return parts
    .map((part) => {
      if (part.type === 'group') return formatting.thousandsSeparator
      if (part.type === 'decimal') return formatting.decimalSeparator
      return part.value
    })
    .join('')
}

function currencyMarker(currency: string): string {
  return formatting.currencyDisplay === 'code' ? currency : getCurrencySymbol(currency)
}

const text = computed(() => {
  if (props.value === null || props.value === undefined || props.value === '') return '—'
  const value = Number(props.value)
  if (!Number.isFinite(value)) return '—'
  if (props.mode === 'percent') return `${numberText(value)}%`
  const number = numberText(value)
  if (props.mode !== 'currency') return number
  // eslint-disable-next-line @typescript-eslint/prefer-nullish-coalescing -- records without a currency send "", which means the default one
  const currency = props.currency || formatting.currency
  const marker = currencyMarker(currency)
  const space = formatting.currencySpace ? ' ' : ''
  return formatting.currencyPosition === 'before'
    ? `${marker}${space}${number}`
    : `${number}${space}${marker}`
})
</script>

<template>
  <span>{{ text }}</span>
</template>
