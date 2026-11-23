import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref, type PropType } from 'vue'
import Column from 'primevue/column'
import AppDataTable from '../components/ui/AppDataTable.vue'
import AppIconButton from '../components/ui/AppIconButton.vue'
import { useTableDensity } from '../composables/useTableDensity'
import { answerConfirm, choose, click, pressEnter, screen, toasts } from './helpers/dom'
import { render, t } from './helpers/render'

interface Row {
  id: string
  name: string
  hours: number | null
  city: { name: string } | null
}

const rows: Row[] = [
  { id: 'a', name: 'Bravo', hours: 3, city: { name: 'Berlin' } },
  { id: 'b', name: 'Alpha', hours: null, city: null },
  { id: 'c', name: 'Charlie 10', hours: 12, city: { name: 'Köln' } },
  { id: 'd', name: 'Charlie 9', hours: 1, city: { name: 'Bonn' } },
]

/** A page with one client-side table, the way views use AppDataTable. */
const Host = defineComponent({
  props: {
    rows: { type: Array as PropType<Row[]>, default: () => rows },
    pageSize: { type: Number, default: 50 },
    deleteRow: { type: Function as PropType<(row: Row) => Promise<unknown>>, default: undefined },
    stateKey: { type: String, default: undefined },
    onOpen: { type: Function as PropType<(row: Row) => void>, default: undefined },
  },
  setup(props) {
    const deleted = ref(0)
    return () =>
      h('div', [
        h('output', `deleted:${deleted.value}`),
        h(
          AppDataTable<Row>,
          {
            rows: props.rows,
            pageSize: props.pageSize,
            selectable: !!props.deleteRow,
            deleteRow: props.deleteRow,
            stateKey: props.stateKey,
            onRowClick: props.onOpen,
            onBulkDeleted: () => deleted.value++,
          },
          () => [
            h(Column, { field: 'name', header: 'Name', sortable: true }),
            h(Column, { field: 'hours', header: 'Hours', sortable: true }),
            h(Column, { field: 'city.name', header: 'City' }),
            h(
              Column,
              { reorderableColumn: false },
              {
                body: ({ data }: { data: Row }) => [
                  h(AppIconButton, { icon: 'pi pi-pencil', label: `edit ${data.name}` }),
                ],
              },
            ),
          ],
        ),
      ])
  },
})

const names = () => screen.rows().map((row) => row[0])
/** The mobile cards (focusable when rows open on click). */
const cards = () =>
  [...screen.root.querySelectorAll('dl')].map((dl) => dl.closest<HTMLElement>('[tabindex]')!)

describe('AppDataTable', () => {
  it('sorts client-side, numbers as numbers and missing values last', async () => {
    await render(Host)
    expect(names()).toEqual(['Bravo', 'Alpha', 'Charlie 10', 'Charlie 9'])
    const [nameHeader, hoursHeader] = screen.root.querySelectorAll(
      'th[data-p-sortable-column="true"]',
    )
    await click(nameHeader!)
    expect(names()).toEqual(['Alpha', 'Bravo', 'Charlie 9', 'Charlie 10'])
    await click(nameHeader!)
    expect(names()).toEqual(['Charlie 10', 'Charlie 9', 'Bravo', 'Alpha'])
    await click(hoursHeader!)
    expect(screen.rows().map((row) => row[1])).toEqual(['1', '3', '12', ''])
    await click(hoursHeader!)
    expect(screen.rows().map((row) => row[1])).toEqual(['12', '3', '1', ''])
  })

  it('pages through more rows than fit', async () => {
    await render(Host, { props: { pageSize: 2 } })
    expect(names()).toEqual(['Bravo', 'Alpha'])
    await click(screen.button('Seite 2'))
    expect(names()).toEqual(['Charlie 10', 'Charlie 9'])
  })

  it('switches the row density for all tables and remembers it', async () => {
    await render(Host, { props: { deleteRow: () => Promise.resolve() } })
    expect(useTableDensity().value).toBe('compact')
    await click(screen.button(t('table.comfortable')))
    expect(useTableDensity().value).toBe('comfortable')
    expect(localStorage.getItem('table-density')).toBe('comfortable')
    await click(screen.button(t('table.compact')))
    expect(useTableDensity().value).toBe('compact')
  })

  it('opens a row on click', async () => {
    const onOpen = vi.fn()
    await render(Host, { props: { onOpen } })
    await click(screen.row('Alpha'))
    expect(onOpen).toHaveBeenCalledWith(rows[1])
  })

  it('gives truncated cells their text as tooltip', async () => {
    await render(Host)
    const cell = screen.row('Bravo').querySelector('td')!
    cell.classList.add('app-text')
    Object.defineProperty(cell, 'scrollWidth', { value: 200 })
    Object.defineProperty(cell, 'clientWidth', { value: 100 })
    cell.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }))
    expect(cell.title).toBe('Bravo')
  })

  describe('selection', () => {
    it('selects a page, clears it and deletes only after confirmation', async () => {
      const deleteRow = vi.fn((row: Row) =>
        row.id === 'c' ? Promise.reject(new Error('protected')) : Promise.resolve(),
      )
      await render(Host, { props: { deleteRow, pageSize: 3 } })
      await click(screen.button(t('table.select')))
      await click(screen.button(t('table.selectPage')))
      expect(screen.text()).toContain(t('table.selected', { count: 3 }))
      await click(screen.button(t('table.clearSelection')))
      expect(screen.text()).toContain(t('table.selected', { count: 0 }))
      expect(screen.button(t('table.deleteSelected', { count: 0 })).hasAttribute('disabled')).toBe(
        true,
      )

      // In selection mode a click on a row selects it instead of opening it.
      await click(screen.row('Bravo'))
      await click(screen.row('Charlie 10'))
      await click(screen.row('Bravo'))
      await click(screen.row('Alpha'))
      await click(screen.button(t('table.deleteSelected', { count: 2 })))
      await answerConfirm(t('common.cancel'))
      expect(deleteRow).not.toHaveBeenCalled()

      await click(screen.button(t('table.deleteSelected', { count: 2 })))
      await answerConfirm(t('common.delete'))
      expect(deleteRow.mock.calls.map(([row]) => row.id)).toEqual(['c', 'b'])
      expect(toasts()).toEqual([
        t('table.bulkDeleted', { count: 1 }),
        t('table.bulkDeleteFailed', { count: 1 }),
      ])
      expect(screen.text()).toContain('deleted:1')
      expect(screen.hasButton(t('table.select'))).toBe(true)
    })

    it('leaves selection mode with Done', async () => {
      await render(Host, { props: { deleteRow: () => Promise.resolve() } })
      await click(screen.button(t('table.select')))
      await click(screen.button(t('common.done')))
      expect(screen.hasButton(t('table.select'))).toBe(true)
    })
  })

  it('restores saved sorting and paging from the browser', async () => {
    localStorage.setItem(
      'people',
      JSON.stringify({ first: 2, rows: 2, sortField: 'name', sortOrder: -1, columnWidths: '' }),
    )
    await render(Host, { props: { stateKey: 'people', pageSize: 2 } })
    expect(names()).toEqual(['Bravo', 'Alpha'])
  })

  describe('on a phone', () => {
    it("shows the table's columns as label/value cards, utility buttons apart", async () => {
      await render(Host, { viewport: 'mobile' })
      expect(screen.root.querySelector('table')).toBeNull()
      const card = screen.root.querySelector('dl')!
      expect([...card.querySelectorAll('dt')].map((dt) => dt.textContent)).toEqual([
        'Name',
        'Hours',
        'City',
      ])
      expect([...card.querySelectorAll('dd')].map((dd) => dd.textContent)).toEqual([
        'Bravo',
        '3',
        'Berlin',
      ])
      expect(screen.text()).toContain('Alpha')
      expect(screen.text()).toContain('—')
      expect(screen.hasButton('edit Bravo')).toBe(true)
    })

    it('opens a card on click and on Enter', async () => {
      const onOpen = vi.fn()
      await render(Host, { viewport: 'mobile', props: { onOpen } })
      await click(cards()[0]!)
      await pressEnter(cards()[1]!)
      expect(onOpen.mock.calls.map(([row]) => (row as Row).id)).toEqual(['a', 'b'])
    })

    it('sorts with the sort select, offering the sortable columns', async () => {
      await render(Host, { viewport: 'mobile' })
      await choose(screen.select(t('table.sortBy')), 'Name')
      const order = () =>
        [...screen.root.querySelectorAll('dl')].map((dl) => dl.querySelector('dd')!.textContent)
      expect(order()).toEqual(['Alpha', 'Bravo', 'Charlie 9', 'Charlie 10'])
      await click(screen.button(t('table.ascending')))
      expect(order()).toEqual(['Charlie 10', 'Charlie 9', 'Bravo', 'Alpha'])
      // Missing values sort last either way, as on the desktop table.
      await choose(screen.select(t('table.sortBy')), 'Hours')
      expect(order()).toEqual(['Charlie 10', 'Bravo', 'Charlie 9', 'Alpha'])
      await click(screen.button(t('table.descending')))
      expect(order()).toEqual(['Charlie 9', 'Bravo', 'Charlie 10', 'Alpha'])
    })

    it('selects cards with their checkboxes', async () => {
      const deleteRow = vi.fn(() => Promise.resolve())
      await render(Host, { viewport: 'mobile', props: { deleteRow } })
      await click(screen.button(t('table.select')))
      const box = screen.root.querySelector<HTMLInputElement>('input[type=checkbox]')!
      box.checked = true
      box.dispatchEvent(new Event('change', { bubbles: true }))
      await click(cards()[0]!)
      expect(screen.text()).toContain(t('table.selected', { count: 0 }))
      await click(cards()[1]!)
      expect(screen.text()).toContain(t('table.selected', { count: 1 }))
    })

    it('pages with the compact paginator', async () => {
      await render(Host, { viewport: 'mobile', props: { pageSize: 2 } })
      expect(screen.root.querySelectorAll('dl')).toHaveLength(2)
      await click(screen.button(/^Nächste Seite$|^Next Page$/))
      expect(screen.text()).toContain('Charlie 10')
    })
  })
})
