import { describe, expect, it } from 'vitest'
import { h } from 'vue'
import Column from 'primevue/column'
import { layoutColumns, readColumns, restColumn, toPx } from '../components/ui/tableColumns'

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

  it('reads the fill marker, and a width among other styles', () => {
    const [note] = readColumns([
      h(Column, {
        field: 'note',
        class: 'app-text app-fill',
        headerStyle: 'min-width: 2rem; width: 9rem',
      }),
    ])
    expect([note!.fill, note!.defaultWidth]).toEqual([true, '9rem'])
  })

  it('takes `hidden` as hidden by default', () => {
    const [column] = readColumns([h(Column, { field: 'x', hidden: '' } as never)])
    expect(column!.defaultHidden).toBe(true)
  })
})

describe('restColumn', () => {
  const read = (...specs: Record<string, unknown>[]) =>
    readColumns(specs.map((spec) => h(Column, spec)))

  it('is the column marked app-fill', () => {
    const cols = read({ field: 'a', class: 'app-text app-fill' }, { field: 'b', class: 'app-text' })
    expect(restColumn(cols)?.key).toBe('a')
  })

  it('else the last free-text column without a width of its own', () => {
    const cols = read(
      { field: 'a', class: 'app-text' },
      { field: 'b', class: 'app-text' },
      { field: 'c', class: 'app-text', headerStyle: 'width: 9rem' },
      { field: 'd', class: 'app-num' },
    )
    expect(restColumn(cols)?.key).toBe('b')
  })

  it('else the last content column', () => {
    const cols = read({ field: 'a' }, { field: 'b' }, { header: 'x', reorderableColumn: false })
    expect(restColumn(cols)?.key).toBe('b')
  })
})

describe('layoutColumns', () => {
  it('gives every column its width, the rest column none: it takes the spare width', () => {
    const layout = layoutColumns(columns, noPrefs, REM)
    // 6rem, 12rem, (rest), num 7rem, actions 3.5rem
    expect(widths(layout)).toEqual({
      number: 96,
      customer: 192,
      note: undefined,
      total: 112,
      'col-4': 56,
    })
    // The rest column at the text default, 12rem.
    expect(layout.minWidth).toBe(96 + 192 + 192 + 112 + 56)
  })

  it("takes the user's widths; the rest column's is its least", () => {
    const layout = layoutColumns(
      columns,
      { widths: { customer: 100, note: 300 }, visible: {} },
      REM,
    )
    expect(widths(layout).customer).toBe(100)
    expect(widths(layout).note).toBeUndefined()
    expect(layout.minWidth).toBe(96 + 100 + 300 + 112 + 56)
  })

  it('reads rem and px', () => {
    expect(toPx('7rem', REM)).toBe(112)
    expect(toPx('90px', REM)).toBe(90)
  })
})
