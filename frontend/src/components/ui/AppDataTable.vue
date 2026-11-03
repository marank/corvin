<script setup lang="ts" generic="T extends { id: string }">
import { computed, onUnmounted, ref, shallowRef, useSlots, watch } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import DataTable, { type DataTablePageEvent, type DataTableSortEvent, type DataTableStateEvent } from 'primevue/datatable'
import Paginator, { type PageState } from 'primevue/paginator'
import Select from 'primevue/select'
import AppEmptyState from './AppEmptyState.vue'
import { useI18n } from 'vue-i18n'

export interface AppTableSortOption {
  label: string
  value: string
}

const props = withDefaults(
  defineProps<{
    rows: T[]
    loading?: boolean
    mobileCard?: (row: T) => string
    lazy?: boolean
    totalRecords?: number
    first?: number
    pageSize?: number
    rowsPerPageOptions?: number[]
    sortField?: string
    sortOrder?: 1 | -1
    sortOptions?: AppTableSortOption[]
    stateKey?: string
    selectable?: boolean
  }>(),
  {
    loading: false,
    lazy: false,
    first: 0,
    pageSize: 50,
    rowsPerPageOptions: () => [10, 20, 50, 100],
    sortField: '',
    sortOrder: 1,
    sortOptions: () => [],
    stateKey: undefined,
    selectable: false,
  },
)
const emit = defineEmits<{
  rowClick: [row: T]
  page: [value: { page: number; pageSize: number; first: number }]
  sort: [value: { field: string; order: 1 | -1 }]
  stateRestore: [value: { page: number; pageSize: number; field: string; order: 1 | -1 }]
  selectionChange: [rows: T[]]
}>()
const { t } = useI18n()

// Table on md+, card list below. Rendered with v-if rather than hidden with CSS:
// a hidden DataTable measures zero-width columns and saves them to its state.
const desktopQuery = window.matchMedia('(min-width: 768px)')
const isDesktop = ref(desktopQuery.matches)
const onMediaChange = (e: MediaQueryListEvent) => { isDesktop.value = e.matches }
desktopQuery.addEventListener('change', onMediaChange)
onUnmounted(() => desktopQuery.removeEventListener('change', onMediaChange))

const slots = useSlots()
const localFirst = ref(props.first)
const localPageSize = ref(props.pageSize)
const localSortField = ref(props.sortField)
const localSortOrder = ref<1 | -1>(props.sortOrder)
const selectionMode = ref(false)
const selectedRows = shallowRef<T[]>([])

watch(() => props.first, (value) => { localFirst.value = value })
watch(() => props.pageSize, (value) => { localPageSize.value = value })
watch(() => props.sortField, (value) => { localSortField.value = value })
watch(() => props.sortOrder, (value) => { localSortOrder.value = value })
watch(() => props.rows, () => {
  const ids = new Set(props.rows.map((row) => row.id))
  if (!props.lazy) updateSelection(selectedRows.value.filter((row) => ids.has(row.id)))
}, { deep: false })

const total = computed(() => props.lazy ? (props.totalRecords ?? 0) : props.rows.length)
const showPaginator = computed(() => total.value > localPageSize.value)
const effectiveSortOptions = computed(() => {
  if (props.sortOptions.length) return props.sortOptions
  return (slots.default?.() ?? [])
    .filter((node) => node.props?.sortable && node.props?.field)
    .map((node) => ({
      label: String(node.props?.header ?? node.props?.field),
      value: String(node.props?.sortField ?? node.props?.['sort-field'] ?? node.props?.field),
    }))
})

function fieldValue(row: T, field: string): unknown {
  return field.split('.').reduce<unknown>((value, key) => {
    if (value && typeof value === 'object') return (value as Record<string, unknown>)[key]
    return null
  }, row)
}

const sortedRows = computed(() => {
  if (props.lazy || !localSortField.value) return props.rows
  return [...props.rows].sort((left, right) => {
    const a = fieldValue(left, localSortField.value)
    const b = fieldValue(right, localSortField.value)
    if (a == null && b == null) return 0
    if (a == null) return -localSortOrder.value
    if (b == null) return localSortOrder.value
    if (typeof a === 'number' && typeof b === 'number') return (a - b) * localSortOrder.value
    return String(a).localeCompare(String(b), undefined, { numeric: true }) * localSortOrder.value
  })
})

const visibleMobileRows = computed(() => {
  if (props.lazy) return props.rows
  return sortedRows.value.slice(localFirst.value, localFirst.value + localPageSize.value)
})

const currentPageRows = computed(() => props.lazy
  ? props.rows
  : sortedRows.value.slice(localFirst.value, localFirst.value + localPageSize.value))

function updateSelection(rows: T[]) {
  selectedRows.value = rows
  emit('selectionChange', rows)
}

function toggleSelection(row: T) {
  const exists = selectedRows.value.some((selected) => selected.id === row.id)
  updateSelection(exists
    ? selectedRows.value.filter((selected) => selected.id !== row.id)
    : [...selectedRows.value, row])
}

function handleRowClick(row: T) {
  if (selectionMode.value) toggleSelection(row)
  else emit('rowClick', row)
}

function startSelection() {
  selectionMode.value = true
}

function finishSelection() {
  selectionMode.value = false
}

function selectCurrentPage() {
  const byId = new Map(selectedRows.value.map((row) => [row.id, row]))
  currentPageRows.value.forEach((row) => byId.set(row.id, row))
  updateSelection([...byId.values()])
}

function clearSelection() {
  updateSelection([])
}

function handlePage(event: DataTablePageEvent | PageState) {
  localFirst.value = event.first
  localPageSize.value = event.rows
  emit('page', { page: event.page + 1, pageSize: event.rows, first: event.first })
}

function handleSort(event: DataTableSortEvent) {
  const field = typeof event.sortField === 'string' ? event.sortField : ''
  const order = event.sortOrder === -1 ? -1 : 1
  localSortField.value = field
  localSortOrder.value = order
  localFirst.value = 0
  emit('sort', { field, order })
}

function handleStateRestore(state: DataTableStateEvent) {
  const rows = Number(state.rows) || props.pageSize
  const first = Number(state.first) || 0
  const restoredField = typeof state.sortField === 'string' ? state.sortField : ''
  const field = restoredField || props.sortField
  const order: 1 | -1 = restoredField ? (state.sortOrder === -1 ? -1 : 1) : props.sortOrder
  if (selectedRows.value.length) updateSelection([])
  localFirst.value = first
  localPageSize.value = rows
  localSortField.value = field
  localSortOrder.value = order
  emit('stateRestore', { page: Math.floor(first / rows) + 1, pageSize: rows, field, order })
}

function updateMobileSort(field: string) {
  localSortField.value = field
  localFirst.value = 0
  emit('sort', { field, order: localSortOrder.value })
}

function toggleSortOrder() {
  localSortOrder.value = localSortOrder.value === 1 ? -1 : 1
  localFirst.value = 0
  emit('sort', { field: localSortField.value, order: localSortOrder.value })
}
</script>

<template>
  <div>
    <div v-if="selectable" class="flex min-h-9 items-center justify-end gap-2 mb-2">
      <template v-if="selectionMode">
        <span class="text-sm text-surface-500">{{ t('table.selected', { count: selectedRows.length }) }}</span>
        <Button :label="t('table.selectPage')" size="small" text @click="selectCurrentPage" />
        <Button :label="t('table.clearSelection')" size="small" text :disabled="selectedRows.length === 0" @click="clearSelection" />
        <Button :label="t('common.done')" size="small" @click="finishSelection" />
      </template>
      <Button v-else :label="t('table.select')" icon="pi pi-check-square" size="small" text @click="startSelection" />
    </div>

    <DataTable
      v-if="isDesktop"
      :value="rows"
      :loading="loading"
      :lazy="lazy"
      :total-records="total"
      :paginator="showPaginator"
      :always-show-paginator="false"
      :first="localFirst"
      :rows="localPageSize"
      :rows-per-page-options="rowsPerPageOptions"
      :sort-field="localSortField || undefined"
      :sort-order="localSortField ? localSortOrder : undefined"
      :resizable-columns="true"
      column-resize-mode="fit"
      :reorderable-columns="true"
      :state-storage="stateKey ? 'local' : undefined"
      :state-key="stateKey"
      paginator-template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink RowsPerPageDropdown CurrentPageReport"
      :current-page-report-template="t('table.pageReport')"
      class="border border-surface-200 dark:border-surface-800"
      :row-class="() => 'cursor-pointer'"
      :selection="selectionMode ? selectedRows : undefined"
      data-key="id"
      @update:selection="(rows: T[]) => updateSelection(rows ?? [])"
      @row-click="(event: any) => handleRowClick(event.data)"
      @page="handlePage"
      @sort="handleSort"
      @state-restore="handleStateRestore"
    >
      <Column v-if="selectionMode" selection-mode="multiple" header-style="width: 3rem" :reorderable-column="false" />
      <template #empty><AppEmptyState :message="t('common.empty')" /></template>
      <slot />
    </DataTable>

    <div v-else>
      <div v-if="effectiveSortOptions.length" class="flex items-center gap-2 mb-2">
        <Select
          :model-value="localSortField"
          :options="effectiveSortOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('table.sortBy')"
          class="min-w-0 flex-1"
          @update:model-value="updateMobileSort"
        />
        <Button
          :icon="localSortOrder === 1 ? 'pi pi-sort-amount-up' : 'pi pi-sort-amount-down'"
          :aria-label="localSortOrder === 1 ? t('table.ascending') : t('table.descending')"
          severity="secondary"
          outlined
          @click="toggleSortOrder"
        />
      </div>
      <div class="flex flex-col gap-2">
        <AppEmptyState v-if="!loading && rows.length === 0" :message="t('common.empty')" />
        <div
          v-for="row in visibleMobileRows"
          :key="row.id"
          class="flex items-start gap-3 border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-3 cursor-pointer"
          @click="handleRowClick(row)"
        >
          <Checkbox
            v-if="selectionMode"
            :model-value="selectedRows.some((selected) => selected.id === row.id)"
            binary
            @click.stop
            @update:model-value="toggleSelection(row)"
          />
          <div class="min-w-0 flex-1">
            <slot name="card" :row="row">
              <div class="font-medium">{{ mobileCard ? mobileCard(row) : row.id }}</div>
            </slot>
          </div>
        </div>
      </div>
      <Paginator
        v-if="showPaginator"
        :first="localFirst"
        :rows="localPageSize"
        :total-records="total"
        :rows-per-page-options="rowsPerPageOptions"
        template="PrevPageLink CurrentPageReport NextPageLink RowsPerPageDropdown"
        :current-page-report-template="t('table.pageReport')"
        class="mt-2"
        @page="handlePage"
      />
    </div>
  </div>
</template>
