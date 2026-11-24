import { onMounted, onUnmounted, ref, type Ref } from 'vue'

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
// hint the browser then gives them equal shares; this hands out the free width by what
// each column holds: short columns (a country, a phone number) get all they need, long
// ones are cut, the longest a little less than its neighbours. Measured from the rows on screen whenever they change and when the
// table comes into view (a table in a hidden tab measures nothing); a column the user
// resized keeps its width (PrimeVue's styles are !important).
const MAX_SHARE_PX = 512
let tableCount = 0

// Water-filling: the free width goes out by weight (the square root of each column's need, so
// longer text gets more room without starving the rest); a column whose part covers its
// need takes only that, and what it leaves goes round again.
export function fairShares(needs: number[], available: number): number[] {
  const shares = needs.map(() => 0)
  let open = needs.map((_, index) => index).filter((index) => needs[index]! > 0)
  let left = Math.max(0, available)
  const weight = (index: number) => Math.sqrt(needs[index]!)
  for (;;) {
    const total = open.reduce((sum, index) => sum + weight(index), 0)
    const covered = open.filter((index) => needs[index]! <= (left * weight(index)) / total)
    if (!covered.length) {
      for (const index of open) shares[index] = (left * weight(index)) / total
      return shares
    }
    for (const index of covered) {
      shares[index] = needs[index]!
      left -= needs[index]!
    }
    open = open.filter((index) => !covered.includes(index))
  }
}

interface Measured {
  // Width the text of each app-text column needs, padding included; 0 for other columns.
  needs: number[]
  // Width left for the app-text columns once the others took theirs.
  available: number
}

function measureColumns(table: HTMLTableElement): Measured {
  const headers = [...(table.tHead?.rows[0]?.cells ?? [])]
  const rows = [...(table.tBodies[0]?.rows ?? [])].filter(
    (row) => row.cells.length === headers.length,
  )
  const range = document.createRange()
  let available = table.parentElement?.clientWidth ?? 0
  const needs = headers.map((header, index) => {
    if (!header.classList.contains('app-text')) {
      available -= header.offsetWidth
      return 0
    }
    let width = 0
    for (const row of rows) {
      const cell = row.cells[index]!
      range.selectNodeContents(cell)
      const style = getComputedStyle(cell)
      const padding = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight)
      // Rounded up: a fraction of a pixel short already shows an ellipsis.
      width = Math.max(width, Math.ceil(range.getBoundingClientRect().width + padding))
    }
    return Math.min(MAX_SHARE_PX, width)
  })
  return { needs, available }
}

export function useTextColumnShares(root: Ref<HTMLElement | undefined>) {
  const id = `app-table-${++tableCount}`
  let style: HTMLStyleElement | undefined

  function update() {
    const table = root.value?.querySelector<HTMLTableElement>('table')
    // jsdom (tests) has no layout to measure.
    if (!table || typeof document.createRange().getBoundingClientRect !== 'function') return
    const { needs, available } = measureColumns(table)
    const total = needs.reduce((sum, need) => sum + need, 0)
    // Each column gets at least its share (min-width); room to spare goes by need (width %).
    // Without room, fairShares decides who is cut.
    const widths = total <= available ? needs : fairShares(needs, available)
    const sum = widths.reduce((acc, width) => acc + width, 0)
    style ??= document.head.appendChild(document.createElement('style'))
    style.textContent = widths
      .map((width, index) =>
        sum && width
          ? `#${id} .p-datatable-tbody > tr > td:nth-child(${index + 1}) { width: ${((width / sum) * 100).toFixed(1)}%; min-width: ${Math.floor(width)}px; }`
          : '',
      )
      .join('\n')
  }

  // jsdom (tests) has no ResizeObserver.
  const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(update) : undefined
  onMounted(() => root.value && observer?.observe(root.value))
  onUnmounted(() => {
    observer?.disconnect()
    style?.remove()
  })
  return { id, update }
}
