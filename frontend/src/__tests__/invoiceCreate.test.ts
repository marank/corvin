import { beforeEach, describe, expect, it, vi } from 'vitest'
import InvoiceCreateView from '../views/invoices/InvoiceCreateView.vue'
import type { ApiCall } from './helpers/api'
import type { ConsolidatePreviewLine, ConsolidateRequest, Invoice } from '../api'
import { mockApi, page, reply, type ApiMock } from './helpers/api'
import {
  answerConfirm,
  choose,
  click,
  confirmText,
  dialog,
  screen,
  toasts,
  toggleCheckbox,
  type,
} from './helpers/dom'
import {
  bankAccount,
  contact,
  customer,
  invoice,
  project,
  template,
  timeEntry,
} from './helpers/fixtures'
import { render, settle, t } from './helpers/render'
import { NOW } from './helpers/time'

const entries = [
  timeEntry({ id: 'te-1', description: 'Homepage', duration_minutes: 120 }),
  timeEntry({
    id: 'te-2',
    description: 'Hosting',
    project: 'prj-2',
    project_name: 'Shop',
    start_datetime: '2026-11-21T09:00:00+01:00',
    end_datetime: '2026-11-21T10:00:00+01:00',
    duration_minutes: 60,
  }),
]

/** The server's grouping, cut down: one line per entry, or all entries on one line. */
function previewOf(call: ApiCall) {
  const body = call.body as ConsolidateRequest
  const ids = body.entry_ids ?? []
  const groups = body.group_by === 'entry' ? ids.map((id) => [id]) : ids.length ? [ids] : []
  const lines: ConsolidatePreviewLine[] = groups.map((group) => {
    const minutes = group.reduce(
      (sum, id) => sum + entries.find((entry) => entry.id === id)!.duration_minutes,
      0,
    )
    return {
      key: `${body.group_by}:${group.join(',')}`,
      entry_ids: group,
      description: `Lines ${group.join(',')}`,
      default_description: `Lines ${group.join(',')}`,
      project_name: 'Website',
      date_from: '2026-11-20',
      date_to: '2026-11-21',
      quantity: minutes / 60,
      unit: 'hours',
      unit_price: 100,
      total: (minutes / 60) * 100,
    }
  })
  for (const own of body.extra_lines ?? [])
    lines.push({
      key: null,
      entry_ids: [],
      description: own.description!,
      quantity: own.quantity!,
      unit: own.unit!,
      unit_price: own.unit_price!,
      total: own.quantity! * own.unit_price!,
    })
  const subtotal = lines.reduce((sum, line) => sum + line.total, 0)
  return {
    lines,
    entry_count: ids.length,
    subtotal,
    vat_rate: body.vat_rate,
    vat_amount: 0,
    total: subtotal,
  }
}

function backend() {
  const api = mockApi()
  api.get('/customers/', page([customer(), customer({ id: 'cus-2', name: 'Beta AG' })]))
  api.get('/customers/cus-1/', customer({ e_invoice_format: 'zugferd' }))
  api.get('/customers/cus-2/', customer({ id: 'cus-2', name: 'Beta AG', payment_terms_days: 30 }))
  api.get('/projects/', page([project(), project({ id: 'prj-2', name: 'Shop' })]))
  api.get(
    '/contacts/',
    page([contact(), contact({ id: 'con-2', name: 'Max Other', is_invoice_contact: false })]),
  )
  api.get('/bank-accounts/', page([bankAccount()]))
  api.get('/document-templates/', page([template()]))
  api.get('/settings/', {
    payment_terms_days: 14,
    vat_enabled: true,
    default_vat_rate: '19.00',
    default_bank_account: null,
  })
  api.get('/time-tracking/', page(entries))
  api.post('/invoices/consolidate_preview/', previewOf)
  return api
}

async function open(url = '/invoices/new?customer=cus-1') {
  return render(InvoiceCreateView, { path: '/invoices/new', url })
}

/** The preview request waits 200 ms for more changes. */
async function waitForPreview() {
  await vi.advanceTimersByTimeAsync(300)
  await settle()
}

/** "Positionen holen" with every offered entry ticked, then "Übernehmen". */
async function fetchAll() {
  await click(screen.button(t('invoices.fetchPositions')))
  await click(dialog(t('invoices.fetchPositions')).button(t('invoices.takeOver')))
  await waitForPreview()
}

const lastPreview = (api: ApiMock) =>
  api.lastBody('POST', '/invoices/consolidate_preview/') as ConsolidateRequest

/** The text field of the line that reads `text`. */
function lineText(text: string) {
  const field = [...screen.root.querySelectorAll<HTMLTextAreaElement>('tbody textarea')].find(
    (el) => el.value === text,
  )
  if (!field) throw new Error(`no line reads "${text}"`)
  return field
}

describe('InvoiceCreateView', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date', 'setTimeout', 'clearTimeout'], now: NOW })
  })

  it('needs a customer before fetching lines', async () => {
    const api = backend()
    await open('/invoices/new')
    expect(screen.text()).toContain(t('invoices.pickCustomer'))
    expect(screen.button(t('invoices.fetchPositions')).hasAttribute('disabled')).toBe(true)
    expect(screen.button(t('invoices.createDraft')).hasAttribute('disabled')).toBe(true)

    await choose(screen.field(t('projects.customer')), 'Beta AG')
    expect(screen.button(t('invoices.fetchPositions')).hasAttribute('disabled')).toBe(false)
    expect(api.requests('GET', '/time-tracking/')).toHaveLength(0)
  })

  it('offers only billable, uninvoiced, finished entries outside contracts', async () => {
    const api = backend()
    await open()
    await click(screen.button(t('invoices.fetchPositions')))
    const modal = dialog(t('invoices.fetchPositions'))
    await type(modal.input(t('invoices.dateFrom')), '1.11.')
    await type(modal.input(t('invoices.dateTo')), '301126')
    expect(Object.fromEntries(api.requests('GET', '/time-tracking/').at(-1)!.query)).toEqual({
      customer: 'cus-1',
      billable: 'true',
      invoice__isnull: 'true',
      contract__isnull: 'true',
      end_datetime__isnull: 'false',
      ordering: 'start_datetime',
      start_datetime__date__gte: '2026-11-01',
      start_datetime__date__lte: '2026-11-30',
      page_size: '500',
    })
    expect(modal.text()).toContain(t('invoices.selectedEntries', { selected: 2, total: 2 }))
    expect(modal.text()).toContain('3:00 h')
  })

  it('takes over the ticked entries and groups them on the invoice', async () => {
    const api = backend()
    await open()
    await click(screen.button(t('invoices.fetchPositions')))
    await toggleCheckbox(dialog(t('invoices.fetchPositions')).row('Hosting'))
    await click(dialog(t('invoices.fetchPositions')).button(t('invoices.takeOver')))
    await waitForPreview()
    expect(lastPreview(api)).toMatchObject({ entry_ids: ['te-1'], group_by: 'day', vat_rate: 19 })
    expect(lineText('Lines te-1').value).toBe('Lines te-1')

    // Fetched later: joins the invoice; entries already on it are not offered again.
    await click(screen.button(t('invoices.fetchPositions')))
    expect(dialog(t('invoices.fetchPositions')).rows()).toHaveLength(1)
    await click(dialog(t('invoices.fetchPositions')).button(t('invoices.takeOver')))
    await waitForPreview()
    expect(lastPreview(api).entry_ids).toEqual(['te-1', 'te-2'])

    await click(screen.button(t('invoices.groupBys.entry')))
    await waitForPreview()
    expect(lastPreview(api).group_by).toBe('entry')
    expect(screen.rows().filter((row) => row[0] !== '')).toHaveLength(2)
  })

  it('creates the draft with the texts as edited and the general fields', async () => {
    const api = backend()
    api.post('/invoices/consolidate/', invoice({ id: 'inv-9' }))
    const { router } = await open()
    await fetchAll()
    await type(lineText('Lines te-1,te-2'), 'Website work')
    await click(screen.button(t('invoices.createDraft')))

    expect(api.lastBody('POST', '/invoices/consolidate/')).toEqual({
      customer_id: 'cus-1',
      project_id: null,
      contact_ids: ['con-1'],
      bank_account_id: null,
      e_invoice_format: 'zugferd',
      entry_ids: ['te-1', 'te-2'],
      group_by: 'day',
      vat_rate: 19,
      issue_date: '2026-11-23',
      due_date: '2026-12-07',
      template_id: null,
      notes: '',
      extra_lines: [],
      entry_lines: [{ entry_ids: ['te-1', 'te-2'], description: 'Website work' }],
    })
    expect(router.currentRoute.value.path).toBe('/invoices/inv-9')
    // Created: leaving needs no confirmation.
    expect(confirmText()).toBe('')
  })

  it('keeps edited texts until regrouping, and asks before that', async () => {
    const api = backend()
    await open()
    await fetchAll()
    await type(lineText('Lines te-1,te-2'), 'Website work')
    expect(screen.hasButton(t('invoices.resetText'))).toBe(true)

    await click(screen.button(t('invoices.groupBys.entry')))
    expect(confirmText()).toContain(t('invoices.regroupMessage'))
    await answerConfirm(t('common.cancel'))
    await waitForPreview()
    expect(lastPreview(api).group_by).toBe('day')

    await click(screen.button(t('invoices.groupBys.entry')))
    await answerConfirm(t('invoices.regroup'))
    await waitForPreview()
    expect(lastPreview(api).group_by).toBe('entry')
    expect(screen.hasButton(t('invoices.resetText'))).toBe(false)
  })

  it('removes lines of other projects once the invoice gets a project', async () => {
    const api = backend()
    await open()
    await fetchAll()
    await choose(screen.field(t('projects.project')), 'Website')
    expect(confirmText()).toContain(t('invoices.otherProjectsMessage', 1))
    await answerConfirm(t('invoices.removeOtherProjects'))
    await waitForPreview()
    expect(lastPreview(api).entry_ids).toEqual(['te-1'])
  })

  it('keeps the project and the lines when removing is cancelled', async () => {
    const api = backend()
    await open()
    await fetchAll()
    await choose(screen.field(t('projects.project')), 'Website')
    await answerConfirm(t('common.cancel'))
    await waitForPreview()
    expect(lastPreview(api).entry_ids).toEqual(['te-1', 'te-2'])
    expect(screen.field(t('projects.project')).textContent).not.toContain('Website')
  })

  it('lets the due date follow the issue date and the payment terms', async () => {
    backend()
    await open('/invoices/new')
    expect(screen.input(t('invoices.issueDate')).value).toBe('23.11.2026')
    expect(screen.input(t('invoices.dueDate')).value).toBe('07.12.2026')

    // The customer's own terms win over the company's.
    await choose(screen.field(t('projects.customer')), 'Beta AG')
    expect(screen.input(t('invoices.dueDate')).value).toBe('23.12.2026')
    await type(screen.input(t('invoices.issueDate')), '1.12.2026')
    expect(screen.input(t('invoices.dueDate')).value).toBe('31.12.2026')

    // A date of the user's own stays put.
    await type(screen.input(t('invoices.dueDate')), '15.1.2027')
    await type(screen.input(t('invoices.issueDate')), '2.12.2026')
    expect(screen.input(t('invoices.dueDate')).value).toBe('15.01.2027')
  })

  it('hides rarely needed fields until asked', async () => {
    const api = backend()
    api.post('/invoices/consolidate/', invoice({ id: 'inv-9' }))
    await open()
    expect(() => screen.field(t('invoices.template'))).toThrow()
    await click(screen.button(t('invoices.showMore')))
    // The customer's defaults are preselected.
    expect(screen.field(t('invoices.eInvoice')).textContent).toContain(
      t('invoices.eInvoiceFormats.zugferd'),
    )
    expect(screen.input(t('invoices.vatRate')).value).toBe('19 %')

    await choose(screen.field(t('invoices.template')), template().name)
    await type(screen.input(t('common.notes')), 'Thanks!')

    await fetchAll()
    await click(screen.button(t('invoices.createDraft')))
    expect(api.lastBody('POST', '/invoices/consolidate/')).toMatchObject({
      template_id: template().id,
      notes: 'Thanks!',
    })
  })

  it('adds own lines to the invoice', async () => {
    const api = backend()
    await open()
    await click(screen.button(t('invoices.addLine')))
    const row = screen.root.querySelector<HTMLElement>('tbody tr')!
    await type(row.querySelector('textarea')!, 'Domain')
    await type(row.querySelectorAll('input')[0]!, '2')
    await type(row.querySelectorAll('input')[1]!, '12.5')
    await waitForPreview()

    expect(lastPreview(api).extra_lines).toEqual([
      { description: 'Domain', quantity: 2, unit: 'flat', unit_price: 12.5 },
    ])
    expect(screen.text()).toContain('25,00 €')
    expect(screen.button(t('invoices.createDraft')).hasAttribute('disabled')).toBe(false)

    await click(screen.row('25,00 €').querySelector(`[aria-label="${t('common.delete')}"]`)!)
    expect(screen.text()).toContain(t('invoices.noLinesYet'))
  })

  it('shows why the invoice could not be calculated and holds it back', async () => {
    const api = backend()
    api.post('/invoices/consolidate_preview/', reply(400, { detail: 'No hourly rate for Acme.' }))
    await open()
    await fetchAll()
    expect(screen.text()).toContain('No hourly rate for Acme.')
    expect(screen.button(t('invoices.createDraft')).hasAttribute('disabled')).toBe(true)
  })

  it('stays on the page when creating fails', async () => {
    const api = backend()
    api.post('/invoices/consolidate/', reply(400, { detail: 'Customer has no address.' }))
    const { router } = await open()
    await fetchAll()
    await click(screen.button(t('invoices.createDraft')))
    expect(toasts().join()).toContain('Customer has no address.')
    expect(router.currentRoute.value.path).toBe('/invoices/new')
  })

  it('warns when no bank account has an IBAN', async () => {
    const api = backend()
    api.get('/bank-accounts/', page([bankAccount({ iban: '' })]))
    await open()
    expect(screen.text()).toContain(t('invoices.noIbanHint'))
  })

  it('asks before leaving a started invoice', async () => {
    backend()
    const { router } = await open()
    await fetchAll()

    await click(screen.button(t('nav.invoices')))
    expect(confirmText()).toContain(t('common.unsavedMessage'))
    await answerConfirm(t('common.keepEditing'))
    expect(router.currentRoute.value.path).toBe('/invoices/new')

    await click(screen.button(t('nav.invoices')))
    await answerConfirm(t('common.discard'))
    expect(router.currentRoute.value.path).toBe('/invoices')
  })

  it('leaves an untouched page without asking', async () => {
    backend()
    const { router } = await open()
    await click(screen.button(t('common.cancel')))
    expect(confirmText()).toBe('')
    expect(router.currentRoute.value.path).toBe('/invoices')
  })

  describe('editing a draft', () => {
    /** The draft bills Homepage (text edited) and has an own line; Hosting is open. */
    async function openDraft(over: Partial<Invoice> = {}) {
      const api = backend()
      api.get('/time-tracking/', page([entries[1]]))
      api.get(
        '/invoices/inv-1/',
        invoice({ contacts: [contact()], e_invoice_format: 'zugferd', ...over }),
      )
      api.get('/invoices/inv-1/draft/', {
        group_by: 'entry',
        entries: [entries[0]],
        texts: { 'entry:te-1': 'Edited' },
        own_lines: [{ description: 'Travel', quantity: '1.00', unit: 'flat', unit_price: '30.00' }],
      })
      api.post('/invoices/inv-1/draft_preview/', previewOf)
      const view = await render(InvoiceCreateView, {
        path: '/invoices/:id/edit',
        url: '/invoices/inv-1/edit',
      })
      await waitForPreview()
      return { api, ...view }
    }

    it('shows the draft as saved and leaves it without asking', async () => {
      const { api, router } = await openDraft()
      expect(screen.text()).toContain(t('invoices.editTitle', { number: 'RE-2026-001' }))
      expect(screen.input(t('common.number')).value).toBe('RE-2026-001')
      expect(screen.input(t('invoices.issueDate')).value).toBe('20.11.2026')
      expect(screen.input(t('invoices.dueDate')).value).toBe('04.12.2026')
      expect(lineText('Edited')).toBeTruthy()
      expect(lineText('Travel')).toBeTruthy()
      expect(api.lastBody('POST', '/invoices/inv-1/draft_preview/')).toMatchObject({
        entry_ids: ['te-1'],
        group_by: 'entry',
      })
      expect(api.requests('POST', '/invoices/consolidate_preview/')).toHaveLength(0)
      // The customer stays.
      expect(screen.field(t('projects.customer')).querySelector('.p-disabled')).toBeTruthy()

      await click(screen.button(t('common.cancel')))
      expect(confirmText()).toBe('')
      expect(router.currentRoute.value.path).toBe('/invoices/inv-1')
    })

    it('saves the page back onto the draft', async () => {
      const { api, router } = await openDraft()
      api.put('/invoices/inv-1/draft/', invoice())
      await type(screen.input(t('common.number')), 'RE-2026-007')
      await type(lineText('Edited'), 'Edited again')
      await click(screen.button(t('common.save')))

      expect(api.lastBody('PUT', '/invoices/inv-1/draft/')).toMatchObject({
        customer_id: 'cus-1',
        number: 'RE-2026-007',
        contact_ids: ['con-1'],
        e_invoice_format: 'zugferd',
        issue_date: '2026-11-20',
        due_date: '2026-12-04',
        vat_rate: 19,
        entry_lines: [{ entry_ids: ['te-1'], description: 'Edited again' }],
        extra_lines: [{ description: 'Travel', quantity: 1, unit: 'flat', unit_price: 30 }],
      })
      expect(router.currentRoute.value.path).toBe('/invoices/inv-1')
    })

    it('offers entries removed from the draft again', async () => {
      await openDraft()
      await click(
        lineText('Edited')
          .closest('tr')!
          .querySelector(`[aria-label="${t('common.delete')}"]`)!,
      )
      await click(screen.button(t('invoices.fetchPositions')))
      const offered = dialog(t('invoices.fetchPositions')).rows()
      expect(offered.map((row) => row[3])).toEqual(['Homepage', 'Hosting'])
    })

    it('opens the rarely needed fields only when one of them is set', async () => {
      await openDraft()
      expect(() => screen.field(t('invoices.template'))).toThrow()
      expect(screen.hasButton(t('invoices.showMore'))).toBe(true)
    })

    it('shows set rarely needed fields right away', async () => {
      await openDraft({ notes: 'Thanks!' })
      expect(screen.input(t('common.notes')).value).toBe('Thanks!')
      await click(screen.button(t('invoices.showLess')))
      expect(() => screen.field(t('common.notes'))).toThrow()
    })

    it('sends a finalized invoice back to its page', async () => {
      const { router } = await openDraft({ status: 'issued' })
      expect(router.currentRoute.value.path).toBe('/invoices/inv-1')
    })
  })
})
