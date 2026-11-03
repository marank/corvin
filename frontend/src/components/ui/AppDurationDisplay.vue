<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ minutes: number | null }>()

const text = computed(() => {
  if (props.minutes === null || props.minutes === undefined) return '—'
  // Round to whole minutes first, otherwise 59.6 would become "0:60 h".
  const total = Math.round(props.minutes)
  const h = Math.floor(total / 60)
  const m = total % 60
  return `${h}:${String(m).padStart(2, '0')} h`
})
</script>

<template>
  <span>{{ text }}</span>
</template>
