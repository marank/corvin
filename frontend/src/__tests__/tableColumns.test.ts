import { describe, expect, it } from 'vitest'
import { h } from 'vue'
import Column from 'primevue/column'
import { layoutColumns, readColumns, toPx } from '../components/ui/tableColumns'

const REM = 16
const columns = readColumns([
  h(Column, { field: 'number', header: 'No.', headerStyle: 'width: 6rem' }),
  h(Column, {
    field: 'customer',
    header: 'Customer',
    class: 'app-text',
    headerStyle: 'width: 12rem',
  }),
  h(Column, { field: 'note', header: 'Note', class: 'app-text' }),
  h(Column, { field: 'total', header: 'Total', class: 'app-num' }),
  h(Column, { header: 'Actions', reorderableColumn: false }),
])
const noPrefs = { widths: {}, visible: {} }
const widths = (layout: ReturnType<typeof layoutColumns>) => Object.fromEntries(layout.widths)

describe('readColumns', () => {
  it('reads key, header, defaults and kind from the <Column>s', () => {
    expect(columns.map((c) => [c.key, c.text, c.utility, c.defaultWidth])).toEqual([
      ['number', false, false, '6rem'],
      ['customer', true, false, '12rem'],
      ['note', true, false, undefined],
      ['total', false, false, undefined],
      ['col-4', false, true, undefined],
    ])
  })

  it('reads optional columns and a minimum width for free text', () => {
    const [note, date] = readColumns([
      h(Column, { field: 'note', class: 'app-text', headerStyle: 'min-width: 11rem' }),
      h(Column, { field: 'date', class: 'app-optional', headerStyle: 'width: 8rem' }),
    ])
    expect([note!.minWidth, note!.defaultWidth, note!.optional]).toEqual([
      '11rem',
      undefined,
      false,
    ])
    expect([date!.minWidth, date!.defaultWidth, date!.optional]).toEqual([undefined, '8rem', true])
  })

  it('takes `hidden` as hidden by default', () => {
    const [column] = readColumns([h(Column, { field: 'x', hidden: '' } as never)])
    expect(column!.defaultHidden).toBe(true)
  })
})

describe('layoutColumns', () => {
  it('gives free text without a width the rest of the row', () => {
    const layout = layoutColumns(columns, noPrefs, 1200, REM)
    // 6rem, 12rem, (fills), num 7rem, actions 3.5rem
    expect(widths(layout)).toEqual({
      number: 96,
      customer: 192,
      note: undefined,
      total: 112,
      'col-4': 56,
    })
    expect(layout.minWidth).toBe(96 + 192 + 128 + 112 + 56)
  })

  it('narrows free-text defaults before the table has to scroll', () => {
    const layout = layoutColumns(columns, noPrefs, 500, REM)
    expect(widths(layout).customer).toBe(128)
    expect(layout.minWidth).toBe(96 + 128 + 128 + 112 + 56)
  })

  it("keeps the user's widths once set: nothing fills, the table is their sum", () => {
    const prefs = { widths: { note: 300 }, visible: {} }
    const layout = layoutColumns(columns, prefs, 500, REM)
    expect(widths(layout)).toEqual({
      number: 96,
      customer: 192,
      note: 300,
      total: 112,
      'col-4': 56,
    })
    expect(layout.width).toBe(96 + 192 + 300 + 112 + 56)
    expect(layout.minWidth).toBe(layout.width)
  })

  it('keeps free text at its own minimum', () => {
    const [note] = readColumns([
      h(Column, { field: 'note', class: 'app-text', headerStyle: 'min-width: 11rem' }),
    ])
    expect(layoutColumns([note!], noPrefs, 100, REM).minWidth).toBe(176)
  })

  it('reads rem and px', () => {
    expect(toPx('7rem', REM)).toBe(112)
    expect(toPx('90px', REM)).toBe(90)
  })
})
