import { describe, expect, it } from 'vitest'
import { useColumnWidths } from '../components/ui/columnWidths'

const saved = (key: string) => JSON.parse(localStorage.getItem(key) ?? 'null') as unknown

describe('useColumnWidths', () => {
  it('drops widths PrimeVue measured on its own', () => {
    localStorage.setItem('t', JSON.stringify({ sortField: 'name', columnWidths: '68,128,214' }))
    const widths = useColumnWidths('t')
    expect(saved('t')).toEqual({ sortField: 'name' })
    localStorage.setItem('t', JSON.stringify({ sortField: 'name', columnWidths: '70,130,210' }))
    widths.dropSavedWidths()
    expect(saved('t')).toEqual({ sortField: 'name' })
    expect(widths.custom.value).toBe(false)
  })

  it('keeps widths the user resized until reset', () => {
    const widths = useColumnWidths('t')
    widths.markResized()
    localStorage.setItem('t', JSON.stringify({ columnWidths: '68,300,214' }))
    widths.dropSavedWidths()
    expect(saved('t')).toEqual({ columnWidths: '68,300,214' })
    // A later visit still trusts them.
    expect(useColumnWidths('t').custom.value).toBe(true)
    expect(saved('t')).toEqual({ columnWidths: '68,300,214' })

    const key = widths.tableKey.value
    widths.reset()
    expect(saved('t')).toEqual({})
    expect(widths.custom.value).toBe(false)
    expect(widths.tableKey.value).toBe(key + 1)
    expect(useColumnWidths('t').custom.value).toBe(false)
  })

  it('does nothing for tables without saved state', () => {
    const widths = useColumnWidths(undefined)
    widths.markResized()
    widths.reset()
    expect(widths.custom.value).toBe(false)
    expect(localStorage.length).toBe(0)
  })
})
