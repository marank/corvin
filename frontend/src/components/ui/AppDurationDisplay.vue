<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ minutes: number | null }>()

const text = computed(() => {
  if (props.minutes === null || props.minutes === undefined) return '—'
  const h = Math.floor(props.minutes / 60)
  const m = Math.round(props.minutes % 60)
  return `${h}:${String(m).padStart(2, '0')} h`
})
</script>

<template>
  <span>{{ text }}</span>
</template>
