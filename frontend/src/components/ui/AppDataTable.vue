<script setup lang="ts" generic="T extends { id: string }">
import {
  computed,
  getCurrentInstance,
  onMounted,
  onUnmounted,
  ref,
  useSlots,
  watch,
  type VNode,
} from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import DataTable, {
  type DataTablePageEvent,
  type DataTableSortEvent,
  type DataTableStateEvent,
} from 'primevue/datatable'
import Paginator, { type PageState } from 'primevue/paginator'
import Popover from 'primevue/popover'
import Select from 'primevue/select'
import AppEmptyState from './AppEmptyState.vue'
import {
  MIN_WIDTH_PX,
  layoutColumns,
  leastWidth,
  readColumns,
  useColumnPrefs,
  useColumnResize,
  type TableColumn,
} from './tableColumns'
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
    // Rows sharing this field's value get a #groupheader row (rows must be sorted by it).
    groupField?: string
    emptyMessage?: string
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
    groupField: undefined,
    emptyMessage: undefined,
  },
)
const emit = defineEmits<{
  rowClick: [row: T]
  page: [value: { page: number; pageSize: number; first: number }]
  sort: [value: { field: string; order: 1 | -1 }]
  stateRestore: [value: { page: number; pageSize: number; field: string; order: 1 | -1 }]
}>()
const { t } = useI18n()

// Table on md+, card list below. Rendered with v-if rather than hidden with CSS:
// a hidden DataTable measures zero-width columns and saves them to its state.
const desktopQuery = window.matchMedia('(min-width: 768px)')
const isDesktop = ref(desktopQuery.matches)
const density = useTableDensity()
const columnPrefs = useColumnPrefs(props.stateKey)
const root = ref<HTMLElement>()
const chooser = ref<InstanceType<typeof Popover>>()
const fitted = computed(() => !!columnPrefs.prefs.value.fit)
const onMediaChange = (e: MediaQueryListEvent) => {
  isDesktop.value = e.matches
}
desktopQuery.addEventListener('change', onMediaChange)
onUnmounted(() => desktopQuery.removeEventListener('change', onMediaChange))

const slots = useSlots()

// The view's <Column>s (see tableColumns.ts): which are shown, and how wide.
const columns = computed(() => readColumns(slots.default?.()))
const choosable = computed(() => columns.value.filter((column) => !column.utility))
// Measured so free-text columns can give way before the table has to scroll.
const available = ref(Number.POSITIVE_INFINITY)
const remPx = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16
// The table's border.
const layoutOf = (shown: TableColumn[]) =>
  layoutColumns(shown, columnPrefs.prefs.value, available.value - 2, remPx)
// Optional columns the user left alone drop out when the row is too narrow for all (as long
// as the table fits its row; once sized by the user, it scrolls instead).
const visibleColumns = computed(() => {
  const chosen = columns.value.filter(columnPrefs.isVisible)
  const all = layoutOf(chosen)
  if (all.width !== undefined || all.minWidth <= available.value - 2) return chosen
  return chosen.filter(
    (column) => !column.optional || columnPrefs.prefs.value.visible[column.key] !== undefined,
  )
})
const isShown = (column: TableColumn) => visibleColumns.value.includes(column)
const layout = computed(() => layoutOf(visibleColumns.value))
useColumnResize(root, columnPrefs.setWidth, {
  fit: () => !!columnPrefs.prefs.value.fit,
  leastOf: (key) => {
    const column = columns.value.find((c) => c.key === key)
    return column ? leastWidth(column, remPx) : MIN_WIDTH_PX
  },
  pin: () =>
    columns.value
      .filter((column) => column.optional && !isShown(column))
      .forEach((column) => columnPrefs.setVisible(column, false)),
})
function headerStyle(column: TableColumn) {
  const px = layout.value.widths.get(column.key)
  return px === undefined ? undefined : { width: `${px}px` }
}
const tableStyle = computed(() => ({
  minWidth: `${layout.value.minWidth}px`,
  ...(layout.value.width === undefined ? {} : { width: `${layout.value.width}px` }),
}))
// jsdom (tests) has no ResizeObserver.
const observer =
  typeof ResizeObserver === 'function'
    ? new ResizeObserver(([entry]) => (available.value = entry!.contentRect.width))
    : undefined
onMounted(() => root.value && observer?.observe(root.value))
onUnmounted(() => observer?.disconnect())
// What AppDataTable adds to each of the view's <Column>s.
function columnBindings(column: TableColumn) {
  return {
    columnKey: column.key,
    hidden: !isShown(column),
    // Both spellings: the view's `header-style` would otherwise win over ours.
    headerStyle: headerStyle(column),
    'header-style': headerStyle(column),
    pt: { headerCell: column.utility ? {} : { 'data-col-key': column.key } },
  }
}
// At least one content column stays visible.
function canHide(column: TableColumn) {
  return visibleColumns.value.filter((c) => !c.utility && c.key !== column.key).length > 0
}
// Only tables whose parent listens to row-click look clickable.
const hasRowClickListener = !!getCurrentInstance()?.vnode.props?.onRowClick
const localFirst = ref(props.first)
const localPageSize = ref(props.pageSize)
const localSortField = ref(props.sortField)
const localSortOrder = ref<1 | -1>(props.sortOrder)

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

// Fallback mobile card for tables without a #card slot or mobileCard: the table's visible
// columns as label/value pairs (reusing their #body templates). Columns that can't be
// reordered (checkboxes, row actions) go in a label-less row at the bottom.
interface CardColumn {
  header: string
  field: string
  body?: (scope: { data: T; field: string; index: number }) => VNode[]
  utility: boolean
}

function cardColumns(): CardColumn[] {
  return visibleColumns.value.map((column) => ({
    header: column.header,
    field: typeof column.node.props?.field === 'string' ? column.node.props.field : '',
    body: (column.node.children as Record<string, CardColumn['body']> | null)?.body,
    utility: column.utility,
  }))
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

// Cells and headers cut off by their column's width get their full text as tooltip.
function showTruncatedText(event: Event) {
  const target = event.target as HTMLElement
  const th = target.closest<HTMLElement>('th')
  const cell = th
    ? th.querySelector<HTMLElement>('.p-datatable-column-title')
    : target.closest('td')
  if (!cell) return
  cell.title = cell.scrollWidth > cell.clientWidth ? cell.textContent.trim() : ''
}

const rowsClickable = hasRowClickListener

function handleRowClick(row: T) {
  emit('rowClick', row)
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
  <div ref="root" @mouseover="showTruncatedText" @focusin="showTruncatedText">
    <div
      v-if="$slots.toolbar || (isDesktop && choosable.length > 1)"
      class="flex flex-wrap min-h-9 items-center gap-2 mb-2"
    >
      <div class="flex-1 min-w-0"><slot name="toolbar" /></div>
      <Button
        v-if="isDesktop && choosable.length > 1"
        size="small"
        text
        severity="secondary"
        :aria-label="t('table.columns')"
        :title="t('table.columns')"
        aria-haspopup="true"
        icon="iconify lucide--columns-3-cog"
        @click="chooser?.toggle($event)"
      />
      <Popover ref="chooser">
        <div class="flex flex-col gap-1 min-w-48 max-h-96 overflow-y-auto">
          <div class="text-xs font-semibold text-surface-500 mb-1">{{ t('table.columns') }}</div>
          <label
            v-for="column in choosable"
            :key="column.key"
            class="flex items-center gap-2 text-sm py-0.5 cursor-pointer"
          >
            <Checkbox
              :model-value="isShown(column)"
              binary
              :disabled="isShown(column) && !canHide(column)"
              @update:model-value="(on: boolean) => columnPrefs.setVisible(column, on)"
            />
            {{ column.header }}
          </label>
          <Button
            :label="t('table.resetColumns')"
            icon="iconify lucide--rotate-ccw"
            size="small"
            text
            severity="secondary"
            class="mt-1 self-start"
            :disabled="!columnPrefs.customized.value"
            @click="columnPrefs.reset"
          />
        </div>
      </Popover>
      <!-- Layout switches: icon and label name what a click switches to. -->
      <Button
        v-if="isDesktop"
        size="small"
        text
        severity="secondary"
        :aria-label="fitted ? t('table.freeWidth') : t('table.fitWidth')"
        :title="fitted ? t('table.freeWidth') : t('table.fitWidth')"
        :icon="
          fitted ? 'iconify lucide--arrow-right-from-line' : 'iconify lucide--unfold-horizontal'
        "
        @click="columnPrefs.setFit(!fitted, columns)"
      />
      <Button
        v-if="isDesktop"
        size="small"
        text
        severity="secondary"
        :aria-label="density === 'compact' ? t('table.comfortable') : t('table.compact')"
        :title="density === 'compact' ? t('table.comfortable') : t('table.compact')"
        :icon="density === 'compact' ? 'iconify lucide--rows-3' : 'iconify lucide--rows-4'"
        @click="density = density === 'compact' ? 'comfortable' : 'compact'"
      />
    </div>

    <DataTable
      v-if="isDesktop"
      :key="columnPrefs.tableKey.value"
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
      :reorderable-columns="true"
      :table-style="tableStyle"
      :state-storage="stateKey ? 'local' : undefined"
      :state-key="stateKey"
      paginator-template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink RowsPerPageDropdown CurrentPageReport"
      :current-page-report-template="t('table.pageReport')"
      class="app-data-table border border-surface-200 dark:border-surface-800"
      :class="{
        'app-table-comfortable': density === 'comfortable',
        'app-table-fit': columnPrefs.prefs.value.fit,
      }"
      :row-class="() => (hasRowClickListener ? 'cursor-pointer' : '')"
      :row-group-mode="groupField ? 'subheader' : undefined"
      :group-rows-by="groupField"
      data-key="id"
      @row-click="(event: any) => handleRowClick(event.data)"
      @page="handlePage"
      @sort="handleSort"
      @state-restore="handleStateRestore"
    >
      <template #empty><AppEmptyState :message="emptyMessage ?? t('common.empty')" /></template>
      <template v-if="groupField" #groupheader="{ data }"
        ><slot name="groupheader" :data="data"
      /></template>
      <component
        :is="column.node"
        v-for="column in columns"
        :key="column.key"
        v-bind="columnBindings(column)"
      />
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
          :icon="
            localSortOrder === 1
              ? 'iconify lucide--arrow-up-narrow-wide'
              : 'iconify lucide--arrow-down-wide-narrow'
          "
          :aria-label="localSortOrder === 1 ? t('table.ascending') : t('table.descending')"
          severity="secondary"
          outlined
          @click="toggleSortOrder"
        />
      </div>
      <div class="flex flex-col gap-1.5">
        <AppEmptyState
          v-if="!loading && rows.length === 0"
          :message="emptyMessage ?? t('common.empty')"
        />
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
