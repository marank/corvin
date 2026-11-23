<script setup lang="ts">
import { useI18n } from 'vue-i18n'

// Task priority as icon + text, so it never looks like a status tag of the same color.
defineProps<{ priority: string }>()
const { t } = useI18n()
const look: Record<string, { icon: string; class: string }> = {
  low: { icon: 'pi pi-angle-down', class: 'text-surface-500' },
  medium: { icon: 'pi pi-minus', class: 'text-surface-700 dark:text-surface-300' },
  high: { icon: 'pi pi-angle-double-up', class: 'text-danger font-medium' },
}
</script>

<template>
  <span
    class="inline-flex items-center gap-1 text-sm whitespace-nowrap"
    :class="look[priority]?.class"
  >
    <i :class="look[priority]?.icon" class="text-xs" aria-hidden="true" />{{
      t(`tasks.priorities.${priority}`)
    }}
  </span>
</template>
