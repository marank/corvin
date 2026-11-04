<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Chip from 'primevue/chip'
import Popover from 'primevue/popover'

export interface ActiveFilter {
  key: string
  label: string
  value: string
}

// Compact list filters: one "Filter" button opens the fields in a popover, active
// filters show as removable chips. Meant for AppDataTable's #toolbar slot.
defineProps<{ active: ActiveFilter[] }>()
const emit = defineEmits<{ remove: [key: string]; clear: [] }>()
const { t } = useI18n()
const popover = ref<InstanceType<typeof Popover>>()
</script>

<template>
  <div class="flex flex-wrap items-center gap-2">
    <Button
      :label="t('common.filter')"
      icon="pi pi-filter"
      size="small"
      severity="secondary"
      outlined
      :badge="active.length ? String(active.length) : undefined"
      aria-haspopup="dialog"
      @click="popover?.toggle($event)"
    />
    <Popover ref="popover">
      <div class="flex flex-col gap-3 w-[min(20rem,calc(100vw-3rem))]">
        <slot />
        <Button v-if="active.length" :label="t('common.clearFilters')" icon="pi pi-filter-slash" text size="small" class="self-start" @click="emit('clear')" />
      </div>
    </Popover>
    <Chip
      v-for="filter in active"
      :key="filter.key"
      removable
      class="app-filter-chip"
      @remove="emit('remove', filter.key)"
    >
      <span class="text-surface-500">{{ filter.label }}:</span>&nbsp;<span class="font-medium">{{ filter.value }}</span>
    </Chip>
    <div class="ml-auto"><slot name="end" /></div>
  </div>
</template>

<style scoped>
.app-filter-chip {
  font-size: 0.8125rem;
  padding-block: 0.125rem;
}
</style>
