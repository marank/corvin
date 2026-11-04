import { ref, watch } from 'vue'

export type TableDensity = 'compact' | 'comfortable'

const KEY = 'table-density'

function stored(): TableDensity {
  try {
    return localStorage.getItem(KEY) === 'comfortable' ? 'comfortable' : 'compact'
  } catch {
    return 'compact'
  }
}

// One row density for all tables, remembered per browser.
const density = ref<TableDensity>(stored())
watch(density, (value) => {
  try {
    localStorage.setItem(KEY, value)
  } catch {
    // Storage unavailable (private mode): the choice lasts for this session only.
  }
})

export function useTableDensity() {
  return density
}
