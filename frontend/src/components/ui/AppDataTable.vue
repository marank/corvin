<script setup lang="ts" generic="T extends { id: number }">
import DataTable from 'primevue/datatable'
import AppEmptyState from './AppEmptyState.vue'
import { useI18n } from 'vue-i18n'

withDefaults(
  defineProps<{
    rows: T[]
    loading?: boolean
    mobileCard?: (row: T) => string
  }>(),
  { loading: false },
)
defineEmits<{ rowClick: [row: T] }>()
const { t } = useI18n()
</script>

<template>
  <!-- Desktop table -->
  <DataTable
    :value="rows"
    :loading="loading"
    class="hidden md:block border border-surface-200 dark:border-surface-800"
    :row-class="() => 'cursor-pointer'"
    @row-click="(e: any) => $emit('rowClick', e.data)"
  >
    <template #empty><AppEmptyState :message="t('common.empty')" /></template>
    <slot />
  </DataTable>

  <!-- Mobile cards -->
  <div class="md:hidden flex flex-col gap-2">
    <AppEmptyState v-if="!loading && rows.length === 0" :message="t('common.empty')" />
    <div
      v-for="row in rows"
      :key="row.id"
      class="border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-3 cursor-pointer"
      @click="$emit('rowClick', row)"
    >
      <slot name="card" :row="row">
        <div class="font-medium">{{ mobileCard ? mobileCard(row) : row.id }}</div>
      </slot>
    </div>
  </div>
</template>
