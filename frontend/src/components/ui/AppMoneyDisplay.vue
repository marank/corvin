<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = withDefaults(
  defineProps<{ amount: number | string | null; currency?: string }>(),
  { currency: 'EUR' },
)
const { locale } = useI18n()

const text = computed(() => {
  if (props.amount === null || props.amount === undefined) return '—'
  return new Intl.NumberFormat(locale.value, {
    style: 'currency',
    currency: props.currency,
  }).format(Number(props.amount))
})
</script>

<template>
  <span>{{ text }}</span>
</template>
