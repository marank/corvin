import { describe, expect, it, vi } from 'vitest'
import CustomerListView from '../views/customers/CustomerListView.vue'
import CustomerDetailView from '../views/customers/CustomerDetailView.vue'
import type { Address, Customer } from '../api'
import { mockApi, page, reply } from './helpers/api'
import { noAttachments, overview } from './helpers/backend'
import {
  activeTab,
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
  typeOnly,
} from './helpers/dom'
import {
  bankAccount,
  contact,
  customer,
  invoice,
  project,
  rate,
  task,
  timeEntry,
} from './helpers/fixtures'
import { render, settle, t } from './helpers/render'
import { NOW } from './helpers/time'

const address = (over: Partial<Address> = {}): Address => ({
  id: 'adr-1',
  customer: 'cus-1',
  label: 'Büro',
  street: 'Hauptstr. 1',
  postal_code: '10115',
  city: 'Berlin',
  country: 'Deutschland',
  is_primary: true,
  is_invoice_address: true,
  is_delivery_address: false,
  ...over,
})

describe('CustomerListView', () => {
  function backend() {
    const api = mockApi()
    api.get(
      '/customers/',
      page([
        customer({ primary_address: address(), uninvoiced_hours: 2.5 }),
        customer({ id: 'cus-2', name: 'Beta AG', is_active: false }),
      ]),
    )
    return api
  }
  const lastQuery = (api: ReturnType<typeof backend>) =>
    Object.fromEntries(api.requests('GET', '/customers/').at(-1)!.query)

  it('lists customers by name with place, open hours and status', async () => {
    const api = backend()
    await render(CustomerListView, { path: '/customers' })
    expect(lastQuery(api)).toEqual({ page: '1', page_size: '50', ordering: 'name' })
    expect(screen.row('Acme GmbH').textContent).toContain('10115 Berlin')
    expect(screen.row('Acme GmbH').textContent).toContain('2:30 h')
    expect(screen.row('Beta AG').textContent).toContain(t('common.inactive'))
  })

  it('searches once the typing pauses', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setTimeout', 'clearTimeout'], now: NOW })
    const api = backend()
    await render(CustomerListView, { path: '/customers' })
    const search = screen.root.querySelector<HTMLInputElement>(
      `input[aria-label="${t('common.search')}"]`,
    )!
    await typeOnly(search, 'ac')
    await typeOnly(search, 'acme ')
    expect(lastQuery(api).search).toBeUndefined()
    await vi.advanceTimersByTimeAsync(300)
    await settle()
    expect(lastQuery(api)).toMatchObject({ search: 'acme', page: '1' })
  })

  it('filters inactive customers', async () => {
    const api = backend()
    await render(CustomerListView, { path: '/customers' })
    await click(screen.button(t('common.filter')))
    await choose(screen.field(t('common.status')), t('common.inactive'))
    expect(lastQuery(api).is_active).toBe('false')
  })

  it('creates a customer', async () => {
    const api = backend()
    api.post('/customers/', (call) => customer(call.body as Partial<Customer>))
    await render(CustomerListView, { path: '/customers' })
    await click(screen.button(t('customers.new')))
    const modal = dialog(t('customers.new'))
    await type(modal.input(t('common.name')), 'Gamma KG')
    await type(modal.input(t('customers.paymentTerms')), '14')
    await click(modal.button(t('common.save')))
    expect(api.lastBody('POST', '/customers/')).toMatchObject({
      name: 'Gamma KG',
      payment_terms_days: 14,
    })
    expect(toasts()).toContain(t('common.created'))
    expect(isDialogOpen(t('customers.new'))).toBe(false)
  })

  it('shows a missing name on the name field', async () => {
    const api = backend()
    api.post('/customers/', reply(400, { name: ['This field may not be blank.'] }))
    await render(CustomerListView, { path: '/customers' })
    await click(screen.button(t('customers.new')))
    await click(dialog(t('customers.new')).button(t('common.save')))
    expect(dialog(t('customers.new')).fieldError(t('common.name'))).toBe(
      'This field may not be blank.',
    )
    // Inline errors need no extra text in the toast.
    expect(toasts()).toEqual([t('common.checkInput')])
  })

  it('asks before throwing away a half-filled new customer', async () => {
    backend()
    await render(CustomerListView, { path: '/customers' })
    await click(screen.button(t('customers.new')))
    await type(dialog(t('customers.new')).input(t('common.name')), 'Gamma')
    await click(dialog(t('customers.new')).button(t('common.cancel')))
    expect(confirmText()).toContain(t('common.unsavedMessage'))
    await answerConfirm(t('common.keepEditing'))
    expect(isDialogOpen(t('customers.new'))).toBe(true)
    await click(dialog(t('customers.new')).button(t('common.cancel')))
    await answerConfirm(t('common.discard'))
    expect(isDialogOpen(t('customers.new'))).toBe(false)
  })

  it('reports a customer the backend refuses to delete', async () => {
    const api = backend()
    api.delete('/customers/cus-1/', reply(409, { detail: 'Customer has invoices.' }))
    await render(CustomerListView, { path: '/customers' })
    await click(screen.row('Acme GmbH').querySelector('button')!)
    await answerConfirm(t('common.delete'))
    expect(toasts()).toEqual([`${t('common.error')}Customer has invoices.`])
  })

  it('opens a customer', async () => {
    backend()
    const { router } = await render(CustomerListView, { path: '/customers' })
    await click(screen.row('Beta AG'))
    expect(router.currentRoute.value.path).toBe('/customers/cus-2')
  })

  it('shows name and place on phone cards', async () => {
    backend()
    await render(CustomerListView, { path: '/customers', viewport: 'mobile' })
    expect(screen.text()).toContain('Acme GmbH10115 Berlin')
  })
})

describe('CustomerDetailView', () => {
  function backend(c: Customer = customer({ number: 'K-001', primary_address: address() })) {
    const api = mockApi()
    const state = { customer: c, addresses: [address()] }
    api.get('/customers/cus-1/', () => state.customer)
    api.get('/contacts/', page([contact()]))
    api.get('/addresses/', () => page(state.addresses))
    api.get(
      '/bank-accounts/',
      page([bankAccount(), bankAccount({ id: 'b-old', is_active: false })]),
    )
    api.get('/hourly-rates/', (call) =>
      page(call.query.has('customer') ? [rate({ customer: 'cus-1', amount: 110 })] : [rate()]),
    )
    overview(api, {
      uninvoiced: 150,
      entries: [timeEntry()],
      invoices: [
        invoice({ id: 'i1', number: 'RE-1', status: 'issued', remaining: 238 }),
        invoice({ id: 'i2', number: 'RE-2', status: 'sent', remaining: 100, partially_paid: true }),
        invoice({ id: 'i3', number: 'RE-3', status: 'paid', remaining: 0 }),
      ],
      tasks: [task(), task({ id: 't2', title: 'Erledigt', status: 'done' })],
      projects: [project(), project({ id: 'p2', name: 'Alt', status: 'done' })],
    })
    noAttachments(api)
    return { api, state }
  }
  const open = () => render(CustomerDetailView, { path: '/customers/:id', url: '/customers/cus-1' })
  const openTab = (name: string) => click(screen.button(name))

  it('gives an overview of open work and money', async () => {
    const { api } = backend()
    await open()
    expect(screen.text()).toContain('Acme GmbH')
    expect(screen.text()).toContain('K-001 · 10115 Berlin')
    const text = screen.text()
    expect(text).toContain(`${t('overview.uninvoiced')}2:30 h`)
    expect(text).toContain(`${t('overview.openInvoices')}338,00 € · 2`)
    expect(text).toContain(`${t('overview.openTasks')}1`)
    expect(text).toContain(`${t('overview.activeProjects')}1`)
    const uninvoiced = api
      .requests('GET', '/time-tracking/summary/')
      .find((c) => c.query.has('invoice__isnull'))!
    expect(Object.fromEntries(uninvoiced.query)).toEqual({
      customer: 'cus-1',
      billable: 'true',
      invoice__isnull: 'true',
      contract__isnull: 'true',
      end_datetime__isnull: 'false',
    })
    expect(screen.button(t('overview.showAll')).getAttribute('href')).toBe(
      '/projects?customer=cus-1',
    )
  })

  it('starts an invoice for this customer', async () => {
    backend()
    const { router } = await open()
    await click(screen.button(t('overview.createInvoice')))
    expect(router.currentRoute.value.fullPath).toBe('/invoices/new?customer=cus-1')
  })

  it('saves the master data', async () => {
    const { api } = backend()
    api.put('/customers/cus-1/', (call) => call.body)
    await open()
    await openTab(t('overview.masterData'))
    await type(screen.input(t('customers.vatId')), 'DE123456789')
    await choose(screen.field(t('settings.bankAccount')), 'Hausbank')
    await toggleCheckbox(screen.checkbox(t('customers.active')))
    await click(screen.button(t('common.save')))
    expect(api.lastBody('PUT', '/customers/cus-1/')).toMatchObject({
      name: 'Acme GmbH',
      vat_id: 'DE123456789',
      bank_account: 'bank-1',
      is_active: false,
    })
    expect(toasts()).toContain(t('common.saved'))
  })

  it('corrects the number', async () => {
    const { api } = backend()
    api.put('/customers/cus-1/', (call) => call.body)
    await open()
    await openTab(t('overview.masterData'))
    await type(screen.input(t('common.number')), 'K-1000')
    await click(screen.button(t('common.save')))
    expect(api.lastBody('PUT', '/customers/cus-1/')).toMatchObject({ number: 'K-1000' })
  })

  it('locks the number once a finalized invoice shows it', async () => {
    backend(customer({ number_locked: true }))
    await open()
    await openTab(t('overview.masterData'))
    expect(screen.input(t('common.number')).disabled).toBe(true)
    expect(screen.field(t('common.number')).textContent).toContain(t('common.numberLocked'))
  })

  it('offers only active bank accounts', async () => {
    backend()
    await open()
    await openTab(t('overview.masterData'))
    await click(screen.field(t('settings.bankAccount')).querySelector('.p-select')!)
    expect([...document.querySelectorAll('[role="option"]')].map((o) => o.textContent)).toEqual([
      'Hausbank',
    ])
  })

  it('shows the API error on the master data field', async () => {
    const { api } = backend()
    api.put('/customers/cus-1/', reply(400, { vat_id: ['Invalid VAT ID.'] }))
    await open()
    await openTab(t('overview.masterData'))
    await click(screen.button(t('common.save')))
    expect(screen.fieldError(t('customers.vatId'))).toBe('Invalid VAT ID.')
  })

  it('asks before leaving with unsaved master data', async () => {
    backend()
    const { router } = await open()
    await openTab(t('overview.masterData'))
    await type(screen.input(t('common.name')), 'Acme AG')
    await click(screen.button(t('nav.customers')))
    expect(confirmText()).toContain(t('common.unsavedMessage'))
    await answerConfirm(t('common.keepEditing'))
    expect(router.currentRoute.value.path).toBe('/customers/cus-1')
  })

  it('adds an invoice contact', async () => {
    const { api } = backend()
    api.post('/contacts/', (call) => call.body)
    await open()
    await openTab(t('customers.contacts'))
    expect(screen.row('Erika').textContent).toContain('erika@acme.example')
    await click(screen.button(t('customers.newContact')))
    const modal = dialog(t('customers.newContact'))
    await type(modal.input(t('customers.firstName')), 'Max')
    await type(modal.input(t('common.email')), 'max@acme.example')
    await toggleCheckbox(modal.checkbox(t('customers.invoiceContact')))
    await click(modal.button(t('common.save')))
    expect(api.lastBody('POST', '/contacts/')).toEqual({
      first_name: 'Max',
      email: 'max@acme.example',
      is_invoice_contact: true,
      customer: 'cus-1',
    })
  })

  it('edits and deletes a contact', async () => {
    const { api } = backend()
    api.put('/contacts/con-1/', (call) => call.body)
    api.delete('/contacts/con-1/')
    await open()
    await openTab(t('customers.contacts'))
    await click(screen.row('Erika'))
    const modal = dialog(t('customers.editContact'))
    await type(modal.input(t('customers.role')), 'CFO')
    await click(modal.button(t('common.save')))
    expect(api.lastBody('PUT', '/contacts/con-1/')).toMatchObject({ id: 'con-1', role: 'CFO' })

    await click(screen.row('Erika').querySelector(`[aria-label="${t('common.delete')}"]`)!)
    await answerConfirm(t('common.delete'))
    expect(api.requests('DELETE', '/contacts/con-1/')).toHaveLength(1)
  })

  it('adds an address without losing unsaved master data', async () => {
    const { api, state } = backend()
    api.post('/addresses/', (call) => {
      state.addresses = [...state.addresses, address({ id: 'adr-2', ...(call.body as object) })]
      return call.body
    })
    api.put('/customers/cus-1/', (call) => call.body)
    await open()
    await openTab(t('overview.masterData'))
    await type(screen.input(t('common.notes')), 'Call before visits')

    await openTab(t('customers.addresses'))
    await click(screen.button(t('customers.newAddress')))
    const modal = dialog(t('customers.newAddress'))
    expect(modal.input(t('customers.country')).value).toBe('Deutschland')
    await type(modal.input(t('customers.street')), 'Lager 5')
    await type(modal.input(t('customers.city')), 'Potsdam')
    await click(modal.button(t('common.save')))
    expect(api.lastBody('POST', '/addresses/')).toMatchObject({
      street: 'Lager 5',
      city: 'Potsdam',
      country: 'Deutschland',
      is_primary: false,
      customer: 'cus-1',
    })
    expect(screen.row('Lager 5')).toBeTruthy()

    await openTab(t('overview.masterData'))
    expect(screen.input(t('common.notes')).value).toBe('Call before visits')
    await click(screen.button(t('common.save')))
    expect(api.lastBody('PUT', '/customers/cus-1/')).toMatchObject({ notes: 'Call before visits' })
  })

  it('deletes an address', async () => {
    const { api, state } = backend()
    api.delete('/addresses/adr-1/', () => {
      state.addresses = []
      return reply(204)
    })
    await open()
    await openTab(t('customers.addresses'))
    await click(screen.row('Hauptstr. 1').querySelector(`[aria-label="${t('common.delete')}"]`)!)
    await answerConfirm(t('common.delete'))
    expect(screen.text()).toContain(t('common.empty'))
  })

  it("lists the customer's hourly rates next to the default", async () => {
    const { api } = backend()
    api.post('/hourly-rates/', (call) => call.body)
    await open()
    await openTab(t('customers.rates'))
    expect(screen.text()).toContain('95,00 €')
    expect(activeTab().rows()[0]).toEqual(['01.01.2026', '—', `110,00 €${t('rates.perHour')}`, ''])

    await click(screen.button(t('customers.newRate')))
    const modal = dialog(t('customers.newRate'))
    expect(modal.input(t('customers.validFrom')).value).toBe('23.11.2026')
    await type(modal.input(t('customers.hourlyRate')), '120')
    await click(modal.button(t('common.save')))
    expect(api.lastBody('POST', '/hourly-rates/')).toEqual({
      amount: 120,
      valid_from: '2026-11-23',
      valid_to: null,
      customer: 'cus-1',
    })
  })

  it('deletes the customer and returns to the list', async () => {
    const { api } = backend()
    api.delete('/customers/cus-1/')
    const { router } = await open()
    await click(screen.button(t('common.delete')))
    await answerConfirm(t('common.delete'))
    expect(api.requests('DELETE', '/customers/cus-1/')).toHaveLength(1)
    expect(router.currentRoute.value.path).toBe('/customers')
  })

  it('offers the way back when the customer is gone', async () => {
    const api = mockApi()
    api.get('/customers/cus-1/', reply(404, { detail: 'Not found.' }))
    await open()
    expect(screen.text()).toContain(t('common.loadFailed'))
  })
})
