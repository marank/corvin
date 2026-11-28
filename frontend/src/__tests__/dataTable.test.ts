import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h, type PropType } from 'vue'
import Column from 'primevue/column'
import AppDataTable from '../components/ui/AppDataTable.vue'
import AppIconButton from '../components/ui/AppIconButton.vue'
import { useTableDensity } from '../composables/useTableDensity'
import { choose, click, pressEnter, screen } from './helpers/dom'
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
    stateKey: { type: String, default: undefined },
    onOpen: { type: Function as PropType<(row: Row) => void>, default: undefined },
    // Name as free text: then it is the rest column, left of the others.
    textName: { type: Boolean, default: false },
  },
  setup(props) {
    return () =>
      h('div', [
        h(
          AppDataTable<Row>,
          {
            rows: props.rows,
            pageSize: props.pageSize,
            stateKey: props.stateKey,
            onRowClick: props.onOpen,
          },
          () => [
            h(Column, {
              field: 'name',
              header: 'Name',
              sortable: true,
              class: props.textName ? 'app-text' : undefined,
            }),
            h(Column, { field: 'hours', header: 'Hours', sortable: true }),
            h(Column, { field: 'city.name', header: 'City' }),
            h(Column, { field: 'name', columnKey: 'nick', header: 'Nick', hidden: true }),
            h(
              Column,
              { reorderableColumn: false },
              {
                body: ({ data }: { data: Row }) => [
                  h(AppIconButton, { icon: 'iconify lucide--pencil', label: `edit ${data.name}` }),
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
    await render(Host)
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

  it('restores saved sorting and paging from the browser', async () => {
    localStorage.setItem(
      'people',
      JSON.stringify({ first: 2, rows: 2, sortField: 'name', sortOrder: -1, columnWidths: '' }),
    )
    await render(Host, { props: { stateKey: 'people', pageSize: 2 } })
    expect(names()).toEqual(['Bravo', 'Alpha'])
  })

  describe('columns', () => {
    const headers = () => [...screen.root.querySelectorAll('thead th')].map((th) => th.textContent)
    const chooserBox = (label: string) =>
      [...document.querySelectorAll('label')]
        .find((el) => el.textContent.trim() === label)!
        .querySelector('input')!

    it('shows and hides columns from the chooser and remembers it per table', async () => {
      await render(Host, { props: { stateKey: 'people' } })
      expect(headers()).toEqual(['Name', 'Hours', 'City', ''])
      await click(screen.button(t('table.columns')))
      await click(chooserBox('Nick'))
      await click(chooserBox('City'))
      expect(headers()).toEqual(['Name', 'Hours', 'Nick', ''])
      expect(JSON.parse(localStorage.getItem('people:columns')!)).toEqual({
        widths: {},
        visible: { nick: true, 'city.name': false },
      })
      await click(screen.button(t('table.resetColumns')))
      expect(headers()).toEqual(['Name', 'Hours', 'City', ''])
    })

    it('keeps at least one column', async () => {
      await render(Host, { props: { stateKey: 'people' } })
      await click(screen.button(t('table.columns')))
      await click(chooserBox('Hours'))
      await click(chooserBox('City'))
      expect(chooserBox('Name').disabled).toBe(true)
    })

    const mouse = (type: string, target: EventTarget, clientX: number) =>
      target.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, clientX }))
    const header = (key: string, right: number, width: number) => {
      const th = screen.root.querySelector<HTMLElement>(`th[data-col-key="${key}"]`)!
      th.getBoundingClientRect = () => ({ right, width }) as DOMRect
      return th
    }
    const drag = (th: HTMLElement, from: number, to: number) => {
      mouse('mousedown', th, from)
      mouse('mousemove', document, to)
      mouse('mouseup', document, to)
    }

    it('resizes only the dragged column, without sorting', async () => {
      await render(Host, { props: { stateKey: 'people' } })
      // City, the rest column, has room to give.
      header('city.name', 600, 300)
      const th = header('hours', 300, 100)
      drag(th, 297, 347)
      await click(th)
      expect(th.style.width).toBe('150px')
      expect(JSON.parse(localStorage.getItem('people:columns')!).widths).toEqual({ hours: 150 })
      expect(names()).toEqual(['Bravo', 'Alpha', 'Charlie 10', 'Charlie 9'])
      th.dispatchEvent(new MouseEvent('dblclick', { bubbles: true, clientX: 299 }))
      await click(document.body)
      expect(JSON.parse(localStorage.getItem('people:columns')!).widths).toEqual({})
    })

    const saved = () =>
      JSON.parse(localStorage.getItem('people:columns') ?? 'null') as {
        widths: Record<string, number>
      } | null

    // Name is the rest column here, at least 12rem (192px).
    it('with the rest column on the left, resizes the column right of the edge', async () => {
      await render(Host, { props: { stateKey: 'people', textName: true } })
      header('name', 400, 400)
      header('city.name', 500, 200)
      drag(header('hours', 300, 100), 298, 268)
      await click(document.body)
      // City grows, Hours keeps its width and moves left with the edge, Name gives way.
      expect(saved()!.widths).toEqual({ 'city.name': 230 })
    })

    it('stops where the rest column reaches its least width', async () => {
      await render(Host, { props: { stateKey: 'people', textName: true } })
      header('name', 202, 202)
      header('city.name', 500, 200)
      drag(header('hours', 300, 100), 298, 268)
      await click(document.body)
      // Name had 10px to spare.
      expect(saved()!.widths).toEqual({ 'city.name': 210 })
    })

    it('stops where the changed column reaches 48px', async () => {
      await render(Host, { props: { stateKey: 'people', textName: true } })
      header('name', 400, 400)
      header('city.name', 500, 200)
      drag(header('hours', 300, 100), 298, 498)
      await click(document.body)
      expect(saved()!.widths).toEqual({ 'city.name': 48 })
    })

    it('with the rest column right of the edge, stops at its least width too', async () => {
      await render(Host, { props: { stateKey: 'people' } })
      // City is the rest column here (8rem, 128px).
      header('city.name', 500, 150)
      drag(header('hours', 300, 100), 298, 398)
      await click(document.body)
      expect(saved()!.widths).toEqual({ hours: 122 })
    })

    it('stores nothing for a drag that cannot move', async () => {
      await render(Host, { props: { stateKey: 'people', textName: true } })
      header('name', 192, 192)
      header('city.name', 500, 200)
      drag(header('hours', 300, 100), 298, 268)
      await click(document.body)
      expect(saved()).toBeNull()
    })

    it("has no handle on the last column's right edge", async () => {
      await render(Host, { props: { stateKey: 'people' } })
      drag(header('city.name', 500, 200), 498, 400)
      await click(document.body)
      expect(saved()).toBeNull()
    })
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

    it('pages with the compact paginator', async () => {
      await render(Host, { viewport: 'mobile', props: { pageSize: 2 } })
      expect(screen.root.querySelectorAll('dl')).toHaveLength(2)
      await click(screen.button(/^Nächste Seite$|^Next Page$/))
      expect(screen.text()).toContain('Charlie 10')
    })
  })
})
