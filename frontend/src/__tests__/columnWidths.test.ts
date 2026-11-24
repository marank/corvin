import { describe, expect, it } from 'vitest'
import { fairShares, useColumnWidths } from '../components/ui/columnWidths'

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

describe('fairShares', () => {
  const round = (shares: number[]) => shares.map(Math.round)

  it('gives short columns all they need and cuts the long ones', () => {
    // Label, street, postal code / city, country, roles in 1163 px.
    expect(round(fairShares([381, 324, 191, 103, 235], 1163))).toEqual([330, 304, 191, 103, 235])
  })

  it('gives longer text more room when every column is too long', () => {
    const [name, city, email] = fairShares([443, 214, 285], 536)
    expect(name! + city! + email!).toBeCloseTo(536)
    expect(name).toBeGreaterThan(email!)
    expect(email).toBeGreaterThan(city!)
  })

  it('leaves other columns at zero', () => {
    expect(round(fairShares([0, 300, 0, 100], 200))).toEqual([0, 127, 0, 73])
  })
})
