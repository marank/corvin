<script setup lang="ts">
import dayjs from 'dayjs'
import { computed } from 'vue'
import { useFormattingStore } from '../../stores/formatting'

const props = withDefaults(defineProps<{
  value: string | Date | null | undefined
  type?: 'date' | 'time' | 'datetime'
}>(), { type: 'date' })
const formatting = useFormattingStore()

const text = computed(() => {
  if (!props.value) return '—'
  const input = props.type === 'time' && typeof props.value === 'string'
    ? `2000-01-01T${props.value}`
    : props.value
  const value = dayjs(input)
  if (!value.isValid()) return '—'
  if (props.type === 'time') return value.format(formatting.timeFormat)
  if (props.type === 'datetime') {
    return value.format(`${formatting.dateFormat} ${formatting.timeFormat}`)
  }
  return value.format(formatting.dateFormat)
})
</script>

<template><span>{{ text }}</span></template>
