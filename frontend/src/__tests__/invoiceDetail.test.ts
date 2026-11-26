import { describe, expect, it, vi } from 'vitest'
import type { Invoice, TimeEntry } from '../api'
import InvoiceDetailView from '../views/invoices/InvoiceDetailView.vue'
import { mockApi, page, reply } from './helpers/api'
import {
  activeTab,
  answerConfirm,
  click,
  confirmText,
  dialog,
  screen,
  toasts,
  type,
} from './helpers/dom'
import { contact, customer, invoice, lineItem, payment, timeEntry } from './helpers/fixtures'
import { render, settle, t } from './helpers/render'

/** Opens the detail page of `inv`; the backend returns `state.invoice` on every reload. */
async function open(inv: Invoice = invoice(), entries: TimeEntry[] = []) {
  const state = { invoice: inv }
  const api = mockApi()
  api.get('/invoices/inv-1/time-entries/', entries)
  api.get('/invoices/inv-1/mails/', [])
  api.get('/invoices/inv-1/', () => state.invoice)
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
      expect(screen.rows()[0]).toEqual(['1', 'Consulting', '2', '100,00 €', '200,00 €'])
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

    it('has no payments yet, and links customer and project', async () => {
      await open(invoice({ project: 'prj-1', project_name: 'Website' }))
      expect(screen.hasButton(t('invoices.payments'))).toBe(false)
      expect(screen.button('Acme GmbH').getAttribute('href')).toBe('/customers/cus-1')
      expect(screen.button('Website').getAttribute('href')).toBe('/projects/prj-1')
    })

    it('lists the time entries it bills with their line', async () => {
      const { api } = await open(
        invoice({
          has_time_entries: true,
          items: [lineItem({ id: 'item-1', position: 3, time_entry_ids: ['te-1'] })],
        }),
        [timeEntry({ invoice: 'inv-1' })],
      )
      expect(api.requests('GET', '/invoices/inv-1/time-entries/')).toHaveLength(1)
      await click(screen.button(t('invoices.times')))
      expect(activeTab().rows()[0]!.slice(1)).toEqual(['3', 'Website', 'Homepage', '2:00 h'])
    })

    it('is edited on the create page, not here', async () => {
      const { router } = await open()
      expect(screen.hasButton(t('invoices.addLine'))).toBe(false)
      expect(screen.rows()[0]!.some((cell) => cell === '')).toBe(false)
      await click(screen.button(t('common.edit')))
      expect(router.currentRoute.value.path).toBe('/invoices/inv-1/edit')
    })

    it('is deleted after confirmation and leaves for the list', async () => {
      const { api, router } = await open()
      api.delete('/invoices/inv-1/')
      await click(screen.button(t('common.moreActions')))
      await click(screen.button(t('common.delete')))
      await answerConfirm(t('common.delete'))
      expect(api.requests('DELETE', '/invoices/inv-1/')).toHaveLength(1)
      expect(router.currentRoute.value.path).toBe('/invoices')
    })

    it('says so when the delete is refused', async () => {
      const { api, router } = await open()
      api.delete('/invoices/inv-1/', reply(409, { detail: 'Invoice is referenced.' }))
      await click(screen.button(t('common.moreActions')))
      await click(screen.button(t('common.delete')))
      await answerConfirm(t('common.delete'))
      expect(toasts().join()).toContain('Invoice is referenced.')
      expect(router.currentRoute.value.path).toBe('/invoices/inv-1')
    })
  })

  describe('an issued invoice', () => {
    it('is read-only: no finalize, no editing', async () => {
      await open(issued())
      expect(screen.hasButton(t('invoices.finalize'))).toBe(false)
      expect(screen.hasButton(t('invoices.addLine'))).toBe(false)
      expect(screen.hasButton(t('common.edit'))).toBe(false)
      // Its ⋮ menu offers cancelling, not deleting.
      await click(screen.button(t('common.moreActions')))
      expect(screen.hasButton(t('invoices.cancelInvoice'))).toBe(true)
      expect(screen.hasButton(t('common.delete'))).toBe(false)
      expect(screen.text()).toContain(`${t('settings.bankAccount')}Hausbank`)
    })

    it('shows what went to whom, and a mail as it was sent', async () => {
      const sentMail = {
        id: 'mail-1',
        kind: 'invoice',
        to: ['erika@acme.example', 'max@acme.example'],
        subject: 'Rechnung RE-2026-001',
        attachments: ['RE-2026-001.pdf'],
        status: 'sent',
        sent_at: '2026-11-20T10:00:00+01:00',
        error: '',
        created_at: '2026-11-20T09:59:00+01:00',
      }
      const failing = {
        ...sentMail,
        id: 'mail-2',
        kind: 'payment_reminder',
        subject: 'Zahlungserinnerung',
        status: 'queued',
        sent_at: null,
        error: 'SMTP down',
        created_at: '2026-11-23T09:00:00+01:00',
      }
      const { api } = await open(issued())
      api.get('/invoices/inv-1/mails/', [failing, sentMail])
      api.get('/invoices/inv-1/mails/mail-1/', { ...sentMail, html: '<p>Guten Tag</p>' })
      await click(screen.button(t('common.moreActions')))
      await click(screen.button(t('invoices.markSent')))
      // Reloaded after an action: the history follows.
      api.post('/invoices/inv-1/mark_sent/', issued({ status: 'sent' }))
      await click(dialog(t('invoices.markSent')).button(t('invoices.markSent')))

      await click(screen.button(t('invoices.history')))
      expect(activeTab().rows()).toEqual([
        [
          '23.11.2026 09:00',
          t('designer.mailKinds.payment_reminder'),
          'erika@acme.example, max@acme.example',
          'Zahlungserinnerung',
          t('invoices.mailStatus.failed'),
        ],
        [
          '20.11.2026 10:00',
          t('designer.mailKinds.invoice'),
          'erika@acme.example, max@acme.example',
          'Rechnung RE-2026-001',
          t('invoices.mailStatus.sent'),
        ],
      ])
      await click(activeTab().row('Rechnung RE-2026-001'))
      const modal = dialog('Rechnung RE-2026-001')
      expect(modal.text()).toContain('RE-2026-001.pdf')
      expect(modal.root.querySelector('iframe')!.getAttribute('srcdoc')).toBe('<p>Guten Tag</p>')
    })

    it('marks an unpaid invoice past its due date as overdue', async () => {
      await open(issued({ due_date: '2026-11-22' }))
      expect(screen.text()).toContain(t('invoices.receivables.overdue'))
    })

    it('offers the PDF under "Dokumente", without time report and XML here', async () => {
      await open(issued())
      await click(screen.button(t('invoices.documents')))
      expect(screen.button(t('invoices.documentPdf')).getAttribute('href')).toBe(
        '/api/v1/invoices/inv-1/pdf/',
      )
      expect(screen.hasButton(t('invoices.documentTimeReport'))).toBe(false)
      expect(screen.hasButton(t('invoices.documentXml'))).toBe(false)
    })

    it('offers the time report and the XRechnung XML when there are some', async () => {
      await open(issued({ e_invoice_format: 'xrechnung', has_time_entries: true }))
      await click(screen.button(t('invoices.documents')))
      expect(screen.button(t('invoices.documentTimeReport')).getAttribute('href')).toBe(
        '/api/v1/invoices/inv-1/time-report/',
      )
      expect(screen.button(t('invoices.documentXml')).getAttribute('href')).toBe(
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

    it('sends the e-mail to the proposed recipients, greeting whoever it goes to', async () => {
      const { api } = await open(issued({ contacts: [contact()] }))
      api.get(
        '/contacts/',
        page([contact(), contact({ id: 'con-2', name: 'Max Other', email: 'max@acme.example' })]),
      )
      api.get('/customers/cus-1/', customer())
      api.get('/invoices/inv-1/email_draft/', (call) => {
        const to = call.query.getAll('to')
        return {
          to: to.length ? to : ['erika@acme.example'],
          subject: 'Rechnung RE-2026-001',
          html: `<p>Hallo ${to.length ? to.join(' & ') : 'erika@acme.example'}</p>`,
        }
      })
      api.post('/invoices/inv-1/send_email/', issued({ status: 'sent' }))

      await click(screen.button(t('invoices.sendEmail')))
      const modal = dialog(t('invoices.sendEmail'))
      const frame = () => modal.root.querySelector('iframe')!.getAttribute('srcdoc')
      expect(modal.field(t('invoices.recipients')).textContent).toContain('erika@acme.example')
      expect(modal.input(t('invoices.mailSubject')).value).toBe('Rechnung RE-2026-001')
      expect(frame()).toBe('<p>Hallo erika@acme.example</p>')

      // Another contact with a click, an address typed in: the greeting follows.
      await click(modal.button('+ Max Other'))
      expect(frame()).toBe('<p>Hallo erika@acme.example & max@acme.example</p>')
      const input = modal.input(t('invoices.recipients'))
      input.value = 'office@acme.example'
      input.dispatchEvent(new Event('input', { bubbles: true }))
      input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
      await settle()
      expect(modal.hasButton('+ Max Other')).toBe(false)
      await click(modal.button(t('common.send')))

      expect(api.lastBody('POST', '/invoices/inv-1/send_email/')).toEqual({
        to: ['erika@acme.example', 'max@acme.example', 'office@acme.example'],
        subject: 'Rechnung RE-2026-001',
        kind: 'invoice',
      })
      expect(toasts()).toContain(t('invoices.emailQueued'))
    })

    it('removes a recipient and keeps unusable text in the field', async () => {
      const { api } = await open(issued())
      api.get('/invoices/inv-1/email_draft/', { to: ['a@acme.example'], subject: 'S', html: '' })
      await click(screen.button(t('invoices.sendEmail')))
      const modal = dialog(t('invoices.sendEmail'))
      const input = modal.input(t('invoices.recipients'))
      await type(input, 'not an address')
      expect(input.value).toBe('not an address')
      await click(modal.button(t('common.remove', { name: 'a@acme.example' })))
      expect(modal.field(t('invoices.recipients')).textContent).not.toContain('a@acme.example')
    })

    it('sends a payment reminder with the reminder template', async () => {
      const { api } = await open(issued({ contacts: [contact()] }))
      api.get('/invoices/inv-1/email_draft/', {
        subject: 'Zahlungserinnerung',
        html: '<p>Offen</p>',
      })
      api.post('/invoices/inv-1/send_email/', issued())
      await click(screen.button(t('common.moreActions')))
      await click(screen.button(t('invoices.sendReminder')))
      expect(api.requests('GET', '/invoices/inv-1/email_draft/')[0]!.query.get('kind')).toBe(
        'payment_reminder',
      )
      const modal = dialog(t('invoices.sendReminder'))
      await click(modal.button(t('common.send')))
      expect(api.lastBody('POST', '/invoices/inv-1/send_email/')).toMatchObject({
        kind: 'payment_reminder',
      })
      expect(toasts()).toContain(t('invoices.reminderQueued'))
    })

    it('marks as sent on the day given, today by default', async () => {
      const { api } = await open(issued())
      api.post('/invoices/inv-1/mark_sent/', issued({ status: 'sent' }))
      await click(screen.button(t('common.moreActions')))
      await click(screen.button(t('invoices.markSent')))
      const modal = dialog(t('invoices.markSent'))
      expect(modal.input(t('invoices.sentAt')).value).toBe('23.11.2026')
      await type(modal.input(t('invoices.sentAt')), '20.11.2026')
      await click(modal.button(t('invoices.markSent')))
      expect(api.lastBody('POST', '/invoices/inv-1/mark_sent/')).toEqual({
        sent_on: '2026-11-20',
      })
    })

    it('is cancelled only after confirmation', async () => {
      const { api, state } = await open(issued())
      api.post('/invoices/inv-1/cancel/', () => {
        state.invoice = issued({ status: 'cancelled' })
        return state.invoice
      })
      await click(screen.button(t('common.moreActions')))
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
    await render(InvoiceDetailView, { path: '/invoices/:id', url: '/invoices/inv-1' })
    expect(screen.text()).toContain(t('common.loadFailed'))
    expect(screen.button(t('nav.invoices')).closest('a')?.getAttribute('href')).toBe('/invoices')
  })
})
