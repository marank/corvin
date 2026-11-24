import { describe, expect, it, vi } from 'vitest'
import type { Invoice } from '../api'
import InvoiceDetailView from '../views/invoices/InvoiceDetailView.vue'
import { mockApi, page, reply } from './helpers/api'
import {
  answerConfirm,
  choose,
  click,
  confirmText,
  dialog,
  isDialogOpen,
  screen,
  toasts,
  type,
} from './helpers/dom'
import { bankAccount, contact, customer, invoice, lineItem, payment } from './helpers/fixtures'
import { render, t } from './helpers/render'

/** Opens the detail page of `inv`; the backend returns `state.invoice` on every reload. */
async function open(inv: Invoice = invoice()) {
  const state = { invoice: inv }
  const api = mockApi()
  api.get('/invoices/inv-1/', () => state.invoice)
  api.get(
    '/bank-accounts/',
    page([bankAccount(), bankAccount({ id: 'bank-2', name: 'Zweitkonto' })]),
  )
  api.get('/attachments/content_types/', { invoice: 7 })
  api.get('/attachments/', page([]))
  const view = await render(InvoiceDetailView, { path: '/invoices/:id', url: '/invoices/inv-1' })
  return { api, state, ...view }
}

const issued = (over: Partial<Invoice> = {}) =>
  invoice({ status: 'issued', number: 'RE-2026-001', ...over })

describe('InvoiceDetailView', () => {
  describe('a draft', () => {
    it('shows its lines and totals', async () => {
      await open()
      expect(screen.text()).toContain('RE-2026-001')
      expect(screen.text()).toContain(t('invoices.status.draft'))
      expect(screen.rows()[0]).toEqual(['1', 'Consulting', '2', '100,00 €', '200,00 €', ''])
      expect(screen.text()).toContain(`${t('invoices.subtotal')}200,00 €`)
      expect(screen.text()).toContain(`${t('invoices.vat')}38,00 €`)
      expect(screen.text()).toContain(`${t('common.total')}238,00 €`)
    })

    it('warns when the invoice would go out without an IBAN', async () => {
      await open(invoice({ bank_account: null }))
      expect(screen.text()).toContain(t('invoices.noIbanHint'))
      expect(screen.button(t('invoices.noIbanLink')).getAttribute('href')).toBe(
        '/settings?tab=bankAccounts',
      )
    })

    it('finalizes only after confirmation', async () => {
      const { api, state } = await open()
      api.post('/invoices/inv-1/finalize/', () => {
        state.invoice = issued()
        return state.invoice
      })

      await click(screen.button(t('invoices.finalize')))
      expect(confirmText()).toContain(t('invoices.finalizeConfirm'))
      await answerConfirm(t('common.cancel'))
      expect(api.requests('POST', '/invoices/inv-1/finalize/')).toHaveLength(0)

      await click(screen.button(t('invoices.finalize')))
      await answerConfirm(t('invoices.finalize'))
      expect(api.requests('POST', '/invoices/inv-1/finalize/')).toHaveLength(1)
      expect(screen.text()).toContain(t('invoices.status.issued'))
      expect(screen.hasButton(t('invoices.finalize'))).toBe(false)
    })

    it('shows why finalizing was refused and stays a draft', async () => {
      const { api } = await open()
      api.post('/invoices/inv-1/finalize/', reply(400, { detail: 'No hourly rate.' }))
      await click(screen.button(t('invoices.finalize')))
      await answerConfirm(t('invoices.finalize'))
      expect(toasts().join()).toContain('No hourly rate.')
      expect(screen.text()).toContain(t('invoices.status.draft'))
    })

    it('edits a line item', async () => {
      const { api, state } = await open()
      api.patch('/invoice-items/item-1/', (call) => {
        state.invoice = invoice({
          items: [lineItem({ quantity: 3, total: 300 })],
          subtotal: 300,
          total: 357,
        })
        return call.body
      })

      await click(screen.row('Consulting'))
      const modal = dialog(t('invoices.editLine'))
      expect(modal.input(t('time.description')).value).toBe('Consulting')
      await type(modal.input(t('invoices.quantity')), '3')
      await click(modal.button(t('common.save')))

      expect(api.lastBody('PATCH', '/invoice-items/item-1/')).toEqual({
        description: 'Consulting',
        quantity: 3,
        unit: 'hours',
        unit_price: 100,
      })
      expect(isDialogOpen(t('invoices.editLine'))).toBe(false)
      expect(screen.text()).toContain(`${t('common.total')}357,00 €`)
    })

    it('adds a line item to this invoice', async () => {
      const { api } = await open()
      api.post('/invoice-items/', (call) => call.body)
      await click(screen.button(t('invoices.addLine')))
      const modal = dialog(t('invoices.addLine'))
      await type(modal.input(t('time.description')), 'Travel')
      await type(modal.input(t('invoices.unitPrice')), '45')
      await click(modal.button(t('common.save')))
      expect(api.lastBody('POST', '/invoice-items/')).toEqual({
        description: 'Travel',
        quantity: 1,
        unit: 'flat',
        unit_price: 45,
        invoice: 'inv-1',
      })
    })

    it('keeps the line dialog open with the field error when the API refuses', async () => {
      const { api } = await open()
      api.post('/invoice-items/', reply(400, { description: ['This field may not be blank.'] }))
      await click(screen.button(t('invoices.addLine')))
      await click(dialog(t('invoices.addLine')).button(t('common.save')))
      const modal = dialog(t('invoices.addLine'))
      expect(modal.fieldError(t('time.description'))).toBe('This field may not be blank.')
    })

    it('deletes a line item after confirmation', async () => {
      const { api } = await open()
      api.delete('/invoice-items/item-1/')
      await click(screen.row('Consulting').querySelector('button')!)
      await answerConfirm(t('common.delete'))
      expect(api.requests('DELETE', '/invoice-items/item-1/')).toHaveLength(1)
      expect(toasts()).toContain(t('common.deleted'))
    })

    it('edits the header, including the e-invoice format and contacts', async () => {
      const { api } = await open()
      api.get('/contacts/', page([contact()]))
      api.patch('/invoices/inv-1/', (call) => call.body)
      await click(screen.button(t('common.edit')))
      const modal = dialog(t('invoices.editInvoice'))
      expect(modal.input(t('invoices.issueDate')).value).toBe('20.11.2026')
      await choose(modal.field(t('invoices.eInvoice')), t('invoices.eInvoiceFormats.xrechnung'))
      await choose(modal.field(t('invoices.contacts')), 'Erika Muster')
      await type(modal.input(t('invoices.dueDate')), '15.12.26')
      expect(modal.input(t('common.number')).value).toBe('RE-2026-001')
      await type(modal.input(t('common.number')), 'RE-2026-007')
      await click(modal.button(t('common.save')))

      expect(api.requests('GET', '/contacts/')[0]!.query.get('customer')).toBe('cus-1')
      expect(api.lastBody('PATCH', '/invoices/inv-1/')).toEqual({
        number: 'RE-2026-007',
        issue_date: '2026-11-20',
        due_date: '2026-12-15',
        vat_rate: 19,
        notes: '',
        e_invoice_format: 'xrechnung',
        contact_ids: ['con-1'],
      })
      expect(toasts()).toContain(t('common.saved'))
    })

    it('overrides the bank account', async () => {
      const { api } = await open()
      api.put('/invoices/inv-1/', (call) => call.body)
      await choose(screen.select(t('settings.bankAccount')), 'Zweitkonto')
      expect(api.lastBody('PUT', '/invoices/inv-1/')).toMatchObject({
        id: 'inv-1',
        bank_account_override: 'bank-2',
      })
    })

    it('is deleted after confirmation and leaves for the list', async () => {
      const { api, router } = await open()
      api.delete('/invoices/inv-1/')
      await click(screen.button(t('common.delete')))
      await answerConfirm(t('common.delete'))
      expect(api.requests('DELETE', '/invoices/inv-1/')).toHaveLength(1)
      expect(router.currentRoute.value.path).toBe('/invoices')
    })

    it('says so when the delete is refused', async () => {
      const { api, router } = await open()
      api.delete('/invoices/inv-1/', reply(409, { detail: 'Invoice is referenced.' }))
      await click(screen.button(t('common.delete')))
      await answerConfirm(t('common.delete'))
      expect(toasts().join()).toContain('Invoice is referenced.')
      expect(router.currentRoute.value.path).toBe('/invoices/inv-1')
    })
  })

  describe('an issued invoice', () => {
    it('is read-only: no finalize, no line editing, no header edit', async () => {
      await open(issued())
      expect(screen.hasButton(t('invoices.finalize'))).toBe(false)
      expect(screen.hasButton(t('invoices.addLine'))).toBe(false)
      expect(screen.hasButton(t('common.edit'))).toBe(false)
      await click(screen.row('Consulting'))
      expect(isDialogOpen(t('invoices.editLine'))).toBe(false)
      expect(screen.text()).toContain(`${t('settings.bankAccount')}Hausbank`)
    })

    it('links the PDF, and the XML only for XRechnung', async () => {
      await open(issued())
      expect(screen.button(t('invoices.downloadPdf')).getAttribute('href')).toBe(
        '/api/v1/invoices/inv-1/pdf/',
      )
      expect(screen.hasButton(t('invoices.downloadXml'))).toBe(false)
    })

    it('offers the XRechnung XML', async () => {
      await open(issued({ e_invoice_format: 'xrechnung' }))
      expect(screen.button(t('invoices.downloadXml')).getAttribute('href')).toBe(
        '/api/v1/invoices/inv-1/xrechnung/',
      )
    })

    it('records a partial payment, prefilled with the open amount', async () => {
      const { api, state } = await open(issued())
      api.post('/payments/', (call) => {
        state.invoice = issued({
          amount_paid: 100,
          remaining: 138,
          partially_paid: true,
          payments: [payment({ amount: 100 })],
        })
        return call.body
      })

      await click(screen.button(t('invoices.addPayment')))
      const modal = dialog(t('invoices.addPayment'))
      expect(modal.input(t('common.amount')).value).toContain('238.00')
      expect(modal.input(t('common.date')).value).toBe('23.11.2026')
      await type(modal.input(t('common.amount')), '100')
      await type(modal.input(t('common.notes')), 'Anzahlung')
      await click(modal.button(t('common.save')))

      expect(api.lastBody('POST', '/payments/')).toEqual({
        date: '2026-11-23',
        amount: 100,
        note: 'Anzahlung',
        invoice: 'inv-1',
      })
      expect(toasts()).toContain(t('invoices.paymentAdded'))
      expect(screen.text()).toContain(t('invoices.status.partially_paid'))
      expect(screen.text()).toContain(`${t('invoices.paid')}100,00 €`)
      expect(screen.text()).toContain(`${t('invoices.remaining')}138,00 €`)
      // With a payment on it, the invoice can no longer be cancelled.
      expect(screen.hasButton(t('invoices.cancelInvoice'))).toBe(false)
    })

    it('dates a payment shortly after midnight on the local day', async () => {
      vi.setSystemTime(new Date(2026, 10, 23, 0, 30))
      await open(issued())
      await click(screen.button(t('invoices.addPayment')))
      expect(dialog(t('invoices.addPayment')).input(t('common.date')).value).toBe('23.11.2026')
    })

    it('enters the payment in the invoice currency', async () => {
      await open(issued({ currency: 'USD' }))
      await click(screen.button(t('invoices.addPayment')))
      expect(dialog(t('invoices.addPayment')).input(t('common.amount')).value).toContain('$')
    })

    it('sends the e-mail to the invoice contact with the template text', async () => {
      const { api } = await open(issued({ contacts: [contact()] }))
      api.get('/invoices/inv-1/email_draft/', { subject: 'Rechnung RE-2026-001', body: 'Hallo' })
      api.post('/invoices/inv-1/send_email/', issued({ status: 'sent' }))

      await click(screen.button(t('invoices.sendEmail')))
      const modal = dialog(t('invoices.sendEmail'))
      expect(modal.input(t('common.email')).value).toBe('erika@acme.example')
      expect(modal.input(t('designer.mailSubject')).value).toBe('Rechnung RE-2026-001')
      await click(modal.button(t('common.send')))

      expect(api.lastBody('POST', '/invoices/inv-1/send_email/')).toEqual({
        to: 'erika@acme.example',
        subject: 'Rechnung RE-2026-001',
        body: 'Hallo',
      })
      expect(toasts()).toContain(t('invoices.emailQueued'))
    })

    it("falls back to the customer's address without invoice contacts", async () => {
      const { api } = await open(issued())
      api.get('/customers/cus-1/', customer())
      api.get('/invoices/inv-1/email_draft/', reply(500))
      await click(screen.button(t('invoices.sendEmail')))
      const modal = dialog(t('invoices.sendEmail'))
      expect(modal.input(t('common.email')).value).toBe('billing@acme.example')
      expect(modal.input(t('designer.mailSubject')).value).toBe('')
    })

    it('marks as sent', async () => {
      const { api } = await open(issued())
      api.post('/invoices/inv-1/mark_sent/', issued({ status: 'sent' }))
      await click(screen.button(t('invoices.markSent')))
      expect(api.requests('POST', '/invoices/inv-1/mark_sent/')).toHaveLength(1)
    })

    it('is cancelled only after confirmation', async () => {
      const { api, state } = await open(issued())
      api.post('/invoices/inv-1/cancel/', () => {
        state.invoice = issued({ status: 'cancelled' })
        return state.invoice
      })
      await click(screen.button(t('invoices.cancelInvoice')))
      expect(confirmText()).toContain(t('invoices.cancelConfirm'))
      await answerConfirm(t('invoices.cancelInvoice'))
      expect(api.requests('POST', '/invoices/inv-1/cancel/')).toHaveLength(1)
      expect(screen.text()).toContain(t('invoices.status.cancelled'))
      expect(screen.hasButton(t('invoices.addPayment'))).toBe(false)
    })

    it('deletes a payment', async () => {
      const { api } = await open(
        issued({ amount_paid: 50, remaining: 188, payments: [payment({ note: 'Bar' })] }),
      )
      api.delete('/payments/pay-1/')
      await click(screen.row('Bar').querySelector('button')!)
      await answerConfirm(t('common.delete'))
      expect(api.requests('DELETE', '/payments/pay-1/')).toHaveLength(1)
    })
  })

  it('shows a paid invoice without payment or cancel actions', async () => {
    await open(issued({ status: 'paid', amount_paid: 238, remaining: 0 }))
    expect(screen.text()).toContain(t('invoices.status.paid'))
    expect(screen.hasButton(t('invoices.addPayment'))).toBe(false)
    expect(screen.hasButton(t('invoices.cancelInvoice'))).toBe(false)
    expect(screen.hasButton(t('invoices.sendEmail'))).toBe(false)
  })

  it('offers the way back when the invoice cannot be loaded', async () => {
    const api = mockApi()
    api.get('/invoices/inv-1/', reply(404, { detail: 'Not found.' }))
    api.get('/bank-accounts/', page([]))
    await render(InvoiceDetailView, { path: '/invoices/:id', url: '/invoices/inv-1' })
    expect(screen.text()).toContain(t('common.loadFailed'))
    expect(screen.button(t('nav.invoices')).closest('a')?.getAttribute('href')).toBe('/invoices')
  })
})
