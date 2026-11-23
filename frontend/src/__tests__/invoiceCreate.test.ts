import { beforeEach, describe, expect, it, vi } from 'vitest'
import InvoiceCreateView from '../views/invoices/InvoiceCreateView.vue'
import type { ConsolidateRequest } from '../api'
import { mockApi, page, reply, type ApiMock } from './helpers/api'
import {
  answerConfirm,
  choose,
  click,
  confirmText,
  screen,
  toasts,
  toggleCheckbox,
  type,
} from './helpers/dom'
import { bankAccount, contact, customer, invoice, project, timeEntry } from './helpers/fixtures'
import { render, settle, t } from './helpers/render'
import { NOW } from './helpers/time'

const entries = [
  timeEntry({ id: 'te-1', description: 'Homepage', duration_minutes: 120 }),
  timeEntry({
    id: 'te-2',
    description: 'Hosting',
    start_datetime: '2026-11-21T09:00:00+01:00',
    end_datetime: '2026-11-21T10:00:00+01:00',
    duration_minutes: 60,
  }),
]

const preview = {
  lines: [{ description: 'Homepage', quantity: 2, unit: 'hours', unit_price: 100, total: 200 }],
  entry_count: 1,
  subtotal: '200.00',
  vat_rate: '19.00',
  vat_amount: '38.00',
  total: '238.00',
}

function backend() {
  const api = mockApi()
  api.get('/customers/', page([customer(), customer({ id: 'cus-2', name: 'Beta AG' })]))
  api.get('/projects/', page([project()]))
  api.get(
    '/contacts/',
    page([contact(), contact({ id: 'con-2', name: 'Max Other', is_invoice_contact: false })]),
  )
  api.get('/bank-accounts/', page([bankAccount()]))
  api.get('/time-tracking/', page(entries))
  api.post('/invoices/consolidate_preview/', preview)
  return api
}

async function open(url = '/invoices/new?customer=cus-1') {
  return render(InvoiceCreateView, { path: '/invoices/new', url })
}

/** The preview request waits 300 ms for more changes. */
async function waitForPreview() {
  await vi.advanceTimersByTimeAsync(300)
  await settle()
}

const lastPreview = (api: ApiMock) =>
  api.lastBody('POST', '/invoices/consolidate_preview/') as ConsolidateRequest

describe('InvoiceCreateView', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date', 'setTimeout', 'clearTimeout'], now: NOW })
  })

  it('needs a customer before going on', async () => {
    const api = backend()
    await open('/invoices/new')
    expect(screen.button(t('common.next')).hasAttribute('disabled')).toBe(true)
    expect(api.requests('GET', '/time-tracking/')).toHaveLength(0)

    await choose(screen.field(t('projects.customer')), 'Beta AG')
    expect(screen.button(t('common.next')).hasAttribute('disabled')).toBe(false)
    expect(api.requests('GET', '/time-tracking/')[0]!.query.get('customer')).toBe('cus-2')
  })

  it('loads only billable, uninvoiced, finished entries outside contracts', async () => {
    const api = backend()
    await open('/invoices/new?customer=cus-1&project=prj-1')
    const query = api.requests('GET', '/time-tracking/').at(-1)!.query
    expect(Object.fromEntries(query)).toEqual({
      customer: 'cus-1',
      project: 'prj-1',
      billable: 'true',
      invoice__isnull: 'true',
      contract__isnull: 'true',
      end_datetime__isnull: 'false',
      ordering: 'start_datetime',
      page_size: '500',
    })
  })

  it('narrows the entries to the service period typed in', async () => {
    const api = backend()
    await open()
    await type(screen.input(t('invoices.dateFrom')), '1.11.')
    await type(screen.input(t('invoices.dateTo')), '301126')
    const query = api.requests('GET', '/time-tracking/').at(-1)!.query
    expect(query.get('start_datetime__date__gte')).toBe('2026-11-01')
    expect(query.get('start_datetime__date__lte')).toBe('2026-11-30')
  })

  it("preselects the customer's invoice contacts", async () => {
    const api = backend()
    await open()
    await click(screen.button(t('common.next')))
    await waitForPreview()
    expect(lastPreview(api).contact_ids).toEqual(['con-1'])
  })

  it('bills the ticked entries and shows the server-side subtotal', async () => {
    const api = backend()
    await open()
    await click(screen.button(t('common.next')))
    await waitForPreview()

    expect(screen.text()).toContain(t('invoices.selectedEntries', { selected: 2, total: 2 }))
    expect(screen.text()).toContain('3:00 h')
    expect(lastPreview(api).entry_ids).toEqual(['te-1', 'te-2'])
    expect(screen.text()).toContain(`${t('invoices.subtotal')}: 200,00 €`)

    await toggleCheckbox(screen.row('Hosting'))
    await waitForPreview()
    expect(screen.text()).toContain(t('invoices.selectedEntries', { selected: 1, total: 2 }))
    expect(screen.text()).toContain('2:00 h')
    expect(lastPreview(api).entry_ids).toEqual(['te-1'])

    // A click on the row toggles the entry as well.
    await click(screen.row('Hosting'))
    await waitForPreview()
    expect(lastPreview(api).entry_ids).toEqual(['te-1', 'te-2'])
  })

  it('cannot go on with nothing to bill', async () => {
    const api = backend()
    await open()
    await click(screen.button(t('common.next')))
    await waitForPreview()
    const previews = api.requests('POST', '/invoices/consolidate_preview/').length

    await toggleCheckbox(screen.root.querySelector('thead')!)
    await waitForPreview()
    expect(screen.text()).toContain(t('invoices.selectedEntries', { selected: 0, total: 2 }))
    expect(screen.button(t('common.next')).hasAttribute('disabled')).toBe(true)
    expect(api.requests('POST', '/invoices/consolidate_preview/')).toHaveLength(previews)
  })

  it('adds manual lines to the invoice', async () => {
    const api = backend()
    api.get('/time-tracking/', page([]))
    await open()
    await click(screen.button(t('common.next')))
    expect(screen.button(t('invoices.addLine')).hasAttribute('disabled')).toBe(true)

    await type(screen.input(t('time.description')), 'Domain')
    await type(screen.input(t('invoices.quantity')), '2')
    await type(screen.input(t('invoices.unitPrice')), '12.5')
    await click(screen.button(t('invoices.addLine')))
    await waitForPreview()

    expect(screen.row('Domain')).toBeTruthy()
    expect(screen.text()).toContain('25,00 €')
    expect(lastPreview(api).extra_lines).toEqual([
      expect.objectContaining({
        description: 'Domain',
        quantity: 2,
        unit: 'flat',
        unit_price: 12.5,
      }),
    ])
    // The form is empty again for the next line.
    expect(screen.input(t('time.description')).value).toBe('')
    expect(screen.button(t('common.next')).hasAttribute('disabled')).toBe(false)

    await click(screen.row('Domain').querySelector('button')!)
    expect(screen.text()).not.toContain('Domain')
    expect(screen.button(t('common.next')).hasAttribute('disabled')).toBe(true)
  })

  it('shows why the invoice could not be calculated and holds it back', async () => {
    const api = backend()
    api.post('/invoices/consolidate_preview/', reply(400, { detail: 'No hourly rate for Acme.' }))
    await open()
    await click(screen.button(t('common.next')))
    await waitForPreview()
    expect(screen.text()).toContain('No hourly rate for Acme.')
    expect(screen.button(t('common.next')).hasAttribute('disabled')).toBe(true)
  })

  it('creates the invoice with the chosen options and opens it', async () => {
    const api = backend()
    api.post('/invoices/consolidate/', invoice({ id: 'inv-9' }))
    const { router } = await open()
    await click(screen.button(t('common.next')))
    await waitForPreview()
    await click(screen.button(t('common.next')))

    expect(screen.text()).toContain(`${t('common.total')}238,00 €`)
    expect(screen.text()).not.toContain(t('invoices.noIbanHint'))
    await choose(screen.field(t('invoices.groupBy')), t('invoices.groupBys.day'))
    await choose(screen.field(t('invoices.eInvoice')), t('invoices.eInvoiceFormats.xrechnung'))
    await choose(screen.field(t('settings.bankAccount')), 'Hausbank')
    await click(screen.button(t('common.create')))

    expect(api.lastBody('POST', '/invoices/consolidate/')).toEqual({
      customer_id: 'cus-1',
      project_id: null,
      contact_ids: ['con-1'],
      bank_account_id: 'bank-1',
      date_from: null,
      date_to: null,
      entry_ids: ['te-1', 'te-2'],
      group_by: 'day',
      e_invoice_format: 'xrechnung',
      extra_lines: [],
    })
    expect(router.currentRoute.value.path).toBe('/invoices/inv-9')
    // Created: leaving needs no confirmation.
    expect(confirmText()).toBe('')
  })

  it('stays on the review step when creating fails', async () => {
    const api = backend()
    api.post('/invoices/consolidate/', reply(400, { detail: 'Customer has no address.' }))
    const { router } = await open()
    await click(screen.button(t('common.next')))
    await waitForPreview()
    await click(screen.button(t('common.next')))
    await click(screen.button(t('common.create')))
    expect(toasts().join()).toContain('Customer has no address.')
    expect(router.currentRoute.value.path).toBe('/invoices/new')
  })

  it('warns when no bank account has an IBAN', async () => {
    const api = backend()
    api.get('/bank-accounts/', page([bankAccount({ iban: '' })]))
    await open()
    await click(screen.button(t('common.next')))
    await waitForPreview()
    await click(screen.button(t('common.next')))
    expect(screen.text()).toContain(t('invoices.noIbanHint'))
  })

  it('asks before leaving a started invoice', async () => {
    backend()
    const { router } = await open()
    await click(screen.button(t('common.next')))
    await waitForPreview()

    await click(screen.button(t('nav.invoices')))
    expect(confirmText()).toContain(t('common.unsavedMessage'))
    await answerConfirm(t('common.keepEditing'))
    expect(router.currentRoute.value.path).toBe('/invoices/new')

    await click(screen.button(t('nav.invoices')))
    await answerConfirm(t('common.discard'))
    expect(router.currentRoute.value.path).toBe('/invoices')
  })

  it('leaves the first step without asking', async () => {
    backend()
    const { router } = await open()
    await click(screen.button(t('common.cancel')))
    expect(confirmText()).toBe('')
    expect(router.currentRoute.value.path).toBe('/invoices')
  })
})
