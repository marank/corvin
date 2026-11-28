import { Fragment, computed, onMounted, onUnmounted, ref, watch, type Ref, type VNode } from 'vue'
import Column from 'primevue/column'

// Column model of AppDataTable, one rule for every table: each column has a width (its
// default, or what the user dragged it to); a dragged edge follows the mouse (see dragOf). One
// column, the rest column, also takes the row's spare width: <Column class="app-fill">, else
// the last free-text column (class="app-text") without a default width, else the last
// column. When the columns don't fit, the table scrolls sideways. Views give defaults with
// `header-style="width: 7rem"`; `hidden` on a <Column> means "hidden until the user shows it"
// in the column chooser.

export interface TableColumn {
  key: string
  header: string
  node: VNode
  // Row actions, checkboxes: always shown, never resized or offered in the chooser.
  utility: boolean
  // Free text (app-text).
  text: boolean
  // Takes the row's spare width (app-fill).
  fill: boolean
  defaultWidth: string | undefined
  defaultHidden: boolean
}

export interface ColumnPrefs {
  widths: Record<string, number>
  visible: Record<string, boolean>
}

export const MIN_WIDTH_PX = 48
const TEXT_DEFAULT = '12rem'
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

function fromStyle(style: unknown, name: string): string | undefined {
  if (style && typeof style === 'object') {
    const value = (style as Record<string, unknown>)[name]
    return typeof value === 'string' ? value : undefined
  }
  if (typeof style !== 'string') return undefined
  return new RegExp(`(?:^|;)\\s*${name}\\s*:\\s*([^;]+)`).exec(style)?.[1]?.trim()
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
    fill: cls.includes(' app-fill '),
    defaultWidth: fromStyle(prop(p, 'headerStyle', 'header-style'), 'width'),
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

// A column's width: the user's, its default, or the default of its kind.
export function columnWidth(column: TableColumn, prefs: ColumnPrefs): string {
  const px = prefs.widths[column.key]
  if (px) return `${px}px`
  if (column.defaultWidth) return column.defaultWidth
  if (column.utility) return UTILITY_DEFAULT
  if (column.text) return TEXT_DEFAULT
  const cls = ` ${classes(column.node.props?.class)} `
  return cls.includes(' app-num ') ? NUM_DEFAULT : OTHER_DEFAULT
}

// "7rem", "120px" → px; anything else (%, calc) counts as the text default.
export function toPx(width: string, remPx: number): number {
  const match = /^([\d.]+)(rem|px)$/.exec(width.trim())
  if (!match) return toPx(TEXT_DEFAULT, remPx)
  return match[2] === 'rem' ? Number(match[1]) * remPx : Number(match[1])
}

// The column taking the row's spare width (see the top of this file).
export function restColumn(columns: TableColumn[]): TableColumn | undefined {
  const content = columns.filter((column) => !column.utility)
  return (
    content.find((column) => column.fill) ??
    content.filter((column) => column.text && !column.defaultWidth).at(-1) ??
    content.at(-1)
  )
}

export interface ColumnLayout {
  // px per column; undefined for the rest column, which takes what is left of the row.
  widths: Map<string, number | undefined>
  // All columns at their widths: below this the table scrolls sideways.
  minWidth: number
}

export function layoutColumns(
  columns: TableColumn[],
  prefs: ColumnPrefs,
  remPx: number,
): ColumnLayout {
  const rest = restColumn(columns)
  const widths = new Map<string, number | undefined>()
  let minWidth = 0
  for (const column of columns) {
    const px = toPx(columnWidth(column, prefs), remPx)
    minWidth += px
    widths.set(column.key, column === rest ? undefined : px)
  }
  return { widths, minWidth: Math.ceil(minWidth) }
}

export interface ResizeTarget {
  setWidth: (key: string, px: number | undefined) => void
  // The rest column's key, and the least it may shrink to: its own width.
  restKey: () => string | undefined
  restLeast: () => number
}

const widthOf = (th: HTMLElement) => th.getBoundingClientRect().width
const keyOf = (th: HTMLElement) => th.dataset.colKey!

// What a drag of the edge between `th` and the next column changes. The line follows the
// mouse: the column on the far side from the rest column changes, the rest column evens it out
// and the columns between them move along unchanged. The drag stops where the rest column
// reaches its least width or the changed column 48px.
function dragOf(th: HTMLElement, headers: HTMLElement[], target: ResizeTarget) {
  const index = headers.indexOf(th)
  const rest = headers.find((h) => keyOf(h) === target.restKey())
  const spare = rest ? Math.max(0, widthOf(rest) - target.restLeast()) : 0
  const clamp = (dx: number, least: number, most: number) => Math.min(Math.max(dx, least), most)
  // A column gets a width of its own only once the drag actually moved it.
  let moved = false
  const set = (h: HTMLElement, px: number, start: number) => {
    moved ||= px !== start
    if (moved) target.setWidth(keyOf(h), px)
  }
  if (!rest || headers.indexOf(rest) > index) {
    const left = widthOf(th)
    return (dx: number) => set(th, left + clamp(dx, MIN_WIDTH_PX - left, spare), left)
  }
  const next = headers[index + 1]!
  const right = widthOf(next)
  return (dx: number) => set(next, right - clamp(dx, -spare, right - MIN_WIDTH_PX), right)
}

// Dragging the right edge of a header cell (not the last one's: that is the table's own),
// listened for on the table's root.
export function useColumnResize(root: Ref<HTMLElement | undefined>, target: ResizeTarget) {
  const HANDLE_PX = 8
  const resizing = ref(false)

  const headersOf = (th: HTMLElement) => [
    ...(th.parentElement?.querySelectorAll<HTMLElement>('th[data-col-key]') ?? []),
  ]

  function handleOf(event: MouseEvent): HTMLTableCellElement | undefined {
    const th = (event.target as HTMLElement).closest<HTMLTableCellElement>('th[data-col-key]')
    if (!th || !root.value?.contains(th)) return undefined
    if (headersOf(th).at(-1) === th) return undefined
    const rect = th.getBoundingClientRect()
    // No layout (jsdom): no edge to grab.
    if (!rect.width) return undefined
    if (event.clientX < rect.right - HANDLE_PX || event.clientX > rect.right + 2) return undefined
    return th
  }

  // Capture phase: PrimeVue must neither start a column drag nor sort on this click.
  function onMouseDown(event: MouseEvent) {
    if (event.button !== 0) return
    const th = handleOf(event)
    if (!th) return
    event.preventDefault()
    event.stopPropagation()
    const apply = dragOf(th, headersOf(th), target)
    const startX = event.clientX
    resizing.value = true
    document.body.classList.add('app-col-resizing')
    const move = (e: MouseEvent) => apply(e.clientX - startX)
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
    const th = handleOf(event)
    if (!th) return
    event.stopPropagation()
    target.setWidth(keyOf(th), undefined)
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
