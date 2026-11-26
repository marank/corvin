import { Fragment, computed, onMounted, onUnmounted, ref, watch, type Ref, type VNode } from 'vue'
import Column from 'primevue/column'

// Column model of AppDataTable. The table lays out with `table-layout: fixed`: every column
// has a width (its default, or what the user dragged it to), except the free-text columns
// (<Column class="app-text">) left at their default, which share the rest of the row. That
// keeps the layout still while paging, sorting and filtering, and a dragged edge moves
// exactly as far as the mouse. Views give defaults with `header-style="width: 7rem"`;
// `hidden` on a <Column> means "hidden until the user shows it" in the column chooser.

export interface TableColumn {
  key: string
  header: string
  node: VNode
  // Row actions, checkboxes: always shown, never resized or offered in the chooser.
  utility: boolean
  // Free text (app-text): without a width of its own it fills the row.
  text: boolean
  defaultWidth: string | undefined
  defaultHidden: boolean
}

export interface ColumnPrefs {
  widths: Record<string, number>
  visible: Record<string, boolean>
}

export const MIN_WIDTH_PX = 48
const TEXT_MIN = '8rem'
const NUM_DEFAULT = '7rem'
const OTHER_DEFAULT = '8rem'
const UTILITY_DEFAULT = '3.5rem'

type Props = Record<string, unknown>

function flatten(nodes: VNode[]): VNode[] {
  return nodes.flatMap((node) =>
    node.type === Fragment && Array.isArray(node.children)
      ? flatten(node.children as VNode[])
      : [node],
  )
}

function prop(props: Props, camel: string, kebab: string): unknown {
  return props[camel] ?? props[kebab]
}

// A boolean attribute written bare in a template (`hidden`) arrives as ''.
function flag(value: unknown): boolean {
  return value === '' || value === true || value === 'true'
}

function widthFromStyle(style: unknown): string | undefined {
  if (style && typeof style === 'object') {
    const width = (style as Record<string, unknown>).width
    return typeof width === 'string' ? width : undefined
  }
  if (typeof style === 'string') return /(?:^|;)\s*width\s*:\s*([^;]+)/.exec(style)?.[1]?.trim()
  return undefined
}

function classes(value: unknown): string {
  if (Array.isArray(value)) return value.map(classes).join(' ')
  if (value && typeof value === 'object')
    return Object.keys(value)
      .filter((key) => (value as Record<string, unknown>)[key])
      .join(' ')
  return typeof value === 'string' ? value : ''
}

function text(value: unknown): string {
  return typeof value === 'string' || typeof value === 'number' ? String(value) : ''
}

function toColumn(node: VNode, index: number): TableColumn {
  const p = (node.props ?? {}) as Props
  const cls = ` ${classes(p.class)} `
  const reorderable = prop(p, 'reorderableColumn', 'reorderable-column')
  return {
    key: text(prop(p, 'columnKey', 'column-key')) || text(p.field) || `col-${index}`,
    header: text(p.header),
    node,
    utility: reorderable === false || reorderable === 'false',
    text: cls.includes(' app-text '),
    defaultWidth: widthFromStyle(prop(p, 'headerStyle', 'header-style')),
    defaultHidden: flag(p.hidden),
  }
}

export function readColumns(nodes: VNode[] | undefined): TableColumn[] {
  return flatten(nodes ?? [])
    .filter((node) => node.type === Column)
    .map(toColumn)
}

function storageKey(stateKey: string) {
  return `${stateKey}:columns`
}

function load(stateKey: string | undefined): ColumnPrefs {
  const empty = { widths: {}, visible: {} }
  if (!stateKey) return empty
  try {
    // Widths of the old automatic layout: never chosen by anyone.
    localStorage.removeItem(`${stateKey}:custom-widths`)
    const saved = JSON.parse(
      localStorage.getItem(storageKey(stateKey)) ?? 'null',
    ) as Partial<ColumnPrefs> | null
    return { widths: saved?.widths ?? {}, visible: saved?.visible ?? {} }
  } catch {
    return empty
  }
}

export function useColumnPrefs(stateKey: string | undefined) {
  const prefs = ref<ColumnPrefs>(load(stateKey))
  // Bumped to remount the DataTable after a reset (PrimeVue keeps the column order).
  const tableKey = ref(0)
  watch(
    prefs,
    (value) => {
      if (!stateKey) return
      try {
        localStorage.setItem(storageKey(stateKey), JSON.stringify(value))
      } catch {
        // Storage unavailable (private mode): the layout lasts for this visit.
      }
    },
    { deep: true },
  )

  function isVisible(column: TableColumn): boolean {
    return column.utility || (prefs.value.visible[column.key] ?? !column.defaultHidden)
  }

  function setVisible(column: TableColumn, visible: boolean) {
    prefs.value.visible[column.key] = visible
  }

  function setWidth(key: string, px: number | undefined) {
    if (px === undefined) delete prefs.value.widths[key]
    else prefs.value.widths[key] = Math.max(MIN_WIDTH_PX, Math.round(px))
  }

  const customized = computed(
    () => Object.keys(prefs.value.widths).length > 0 || Object.keys(prefs.value.visible).length > 0,
  )

  function reset() {
    prefs.value = { widths: {}, visible: {} }
    if (stateKey) {
      try {
        const state = JSON.parse(localStorage.getItem(stateKey) ?? 'null') as Props | null
        if (state) {
          delete state.columnOrder
          delete state.columnWidths
          delete state.tableWidth
          localStorage.setItem(stateKey, JSON.stringify(state))
        }
      } catch {
        // Nothing saved to clean up.
      }
    }
    tableKey.value++
  }

  return { prefs, tableKey, isVisible, setVisible, setWidth, customized, reset }
}

export type ColumnPrefsApi = ReturnType<typeof useColumnPrefs>

// The width a column asks for: the user's, its default, or none (free text: fills the row).
export function columnWidth(column: TableColumn, prefs: ColumnPrefs): string | undefined {
  const px = prefs.widths[column.key]
  if (px) return `${px}px`
  if (column.defaultWidth) return column.defaultWidth
  if (column.text) return undefined
  if (column.utility) return UTILITY_DEFAULT
  const cls = ` ${classes(column.node.props?.class)} `
  return cls.includes(' app-num ') ? NUM_DEFAULT : OTHER_DEFAULT
}

// "7rem", "120px" → px; anything else (%, calc) counts as the text minimum.
export function toPx(width: string, remPx: number): number {
  const match = /^([\d.]+)(rem|px)$/.exec(width.trim())
  if (!match) return toPx(TEXT_MIN, remPx)
  return match[2] === 'rem' ? Number(match[1]) * remPx : Number(match[1])
}

export interface ColumnLayout {
  // px per column; undefined: the column takes what is left of the row.
  widths: Map<string, number | undefined>
  // Below this the table scrolls sideways instead of squeezing its columns.
  minWidth: number
}

// Free-text columns at their default share the free width. If the user gave each one a
// width (or there are none), the last visible content column fills the row instead, at
// least as wide as it was set. When the row is too narrow, free-text columns with a default
// width give way first (down to the text minimum); only then does the table scroll.
export function layoutColumns(
  columns: TableColumn[],
  prefs: ColumnPrefs,
  available: number,
  remPx: number,
): ColumnLayout {
  const textMin = toPx(TEXT_MIN, remPx)
  const asked = columns.map((column) => {
    const width = columnWidth(column, prefs)
    return { column, px: width ? toPx(width, remPx) : undefined }
  })
  const fill = new Set(asked.filter((a) => a.px === undefined).map((a) => a.column.key))
  if (!fill.size) {
    const last = columns.filter((column) => !column.utility).at(-1)
    if (last) fill.add(last.key)
  }
  const needed = (a: { column: TableColumn; px: number | undefined }) =>
    fill.has(a.column.key) ? Math.max(a.px ?? 0, textMin) : a.px!
  const total = asked.reduce((sum, a) => sum + needed(a), 0)
  const yielding = asked.filter(
    (a) => !fill.has(a.column.key) && a.column.text && !prefs.widths[a.column.key],
  )
  const room = yielding.reduce((sum, a) => sum + a.px! - Math.min(a.px!, textMin), 0)
  const cut = Math.min(Math.max(0, total - available), room)
  const widths = new Map<string, number | undefined>()
  for (const a of asked) {
    if (fill.has(a.column.key)) widths.set(a.column.key, undefined)
    else if (yielding.includes(a) && room > 0)
      widths.set(a.column.key, a.px! - (cut * (a.px! - Math.min(a.px!, textMin))) / room)
    else widths.set(a.column.key, a.px)
  }
  return { widths, minWidth: Math.ceil(total - cut) }
}

// Dragging the right edge of a header cell, listened for on the table's root.
export function useColumnResize(
  root: Ref<HTMLElement | undefined>,
  setWidth: (key: string, px: number | undefined) => void,
) {
  const HANDLE_PX = 8
  const resizing = ref(false)

  function handleOf(event: MouseEvent): { th: HTMLTableCellElement; key: string } | undefined {
    const th = (event.target as HTMLElement).closest<HTMLTableCellElement>('th[data-col-key]')
    if (!th || !root.value?.contains(th)) return undefined
    const rect = th.getBoundingClientRect()
    // No layout (jsdom): no edge to grab.
    if (!rect.width) return undefined
    if (event.clientX < rect.right - HANDLE_PX || event.clientX > rect.right + 2) return undefined
    return { th, key: th.dataset.colKey! }
  }

  // Capture phase: PrimeVue must neither start a column drag nor sort on this click.
  function onMouseDown(event: MouseEvent) {
    if (event.button !== 0) return
    const handle = handleOf(event)
    if (!handle) return
    event.preventDefault()
    event.stopPropagation()
    const startX = event.clientX
    const startWidth = handle.th.getBoundingClientRect().width
    resizing.value = true
    document.body.classList.add('app-col-resizing')
    const move = (e: MouseEvent) => setWidth(handle.key, startWidth + e.clientX - startX)
    const up = () => {
      document.removeEventListener('mousemove', move)
      document.removeEventListener('mouseup', up)
      document.body.classList.remove('app-col-resizing')
      // The click that follows mouseup must not sort the column.
      setTimeout(() => (resizing.value = false))
    }
    document.addEventListener('mousemove', move)
    document.addEventListener('mouseup', up)
  }

  function onClick(event: MouseEvent) {
    if (!resizing.value && !handleOf(event)) return
    event.preventDefault()
    event.stopPropagation()
  }

  // Double-click on the edge: back to the column's default width.
  function onDoubleClick(event: MouseEvent) {
    const handle = handleOf(event)
    if (!handle) return
    event.stopPropagation()
    setWidth(handle.key, undefined)
  }

  // Native capture listeners, not template ones: Vue skips handlers attached after an event's
  // timestamp, which a capture listener on the root sets first (fake clocks in tests).
  const listeners = [
    ['mousedown', onMouseDown],
    ['click', onClick],
    ['dblclick', onDoubleClick],
  ] as const
  onMounted(() => listeners.forEach(([type, fn]) => root.value?.addEventListener(type, fn, true)))
  onUnmounted(() =>
    listeners.forEach(([type, fn]) => root.value?.removeEventListener(type, fn, true)),
  )
}
