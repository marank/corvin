import { describe, expect, it } from 'vitest'
import InvoiceListView from '../views/invoices/InvoiceListView.vue'
import { mockApi, page, reply } from './helpers/api'
import {
  answerConfirm,
  choose,
  click,
  confirmText,
  screen,
  toasts,
  toggleCheckbox,
} from './helpers/dom'
import { customer, invoice } from './helpers/fixtures'
import { render, t } from './helpers/render'

const invoices = [
  invoice({ id: 'inv-1', number: '', status: 'draft' }),
  invoice({
    id: 'inv-2',
    number: 'RE-2026-002',
    status: 'issued',
    partially_paid: true,
    amount_paid: 100,
    remaining: 138,
  }),
  invoice({ id: 'inv-3', number: 'RE-2026-003', status: 'paid', remaining: 0 }),
]

function backend(results = invoices, count = results.length) {
  const api = mockApi()
  api.get('/invoices/', page(results, count))
  api.get('/customers/', page([customer()]))
  api.get('/customers/cus-1/', customer())
  api.get('/projects/', page([]))
  return api
}

const open = (url = '/invoices', viewport: 'desktop' | 'mobile' = 'desktop') =>
  render(InvoiceListView, { path: '/invoices', url, viewport })

const lastQuery = (api: ReturnType<typeof backend>) =>
  Object.fromEntries(api.requests('GET', '/invoices/').at(-1)!.query)

describe('InvoiceListView', () => {
  it('lists the newest invoices first, one page at a time', async () => {
    const api = backend()
    await open()
    expect(lastQuery(api)).toEqual({ page: '1', page_size: '50', ordering: '-issue_date' })
    expect(screen.rows().map((row) => row[0])).toEqual(['', 'RE-2026-002', 'RE-2026-003'])
  })

  it('shows the open amount and partial payments, but no amount open on drafts', async () => {
    backend()
    await open()
    const [draft, partial, paid] = screen.rows()
    expect(draft![5]).toBe('—')
    expect(partial![5]).toBe('138,00 €')
    expect(partial![6]).toBe(t('invoices.status.partially_paid'))
    expect(paid![6]).toBe(t('invoices.status.paid'))
  })

  it('opens an invoice on click', async () => {
    backend()
    const { router } = await open()
    await click(screen.row('RE-2026-002'))
    expect(router.currentRoute.value.path).toBe('/invoices/inv-2')
  })

  it('records external invoices from the ⋮ menu', async () => {
    backend()
    const { router } = await open()
    expect(screen.hasButton(t('invoices.importExternal'))).toBe(false)
    await click(screen.button(t('common.moreActions')))
    await click(screen.button(t('invoices.importExternal')))
    expect(router.currentRoute.value.path).toBe('/invoices/import')
  })

  it('takes the receivable filter from the dashboard link', async () => {
    const api = backend()
    await open('/invoices?receivable=overdue')
    expect(lastQuery(api).receivable).toBe('overdue')
    expect(screen.text()).toContain(
      `${t('invoices.receivable')}: ${t('invoices.receivables.overdue')}`,
    )
  })

  it('ignores an unknown receivable filter', async () => {
    const api = backend()
    await open('/invoices?receivable=everything')
    expect(lastQuery(api).receivable).toBeUndefined()
  })

  it('filters by customer from the URL and names it on the chip', async () => {
    const api = backend()
    await open('/invoices?customer=cus-1')
    expect(lastQuery(api).customer).toBe('cus-1')
    expect(screen.text()).toContain(`${t('projects.customer')}: Acme GmbH`)
  })

  it('filters by status and goes back to page one', async () => {
    const api = backend(invoices, 120)
    await open()
    await click(screen.button('Seite 2'))
    expect(lastQuery(api).page).toBe('2')

    await click(screen.button(t('common.filter')))
    await choose(screen.field(t('common.status')), t('invoices.status.paid'))
    expect(lastQuery(api)).toMatchObject({ status: 'paid', page: '1' })

    const chip = screen.root.querySelector('.p-chip')!
    expect(chip.textContent).toContain(t('invoices.status.paid'))
    await click(chip.querySelector('[data-pc-section="removeicon"]')!)
    expect(lastQuery(api).status).toBeUndefined()
  })

  it('clears all filters at once', async () => {
    const api = backend()
    await open('/invoices?customer=cus-1&receivable=open')
    await click(screen.button(new RegExp(`^${t('common.filter')}`)))
    await click(screen.button(t('common.clearFilters')))
    expect(lastQuery(api)).toEqual({ page: '1', page_size: '50', ordering: '-issue_date' })
  })

  it('sorts on the server when a column header is clicked', async () => {
    const api = backend()
    await open()
    await click(screen.root.querySelector('th[data-p-sortable-column="true"]')!)
    expect(lastQuery(api).ordering).toBe('number')
  })

  it('deletes drafts only, after confirmation', async () => {
    const api = backend()
    api.delete('/invoices/inv-1/')
    await open()
    expect(screen.row('RE-2026-002').querySelector('button')).toBeNull()

    const before = api.requests('GET', '/invoices/').length
    await click(screen.root.querySelector('tbody tr button')!)
    expect(confirmText()).toContain(t('common.deleteConfirm'))
    await answerConfirm(t('common.delete'))
    expect(api.requests('DELETE', '/invoices/inv-1/')).toHaveLength(1)
    expect(api.requests('GET', '/invoices/').length).toBe(before + 1)
  })

  it('deletes a selection one by one and reports the ones the backend refused', async () => {
    const api = backend()
    api.delete('/invoices/inv-1/')
    api.delete('/invoices/inv-3/', reply(409, { detail: 'Finalized.' }))
    await open()
    await click(screen.button(t('table.select')))
    await toggleCheckbox(screen.root.querySelectorAll('tbody tr')[0]!)
    await toggleCheckbox(screen.root.querySelectorAll('tbody tr')[2]!)
    expect(screen.text()).toContain(t('table.selected', { count: 2 }))

    await click(screen.button(t('table.deleteSelected', { count: 2 })))
    expect(confirmText()).toContain(t('table.bulkDeleteConfirm', { count: 2 }))
    await answerConfirm(t('common.delete'))
    expect(api.requests('DELETE', /^\/invoices\/inv-\d\/$/).map((c) => c.path)).toEqual([
      '/invoices/inv-1/',
      '/invoices/inv-3/',
    ])
    expect(toasts()).toEqual([
      t('table.bulkDeleted', { count: 1 }),
      t('table.bulkDeleteFailed', { count: 1 }),
    ])
    expect(screen.hasButton(t('table.select'))).toBe(true)
  })

  describe('on a phone', () => {
    it('shows cards with number, customer, total and status', async () => {
      backend()
      await open('/invoices', 'mobile')
      expect(screen.root.querySelector('table')).toBeNull()
      expect(screen.text()).toContain('RE-2026-002')
      expect(screen.text()).toContain(t('invoices.status.partially_paid'))
    })

    it('sorts with the sort select and the direction button', async () => {
      const api = backend()
      await open('/invoices', 'mobile')
      await choose(screen.select(t('table.sortBy')), t('common.total'))
      expect(lastQuery(api).ordering).toBe('-total')
      await click(screen.button(t('table.descending')))
      expect(lastQuery(api).ordering).toBe('total')
    })

    it('says when there are no invoices', async () => {
      backend([])
      await open('/invoices', 'mobile')
      expect(screen.text()).toContain(t('common.empty'))
    })
  })
})
