<script setup lang="ts">
import Tag from 'primevue/tag'

const props = defineProps<{ status: string; label?: string }>()

const severityMap: Record<string, string> = {
  draft: 'secondary',
  issued: 'info',
  sent: 'info',
  partially_paid: 'warn',
  paid: 'success',
  cancelled: 'danger',
  active: 'success',
  on_hold: 'warn',
  done: 'secondary',
  open: 'info',
  in_progress: 'warn',
  low: 'secondary',
  medium: 'info',
  high: 'danger',
}
</script>

<template>
  <Tag :value="label ?? props.status" :severity="(severityMap[props.status] as any) ?? 'secondary'" />
</template>
