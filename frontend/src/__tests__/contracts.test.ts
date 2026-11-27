import { describe, expect, it } from 'vitest'
import ContractListView from '../views/contracts/ContractListView.vue'
import ContractDetailView from '../views/contracts/ContractDetailView.vue'
import type { ContractUsage, SupportContract } from '../api'
import { mockApi, page, reply } from './helpers/api'
import { pickers } from './helpers/backend'
import {
  answerConfirm,
  choose,
  click,
  confirmText,
  dialog,
  isDialogOpen,
  screen,
  toasts,
  toggleCheckbox,
  type,
} from './helpers/dom'
import { contract, customer, invoice, timeEntry } from './helpers/fixtures'
import { render, t } from './helpers/render'

describe('ContractListView', () => {
  function backend() {
    const api = pickers(mockApi())
    api.get(
      '/support-contracts/',
      page([
        contract(),
        contract({ id: 'ctr-2', name: 'Hosting', active: false, period: 'yearly' }),
      ]),
    )
    api.get('/customers/cus-1/', customer())
    return api
  }
  const lastQuery = (api: ReturnType<typeof backend>) =>
    Object.fromEntries(api.requests('GET', '/support-contracts/').at(-1)!.query)

  it('lists contracts with period, hours, price and next billing', async () => {
    const api = backend()
    await render(ContractListView, { path: '/contracts' })
    expect(lastQuery(api).ordering).toBe('number')
    expect(screen.rows()[0]).toEqual([
      'V-001',
      'Wartung',
      'Acme GmbH',
      t('contracts.periods.monthly'),
      '10:00 h',
      '500,00 €',
      '01.12.2026',
      t('common.active'),
      '',
    ])
    expect(screen.row('Hosting').textContent).toContain(t('common.inactive'))
  })

  it('filters by customer from the URL, period and status', async () => {
    const api = backend()
    await render(ContractListView, { path: '/contracts', url: '/contracts?customer=cus-1' })
    expect(lastQuery(api).customer).toBe('cus-1')
    await click(screen.button(/^Filter/))
    await choose(screen.field(t('contracts.period')), t('contracts.periods.quarterly'))
    await choose(screen.field(t('common.status')), t('common.inactive'))
    expect(lastQuery(api)).toMatchObject({
      customer: 'cus-1',
      period: 'quarterly',
      active: 'false',
    })
  })

  it('creates a contract, with an overage rate only when overage is billed', async () => {
    const api = backend()
    api.post('/support-contracts/', (call) => contract(call.body as Partial<SupportContract>))
    await render(ContractListView, { path: '/contracts' })
    await click(screen.button(t('contracts.new')))
    const modal = dialog(t('contracts.new'))
    expect(modal.input(t('contracts.startDate')).value).toBe('23.11.2026')
    expect(() => modal.field(t('contracts.overageRate'))).toThrow()

    await type(modal.input(t('common.name')), 'Premium')
    await choose(modal.field(t('projects.customer')), 'Acme GmbH')
    await type(modal.input(t('contracts.fixedPrice')), '750')
    await toggleCheckbox(modal.checkbox(t('contracts.billOverage')))
    await type(dialog(t('contracts.new')).input(t('contracts.overageRate')), '95')
    await click(modal.button(t('common.save')))

    expect(api.lastBody('POST', '/support-contracts/')).toEqual({
      name: 'Premium',
      customer: 'cus-1',
      period: 'monthly',
      included_hours: 10,
      fixed_price: 750,
      bill_overage: true,
      overage_rate: 95,
      active: true,
      travel_included: false,
      start_date: '2026-11-23',
      next_billing_date: '2026-11-23',
    })
    expect(isDialogOpen(t('contracts.new'))).toBe(false)
    expect(toasts()).toContain(t('common.created'))
  })

  it('shows the API errors on the contract fields', async () => {
    const api = backend()
    api.post(
      '/support-contracts/',
      reply(400, { name: ['Required.'], next_billing_date: ['Before the start.'] }),
    )
    await render(ContractListView, { path: '/contracts' })
    await click(screen.button(t('contracts.new')))
    await click(dialog(t('contracts.new')).button(t('common.save')))
    const modal = dialog(t('contracts.new'))
    expect(modal.fieldError(t('common.name'))).toBe('Required.')
    expect(modal.fieldError(t('contracts.nextBilling'))).toBe('Before the start.')
  })

  it('opens a contract', async () => {
    backend()
    const { router } = await render(ContractListView, { path: '/contracts' })
    await click(screen.row('Hosting'))
    expect(router.currentRoute.value.path).toBe('/contracts/ctr-2')
  })
})

describe('ContractDetailView', () => {
  const usage = (over: Partial<ContractUsage> = {}): ContractUsage => ({
    period_start: '2026-11-01',
    period_end: '2026-11-30',
    used_hours: 12.5,
    included_hours: 10,
    overage_hours: 2.5,
    ...over,
  })

  function backend(u = usage()) {
    const api = pickers(mockApi())
    api.get('/support-contracts/ctr-1/', contract())
    api.get('/support-contracts/ctr-1/usage/', u)
    api.get('/time-tracking/', page([timeEntry({ description: 'Patchday' })]))
    api.get('/invoices/', page([invoice({ id: 'inv-7', number: 'RE-7' })]))
    return api
  }
  const open = () => render(ContractDetailView, { path: '/contracts/:id', url: '/contracts/ctr-1' })

  it('shows the usage of this period, with the overage', async () => {
    const api = backend()
    await open()
    const text = screen.text()
    expect(text).toContain('V-001 · Acme GmbH')
    expect(text).toContain(`${t('contracts.usage')} (01.11.2026 – 30.11.2026)`)
    expect(text).toContain(`${t('contracts.used')}: 12:30 h`)
    expect(text).toContain(`${t('contracts.overage')}: 2:30 h`)
    expect(screen.root.querySelector('[role="progressbar"]')!.getAttribute('aria-valuenow')).toBe(
      '100',
    )
    expect(text).toContain('01.01.2026 – ∞')
    expect(screen.row('Patchday')).toBeTruthy()
    expect(api.requests('GET', '/time-tracking/')[0]!.query.get('contract')).toBe('ctr-1')
  })

  it('shows no overage within the included hours', async () => {
    backend(usage({ used_hours: 4, overage_hours: 0 }))
    await open()
    expect(screen.text()).not.toContain(`${t('contracts.overage')}:`)
    expect(screen.root.querySelector('[role="progressbar"]')!.getAttribute('aria-valuenow')).toBe(
      '40',
    )
  })

  it('bills the current period after confirmation and opens the invoice', async () => {
    const api = backend()
    api.post('/support-contracts/ctr-1/run_now/', invoice({ id: 'inv-8' }))
    const { router } = await open()
    await click(screen.button(t('contracts.runNow')))
    expect(confirmText()).toContain(t('contracts.runNowConfirm'))
    await answerConfirm(t('common.cancel'))
    expect(api.requests('POST', '/support-contracts/ctr-1/run_now/')).toHaveLength(0)

    await click(screen.button(t('contracts.runNow')))
    await answerConfirm(t('contracts.runNow'))
    expect(toasts()).toContain(t('contracts.generatedInvoice'))
    expect(router.currentRoute.value.path).toBe('/invoices/inv-8')
  })

  it('says why billing failed', async () => {
    const api = backend()
    api.post('/support-contracts/ctr-1/run_now/', reply(400, { detail: 'Nothing to bill.' }))
    const { router } = await open()
    await click(screen.button(t('contracts.runNow')))
    await answerConfirm(t('contracts.runNow'))
    expect(toasts().join()).toContain('Nothing to bill.')
    expect(router.currentRoute.value.path).toBe('/contracts/ctr-1')
  })

  it('opens an invoice of the contract', async () => {
    backend()
    const { router } = await open()
    await click(screen.row('RE-7'))
    expect(router.currentRoute.value.path).toBe('/invoices/inv-7')
  })

  it('saves changed terms', async () => {
    const api = backend()
    api.put('/support-contracts/ctr-1/', (call) => call.body)
    await open()
    await click(screen.button(t('overview.masterData')))
    await type(screen.input(t('contracts.includedHours')), '15')
    await choose(screen.field(t('contracts.period')), t('contracts.periods.quarterly'))
    await click(screen.button(t('common.save')))
    expect(api.lastBody('PUT', '/support-contracts/ctr-1/')).toMatchObject({
      included_hours: 15,
      period: 'quarterly',
    })
    expect(toasts()).toContain(t('common.saved'))
  })

  it('deletes the contract', async () => {
    const api = backend()
    api.delete('/support-contracts/ctr-1/')
    const { router } = await open()
    await click(screen.button(t('common.delete')))
    await answerConfirm(t('common.delete'))
    expect(router.currentRoute.value.path).toBe('/contracts')
  })

  it('offers the way back when the contract is gone', async () => {
    const api = mockApi()
    api.get('/support-contracts/ctr-1/', reply(404, {}))
    await open()
    expect(screen.text()).toContain(t('common.loadFailed'))
  })
})
