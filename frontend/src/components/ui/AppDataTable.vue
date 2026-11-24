<script setup lang="ts" generic="T extends { id: string }">
import {
  Fragment,
  computed,
  getCurrentInstance,
  nextTick,
  onUnmounted,
  ref,
  shallowRef,
  useSlots,
  watch,
  type VNode,
} from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import DataTable, {
  type DataTablePageEvent,
  type DataTableSortEvent,
  type DataTableStateEvent,
} from 'primevue/datatable'
import Paginator, { type PageState } from 'primevue/paginator'
import Select from 'primevue/select'
import AppEmptyState from './AppEmptyState.vue'
import { useColumnWidths, useTextColumnShares } from './columnWidths'
import { useConfirm } from 'primevue/useconfirm'
import { useNotify } from '../../composables/useNotify'
import { useTableDensity } from '../../composables/useTableDensity'
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
    // Enables "delete selected" in selection mode; called once per selected row.
    deleteRow?: (row: T) => Promise<unknown>
    // Rows sharing this field's value get a #groupheader row (rows must be sorted by it).
    groupField?: string
  }>(),
  {
    loading: false,
    mobileCard: undefined,
    lazy: false,
    totalRecords: undefined,
    first: 0,
    pageSize: 50,
    rowsPerPageOptions: () => [10, 20, 50, 100],
    sortField: '',
    sortOrder: 1,
    sortOptions: () => [],
    stateKey: undefined,
    selectable: false,
    deleteRow: undefined,
    groupField: undefined,
  },
)
const emit = defineEmits<{
  rowClick: [row: T]
  page: [value: { page: number; pageSize: number; first: number }]
  sort: [value: { field: string; order: 1 | -1 }]
  stateRestore: [value: { page: number; pageSize: number; field: string; order: 1 | -1 }]
  selectionChange: [rows: T[]]
  bulkDeleted: []
}>()
const { t } = useI18n()
const confirm = useConfirm()
const notify = useNotify()
const deleting = ref(false)

// Table on md+, card list below. Rendered with v-if rather than hidden with CSS:
// a hidden DataTable measures zero-width columns and saves them to its state.
const desktopQuery = window.matchMedia('(min-width: 768px)')
const isDesktop = ref(desktopQuery.matches)
const density = useTableDensity()
const columnWidths = useColumnWidths(props.stateKey)
const root = ref<HTMLElement>()
const textShares = useTextColumnShares(root)
watch(
  () => [props.rows, isDesktop.value, columnWidths.tableKey.value],
  () => nextTick(textShares.update),
)
const onMediaChange = (e: MediaQueryListEvent) => {
  isDesktop.value = e.matches
}
desktopQuery.addEventListener('change', onMediaChange)
onUnmounted(() => desktopQuery.removeEventListener('change', onMediaChange))

const slots = useSlots()
// Only tables whose parent listens to row-click (or that are in selection mode) look clickable.
const hasRowClickListener = !!getCurrentInstance()?.vnode.props?.onRowClick
const localFirst = ref(props.first)
const localPageSize = ref(props.pageSize)
const localSortField = ref(props.sortField)
const localSortOrder = ref<1 | -1>(props.sortOrder)
const selectionMode = ref(false)
const selectedRows = shallowRef<T[]>([])

watch(
  () => props.first,
  (value) => {
    localFirst.value = value
  },
)
watch(
  () => props.pageSize,
  (value) => {
    localPageSize.value = value
  },
)
watch(
  () => props.sortField,
  (value) => {
    localSortField.value = value
  },
)
watch(
  () => props.sortOrder,
  (value) => {
    localSortOrder.value = value
  },
)
watch(
  () => props.rows,
  () => {
    const ids = new Set(props.rows.map((row) => row.id))
    if (!props.lazy) updateSelection(selectedRows.value.filter((row) => ids.has(row.id)))
  },
  { deep: false },
)

const total = computed(() => (props.lazy ? (props.totalRecords ?? 0) : props.rows.length))
const showPaginator = computed(() => total.value > localPageSize.value)
const effectiveSortOptions = computed(() => {
  if (props.sortOptions.length) return props.sortOptions
  return (slots.default?.() ?? [])
    .filter((node) => node.props?.sortable && node.props.field)
    .map((node) => ({
      label: String(node.props?.header ?? node.props?.field),
      value: String(node.props?.sortField ?? node.props?.['sort-field'] ?? node.props?.field),
    }))
})

// Fallback mobile card for tables without a #card slot or mobileCard: the table's own
// columns as label/value pairs (reusing their #body templates). Columns that can't be
// reordered (checkboxes, row actions) go in a label-less row at the bottom.
interface CardColumn {
  header: string
  field: string
  body?: (scope: { data: T; field: string; index: number }) => VNode[]
  utility: boolean
}

function flattenNodes(nodes: VNode[]): VNode[] {
  return nodes.flatMap((node) =>
    node.type === Fragment && Array.isArray(node.children)
      ? flattenNodes(node.children as VNode[])
      : [node],
  )
}

function cardColumns(): CardColumn[] {
  return flattenNodes(slots.default?.() ?? [])
    .filter((node) => node.type === Column)
    .map((node) => {
      const p = node.props ?? {}
      const reorderable = p.reorderableColumn ?? p['reorderable-column']
      return {
        header: String(p.header ?? ''),
        field: String(p.field ?? ''),
        body: (node.children as Record<string, CardColumn['body']> | null)?.body,
        utility: reorderable === false || reorderable === 'false',
      }
    })
}

function cardValue(column: CardColumn, row: T, index: number): VNode[] | string {
  if (column.body) return column.body({ data: row, field: column.field, index })
  const value = column.field ? fieldValue(row, column.field) : null
  return value == null || value === '' ? '—' : String(value)
}

const RenderNodes = (props: { nodes: VNode[] | string }) => props.nodes

// A cell's value: rows are API records, whose fields hold text, numbers or booleans.
type CellValue = string | number | boolean | null | undefined

function fieldValue(row: T, field: string): CellValue {
  return field.split('.').reduce<unknown>((value, key) => {
    if (value && typeof value === 'object') return (value as Record<string, unknown>)[key]
    return null
  }, row) as CellValue
}

const sortedRows = computed(() => {
  if (props.lazy || !localSortField.value) return props.rows
  return [...props.rows].sort((left, right) => {
    const a = fieldValue(left, localSortField.value)
    const b = fieldValue(right, localSortField.value)
    if (a == null && b == null) return 0
    // Missing values last in either direction, like the desktop table.
    if (a == null) return 1
    if (b == null) return -1
    if (typeof a === 'number' && typeof b === 'number') return (a - b) * localSortOrder.value
    return String(a).localeCompare(String(b), undefined, { numeric: true }) * localSortOrder.value
  })
})

const visibleMobileRows = computed(() => {
  if (props.lazy) return props.rows
  return sortedRows.value.slice(localFirst.value, localFirst.value + localPageSize.value)
})

const currentPageRows = computed(() =>
  props.lazy
    ? props.rows
    : sortedRows.value.slice(localFirst.value, localFirst.value + localPageSize.value),
)

// Truncated free-text cells (td.app-text, see style.css) get their full text as tooltip.
function showTruncatedText(event: Event) {
  const cell = (event.target as HTMLElement).closest<HTMLElement>('td.app-text')
  if (!cell) return
  cell.title = cell.scrollWidth > cell.clientWidth ? cell.textContent.trim() : ''
}

function updateSelection(rows: T[]) {
  selectedRows.value = rows
  emit('selectionChange', rows)
}

function toggleSelection(row: T) {
  const exists = selectedRows.value.some((selected) => selected.id === row.id)
  updateSelection(
    exists
      ? selectedRows.value.filter((selected) => selected.id !== row.id)
      : [...selectedRows.value, row],
  )
}

const rowsClickable = computed(() => hasRowClickListener || selectionMode.value)
// The checkbox toggles the selection itself; its click must not reach the row as well.
const stopRowClick = { root: { onClick: (event: Event) => event.stopPropagation() } }

function handleRowClick(row: T) {
  if (selectionMode.value) toggleSelection(row)
  else emit('rowClick', row)
}

// Deletes one by one so a row the backend refuses (protected, invoiced) doesn't stop the rest.
function deleteSelected() {
  const rows = selectedRows.value
  const deleteRow = props.deleteRow
  if (!deleteRow || !rows.length) return
  confirm.require({
    header: t('common.delete'),
    message: t('table.bulkDeleteConfirm', { count: rows.length }),
    icon: 'pi pi-trash',
    rejectLabel: t('common.cancel'),
    rejectProps: { text: true },
    acceptLabel: t('common.delete'),
    acceptClass: 'p-button-danger',
    accept: () => void deleteRows(rows, deleteRow),
  })
}

async function deleteRows(rows: T[], deleteRow: (row: T) => Promise<unknown>) {
  deleting.value = true
  let failed = 0
  for (const row of rows) {
    try {
      await deleteRow(row)
    } catch {
      failed++
    }
  }
  deleting.value = false
  if (rows.length > failed) notify.ok(t('table.bulkDeleted', { count: rows.length - failed }))
  if (failed) notify.error(null, t('table.bulkDeleteFailed', { count: failed }))
  updateSelection([])
  selectionMode.value = false
  emit('bulkDeleted')
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
  <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -- not interactive: hover/focus only fill the native title tooltip of truncated cells. -->
  <div :id="textShares.id" ref="root" @mouseover="showTruncatedText" @focusin="showTruncatedText">
    <div v-if="selectable || $slots.toolbar" class="flex flex-wrap min-h-9 items-center gap-2 mb-2">
      <div class="flex-1 min-w-0"><slot name="toolbar" /></div>
      <template v-if="selectable && selectionMode">
        <span class="text-sm text-surface-500">{{
          t('table.selected', { count: selectedRows.length })
        }}</span>
        <Button :label="t('table.selectPage')" size="small" text @click="selectCurrentPage" />
        <Button
          :label="t('table.clearSelection')"
          size="small"
          text
          :disabled="selectedRows.length === 0"
          @click="clearSelection"
        />
        <Button
          v-if="deleteRow"
          :label="t('table.deleteSelected', { count: selectedRows.length })"
          icon="pi pi-trash"
          size="small"
          severity="danger"
          outlined
          :loading="deleting"
          :disabled="selectedRows.length === 0"
          @click="deleteSelected"
        />
        <Button :label="t('common.done')" size="small" @click="finishSelection" />
      </template>
      <Button
        v-else-if="selectable"
        :label="t('table.select')"
        icon="pi pi-check-square"
        size="small"
        text
        @click="startSelection"
      />
      <Button
        v-if="isDesktop && columnWidths.custom.value"
        icon="pi pi-arrows-h"
        size="small"
        text
        severity="secondary"
        :aria-label="t('table.resetWidths')"
        :title="t('table.resetWidths')"
        @click="columnWidths.reset"
      />
      <Button
        v-if="isDesktop"
        :icon="density === 'compact' ? 'pi pi-expand' : 'pi pi-compress'"
        size="small"
        text
        severity="secondary"
        :aria-label="density === 'compact' ? t('table.comfortable') : t('table.compact')"
        :title="density === 'compact' ? t('table.comfortable') : t('table.compact')"
        @click="density = density === 'compact' ? 'comfortable' : 'compact'"
      />
    </div>

    <DataTable
      v-if="isDesktop"
      :key="columnWidths.tableKey.value"
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
      :class="{ 'app-table-comfortable': density === 'comfortable' }"
      :row-class="() => (hasRowClickListener || selectionMode ? 'cursor-pointer' : '')"
      :row-group-mode="groupField ? 'subheader' : undefined"
      :group-rows-by="groupField"
      :selection="selectionMode ? selectedRows : undefined"
      data-key="id"
      @update:selection="(rows: T[]) => updateSelection(rows ?? [])"
      @row-click="(event: any) => handleRowClick(event.data)"
      @page="handlePage"
      @sort="handleSort"
      @state-restore="handleStateRestore"
      @state-save="columnWidths.dropSavedWidths"
      @column-resize-end="columnWidths.markResized"
      @column-reorder="nextTick(textShares.update)"
    >
      <Column
        v-if="selectionMode"
        selection-mode="multiple"
        header-style="width: 3rem"
        :reorderable-column="false"
      />
      <template #empty><AppEmptyState :message="t('common.empty')" /></template>
      <template v-if="groupField" #groupheader="{ data }"
        ><slot name="groupheader" :data="data"
      /></template>
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
          :aria-label="t('table.sortBy')"
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
      <div class="flex flex-col gap-1.5">
        <AppEmptyState v-if="!loading && rows.length === 0" :message="t('common.empty')" />
        <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -- the card holds its own buttons, so it can't be role="button"; it is focusable and opens on Enter instead. -->
        <div
          v-for="(row, index) in visibleMobileRows"
          :key="row.id"
          class="flex items-start gap-3 app-card px-3 py-2 text-sm"
          :class="{ 'cursor-pointer': rowsClickable }"
          :tabindex="rowsClickable ? 0 : undefined"
          @click="handleRowClick(row)"
          @keydown.enter.self="handleRowClick(row)"
        >
          <Checkbox
            v-if="selectionMode"
            :model-value="selectedRows.some((selected) => selected.id === row.id)"
            binary
            :pt="stopRowClick"
            @update:model-value="toggleSelection(row)"
          />
          <div class="min-w-0 flex-1">
            <slot name="card" :row="row">
              <div v-if="mobileCard" class="font-medium">{{ mobileCard(row) }}</div>
              <template v-else>
                <dl class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-0.5">
                  <template
                    v-for="column in cardColumns().filter((c) => !c.utility)"
                    :key="column.field + column.header"
                  >
                    <dt class="text-surface-500">{{ column.header }}</dt>
                    <dd class="min-w-0 break-words">
                      <RenderNodes :nodes="cardValue(column, row, index)" />
                    </dd>
                  </template>
                </dl>
                <div
                  v-if="cardColumns().some((c) => c.utility && c.body)"
                  class="flex justify-end gap-1"
                  @click.stop
                >
                  <template
                    v-for="(column, i) in cardColumns().filter((c) => c.utility && c.body)"
                    :key="i"
                  >
                    <RenderNodes :nodes="cardValue(column, row, index)" />
                  </template>
                </div>
              </template>
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
