import { onUnmounted, ref, type Ref } from 'vue'

// PrimeVue stores the measured column widths with every state save and restores them with
// !important, which freezes the automatic layout at whatever window size and data the first
// visit had. Widths are kept only once the user resized a column; until then each visit
// lays the table out anew. `reset` goes back to the automatic layout.
const markerKey = (stateKey: string) => `${stateKey}:custom-widths`

export function useColumnWidths(stateKey: string | undefined) {
  const custom = ref(!!stateKey && localStorage.getItem(markerKey(stateKey)) === '1')
  // Bumped to remount the DataTable, which drops PrimeVue's width styles.
  const tableKey = ref(0)

  function dropSavedWidths() {
    if (!stateKey || custom.value) return
    const saved = localStorage.getItem(stateKey)
    if (!saved) return
    const state = JSON.parse(saved) as Record<string, unknown>
    if (!('columnWidths' in state)) return
    delete state.columnWidths
    delete state.tableWidth
    localStorage.setItem(stateKey, JSON.stringify(state))
  }

  function markResized() {
    if (!stateKey) return
    custom.value = true
    localStorage.setItem(markerKey(stateKey), '1')
  }

  function reset() {
    if (!stateKey) return
    custom.value = false
    localStorage.removeItem(markerKey(stateKey))
    dropSavedWidths()
    tableKey.value++
  }

  // Before the DataTable mounts: widths saved by earlier versions were never chosen by anyone.
  dropSavedWidths()
  return { custom, tableKey, dropSavedWidths, markResized, reset }
}

// Free-text columns (td.app-text, see style.css) may shrink below their content. Without a
// hint the browser then gives them equal shares; this hands each a share of the free width
// in proportion to the text it holds, so a long name gets more room than a short city.
// Measured per render from the rows on screen; a column the user resized keeps its width
// (PrimeVue's styles are !important).
const MAX_SHARE_PX = 512
let tableCount = 0

function textWidths(table: HTMLTableElement): number[] {
  const headers = [...(table.tHead?.rows[0]?.cells ?? [])]
  const rows = [...(table.tBodies[0]?.rows ?? [])].filter(
    (row) => row.cells.length === headers.length,
  )
  const range = document.createRange()
  return headers.map((header, index) => {
    if (!header.classList.contains('app-text')) return 0
    let width = 0
    for (const row of rows) {
      range.selectNodeContents(row.cells[index]!)
      width = Math.max(width, range.getBoundingClientRect().width)
    }
    return Math.min(MAX_SHARE_PX, width)
  })
}

export function useTextColumnShares(root: Ref<HTMLElement | undefined>) {
  const id = `app-table-${++tableCount}`
  let style: HTMLStyleElement | undefined

  function update() {
    const table = root.value?.querySelector<HTMLTableElement>('table')
    // jsdom (tests) has no layout to measure.
    if (!table || typeof document.createRange().getBoundingClientRect !== 'function') return
    const widths = textWidths(table)
    const total = widths.reduce((sum, width) => sum + width, 0)
    style ??= document.head.appendChild(document.createElement('style'))
    style.textContent = widths
      .map((width, index) =>
        total && width
          ? `#${id} .p-datatable-tbody > tr > td:nth-child(${index + 1}) { width: ${((width / total) * 100).toFixed(1)}%; }`
          : '',
      )
      .join('\n')
  }

  onUnmounted(() => style?.remove())
  return { id, update }
}
