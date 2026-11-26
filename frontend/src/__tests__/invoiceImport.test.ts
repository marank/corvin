import { describe, expect, it } from 'vitest'
import InvoiceImportView from '../views/invoices/InvoiceImportView.vue'
import { mockApi, page, reply } from './helpers/api'
import { choose, click, screen, type } from './helpers/dom'
import { customer, invoice, project, timeEntry } from './helpers/fixtures'
import { render, settle, t } from './helpers/render'

function backend(vatEnabled = true) {
  const api = mockApi()
  api.get('/customers/', page([customer()]))
  api.get('/projects/', page([project()]))
  api.get('/settings/', { vat_enabled: vatEnabled, default_vat_rate: '19.00' })
  api.get(
    '/time-tracking/',
    page([timeEntry(), timeEntry({ id: 'te-2', description: 'Hosting', duration_minutes: 60 })]),
  )
  return api
}

async function attach(label: string, file: File) {
  const input = screen.root.querySelector<HTMLInputElement>(`input[aria-label="${label}"]`)!
  Object.defineProperty(input, 'files', { value: [file], configurable: true })
  input.dispatchEvent(new Event('change'))
  await settle()
}

const pdf = () => new File(['%PDF-1.4'], 'RE-17.pdf', { type: 'application/pdf' })

describe('InvoiceImportView', () => {
  it('records an external invoice with its PDF and the time entries it billed', async () => {
    const api = backend()
    api.post('/invoices/import_external/', invoice({ id: 'inv-7', is_external: true }))
    const { router } = await render(InvoiceImportView, { path: '/invoices/import' })
    expect(screen.button(t('invoices.importSave')).hasAttribute('disabled')).toBe(true)

    await choose(screen.field(t('projects.customer')), 'Acme GmbH')
    expect(api.requests('GET', '/time-tracking/').at(-1)!.query.get('invoice__isnull')).toBe('true')
    await type(screen.input(t('invoices.number')), 'RE-17')
    await type(screen.input(t('invoices.netAmount')), '100')
    expect(screen.text()).toContain('119,00 €')
    await click(screen.row('Hosting'))
    await attach(t('invoices.pdfFile'), pdf())
    expect(screen.text()).toContain('RE-17.pdf')
    await click(screen.button(t('invoices.importSave')))

    const body = api.lastBody('POST', '/invoices/import_external/') as FormData
    expect(body.get('customer_id')).toBe('cus-1')
    expect(body.get('number')).toBe('RE-17')
    expect(body.get('issue_date')).toBe('2026-11-23')
    expect(body.get('net')).toBe('100.00')
    expect(body.get('vat_rate')).toBe('19')
    expect((body.get('pdf') as File).name).toBe('RE-17.pdf')
    expect(body.getAll('entry_ids')).toEqual(['te-2'])
    expect(body.has('xml')).toBe(false)
    expect(router.currentRoute.value.path).toBe('/invoices/inv-7')
  })

  it('asks for the amount alone without VAT', async () => {
    const api = backend(false)
    api.post('/invoices/import_external/', invoice({ id: 'inv-7' }))
    await render(InvoiceImportView, { path: '/invoices/import' })
    expect(() => screen.field(t('invoices.vatRate'))).toThrow()
    await choose(screen.field(t('projects.customer')), 'Acme GmbH')
    await type(screen.input(t('invoices.number')), 'RE-17')
    await type(screen.input(t('common.amount')), '250')
    await attach(t('invoices.pdfFile'), pdf())
    await click(screen.button(t('invoices.importSave')))
    const body = api.lastBody('POST', '/invoices/import_external/') as FormData
    expect(body.get('net')).toBe('250.00')
    expect(body.has('vat_rate')).toBe(false)
  })

  it('shows why the upload was refused', async () => {
    const api = backend()
    api.post('/invoices/import_external/', reply(400, { number: ['Diese Nummer ist vergeben.'] }))
    const { router } = await render(InvoiceImportView, { path: '/invoices/import' })
    await choose(screen.field(t('projects.customer')), 'Acme GmbH')
    await type(screen.input(t('invoices.number')), 'RE-1')
    await attach(t('invoices.pdfFile'), pdf())
    await click(screen.button(t('invoices.importSave')))
    expect(screen.fieldError(t('invoices.number'))).toBe('Diese Nummer ist vergeben.')
    expect(router.currentRoute.value.path).toBe('/invoices/import')
  })
})
