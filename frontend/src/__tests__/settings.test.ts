import { afterEach, describe, expect, it, vi } from 'vitest'
import SettingsProfileView from '../views/settings/SettingsProfileView.vue'
import type { CompanyImage } from '../api'
import { setLocale } from '../i18n'
import { useFormattingStore } from '../stores/formatting'
import { useSettingsStore } from '../stores/settings'
import { mockApi, page, reply, type ApiMock } from './helpers/api'
import {
  activeTab,
  answerConfirm,
  choose,
  click,
  confirmText,
  dialog,
  screen,
  toasts,
  toggleCheckbox,
  type,
  within,
} from './helpers/dom'
import { bankAccount, rate } from './helpers/fixtures'
import { render, settle, t } from './helpers/render'
import { NOW } from './helpers/time'

const settings = {
  company_name: 'Corvin IT',
  email: 'info@corvin.example',
  vat_enabled: true,
  default_vat_rate: 19,
  currency: 'EUR',
  currency_display: 'symbol',
  default_bank_account: 'bank-1',
  // Stored before scopes became lists.
  numbering_schemes: { invoice: { format: 'R-{counter:3}', scope: 'customer_year', start: 5 } },
}

const image = (over: Partial<CompanyImage> = {}): CompanyImage => ({
  id: 'img-1',
  kind: 'logo_light',
  key: 'logo_light',
  name: 'Logo',
  image: 'logo.png',
  url: '/api/v1/company-images/img-1/file/',
  ...over,
})

function backend(images: CompanyImage[] = []) {
  const api = mockApi()
  const state = { settings: { ...settings } as Record<string, unknown> }
  api.get('/settings/', () => state.settings)
  api.put(
    '/settings/',
    (call) => (state.settings = { ...state.settings, ...(call.body as object) }),
  )
  api.get(
    '/bank-accounts/',
    page([bankAccount(), bankAccount({ id: 'bank-2', name: 'Tagesgeld', iban: 'DE99' })]),
  )
  api.get('/company-contacts/', page([]))
  api.get('/company-images/', page(images))
  api.get('/hourly-rates/', page([rate()]))
  api.post('/settings/preview-number/', (call) => {
    const body = call.body as { entity: string; format: string }
    return { preview: `${body.format.replace(/\{counter(:\d)?\}/, '0042')}` }
  })
  return { api, state }
}

const open = (url = '/settings') => render(SettingsProfileView, { path: '/settings', url })
const openTab = (name: string) => click(screen.button(name))

/** The numbering row of one entity. */
function numberingRow(entity: string) {
  const name = [...document.querySelectorAll('.font-medium')].find(
    (el) => el.textContent.trim() === t(`settings.entities.${entity}`),
  )
  return within(name!.parentElement!)
}

describe('SettingsProfileView', () => {
  afterEach(() => setLocale('de'))

  it('saves the company data, the numbering and the formatting the app then uses', async () => {
    const { api } = backend()
    const { pinia } = await open()
    expect(screen.input(t('settings.companyName')).value).toBe('Corvin IT')
    await type(screen.input(t('settings.companyName')), 'Corvin GmbH')
    await choose(screen.field(t('settings.currencyDisplay')), t('settings.currencyDisplays.code'))
    await click(screen.button(t('common.save')))

    const body = api.lastBody('PUT', '/settings/') as Record<string, unknown>
    expect(body).toMatchObject({ company_name: 'Corvin GmbH', currency_display: 'code' })
    expect(Object.keys(body.numbering_schemes as object)).toEqual([
      'customer',
      'project',
      'invoice',
      'contract',
      'visit',
      'task',
    ])
    expect(toasts()).toContain(t('common.saved'))
    expect(useFormattingStore(pinia).currencyDisplay).toBe('code')
  })

  it('shows API errors on the company fields', async () => {
    const { api } = backend()
    api.put('/settings/', reply(400, { email: ['Enter a valid email address.'] }))
    await open()
    await click(screen.button(t('common.save')))
    expect(screen.fieldError(t('common.email'))).toBe('Enter a valid email address.')
  })

  it('labels every field in the UI language', async () => {
    backend()
    setLocale('en')
    await open()
    expect(screen.field('Postal code')).toBeTruthy()
  })

  it('locks the VAT rate while VAT is off', async () => {
    backend()
    await open()
    expect(screen.input(t('settings.defaultVat')).disabled).toBe(false)
    await toggleCheckbox(screen.checkbox(t('settings.vatEnabled')))
    expect(screen.input(t('settings.defaultVat')).disabled).toBe(true)
  })

  it('asks before leaving with unsaved changes', async () => {
    backend()
    const { router } = await open()
    await type(screen.input(t('settings.companyName')), 'Changed')
    void router.push('/')
    await settle()
    expect(confirmText()).toContain(t('common.unsavedMessage'))
    await answerConfirm(t('common.discard'))
    expect(router.currentRoute.value.path).toBe('/')
  })

  describe('numbering', () => {
    it('reads old single-name scopes and previews every scheme once', async () => {
      vi.useFakeTimers({ toFake: ['Date', 'setTimeout', 'clearTimeout'], now: NOW })
      const { api } = backend()
      await open()
      await openTab(t('settings.numbering'))
      await vi.advanceTimersByTimeAsync(1000)
      await settle()
      const invoice = numberingRow('invoice')
      expect(invoice.input(t('settings.numberFormat')).value).toBe('R-{counter:3}')
      expect(invoice.text()).toContain(t('settings.scopes.customer'))
      expect(invoice.text()).toContain(t('settings.scopes.year'))
      expect(invoice.text()).toContain('R-0042')
      expect(api.requests('POST', '/settings/preview-number/')).toHaveLength(6)
      expect(
        api
          .requests('POST', '/settings/preview-number/')
          .find((c) => (c.body as { entity: string }).entity === 'invoice')!.body,
      ).toEqual({
        entity: 'invoice',
        format: 'R-{counter:3}',
        scope: ['customer', 'year'],
        start: 5,
      })
    })

    it('updates the preview shortly after the format changes', async () => {
      vi.useFakeTimers({ toFake: ['Date', 'setTimeout', 'clearTimeout'], now: NOW })
      const { api } = backend()
      await open()
      await openTab(t('settings.numbering'))
      await vi.advanceTimersByTimeAsync(250)
      await settle()
      const before = api.requests('POST', '/settings/preview-number/').length
      await type(numberingRow('task').input(t('settings.numberFormat')), 'A-{counter}')
      expect(api.requests('POST', '/settings/preview-number/')).toHaveLength(before)
      await vi.advanceTimersByTimeAsync(250)
      await settle()
      expect(numberingRow('task').text()).toContain('A-0042')
    })

    it('shows a dash for a format the backend cannot preview', async () => {
      vi.useFakeTimers({ toFake: ['Date', 'setTimeout', 'clearTimeout'], now: NOW })
      const { api } = backend()
      api.post('/settings/preview-number/', reply(400, { format: ['Unknown placeholder.'] }))
      await open()
      await openTab(t('settings.numbering'))
      await vi.advanceTimersByTimeAsync(250)
      await settle()
      expect(numberingRow('customer').text()).toContain('—')
    })
  })

  describe('bank accounts', () => {
    it('opens directly from the invoice hint, with the Save button hidden', async () => {
      backend()
      await open('/settings?tab=bankAccounts')
      expect(activeTab().row('Hausbank')).toBeTruthy()
      // Hidden rather than removed, so the header keeps its height across tabs.
      expect(screen.button(t('common.save')).classList).toContain('invisible')
    })

    it('adds an account and shows an invalid IBAN on its field', async () => {
      const { api } = backend()
      api.post('/bank-accounts/', reply(400, { iban: ['Invalid IBAN.'] }))
      await open('/settings?tab=bankAccounts')
      await click(screen.button(t('settings.newBankAccount')))
      const modal = dialog(t('settings.newBankAccount'))
      await type(modal.input(t('common.name')), 'Geschäftskonto')
      await type(modal.input(t('settings.iban')), 'DE00 1234')
      await click(modal.button(t('common.save')))
      expect(api.lastBody('POST', '/bank-accounts/')).toEqual({
        is_active: true,
        name: 'Geschäftskonto',
        iban: 'DE00 1234',
      })
      expect(dialog(t('settings.newBankAccount')).fieldError(t('settings.iban'))).toBe(
        'Invalid IBAN.',
      )
    })

    it('makes another account the default', async () => {
      const { api } = backend()
      await open('/settings?tab=bankAccounts')
      const row = activeTab().row('Tagesgeld')
      await click(row.querySelector('.lucide--star')!.closest('button')!)
      expect(api.lastBody('PUT', '/settings/')).toEqual({ default_bank_account: 'bank-2' })
      expect(activeTab().row('Tagesgeld').querySelector('.lucide--check')).not.toBeNull()
      expect(activeTab().row('Hausbank').querySelector('.lucide--check')).toBeNull()
    })

    it('forgets the default when its account is deleted', async () => {
      const { api } = backend()
      api.delete('/bank-accounts/bank-1/')
      await open('/settings?tab=bankAccounts')
      await click(
        activeTab()
          .row('Hausbank')
          .querySelector(`[aria-label="${t('common.delete')}"]`)!,
      )
      await answerConfirm(t('common.delete'))
      expect(api.requests('DELETE', '/bank-accounts/bank-1/')).toHaveLength(1)
      expect(activeTab().text()).not.toContain('Hausbank')
    })

    it('edits an account', async () => {
      const { api } = backend()
      api.put('/bank-accounts/bank-2/', (call) => call.body)
      await open('/settings?tab=bankAccounts')
      await click(activeTab().row('Tagesgeld'))
      const modal = dialog(t('settings.editBankAccount'))
      await type(modal.input(t('settings.bic')), 'GENODEF1')
      await click(modal.button(t('common.save')))
      expect(api.lastBody('PUT', '/bank-accounts/bank-2/')).toMatchObject({
        id: 'bank-2',
        bic: 'GENODEF1',
      })
    })
  })

  it('adds a company contact', async () => {
    const { api } = backend()
    api.post('/company-contacts/', (call) => call.body)
    await open('/settings?tab=contacts')
    await click(screen.button(t('settings.newCompanyContact')))
    const modal = dialog(t('settings.newCompanyContact'))
    await type(modal.input(t('customers.firstName')), 'Matthias')
    await click(modal.button(t('common.save')))
    expect(api.lastBody('POST', '/company-contacts/')).toEqual({ first_name: 'Matthias' })
    expect(toasts()).toContain(t('common.saved'))
  })

  describe('images', () => {
    async function pickFile(input: HTMLInputElement, file: File) {
      Object.defineProperty(input, 'files', { value: [file], configurable: true })
      input.dispatchEvent(new Event('change'))
      await settle()
    }
    const uploads = (api: ApiMock) => api.calls.filter((c) => c.path.startsWith('/company-images/'))

    it('uploads a logo, and replaces it on the next upload', async () => {
      const { api } = backend()
      const stored: CompanyImage[] = []
      api.get('/company-images/', () => page(stored))
      api.post('/company-images/', () => {
        stored.push(image())
        return image()
      })
      api.put('/company-images/img-1/', image())
      await open('/settings?tab=images')
      const inputs = activeTab().root.querySelectorAll<HTMLInputElement>('input[type=file]')
      await pickFile(inputs[0]!, new File(['png'], 'logo.png', { type: 'image/png' }))
      const sent = api.lastBody('POST', '/company-images/') as FormData
      expect(sent.get('kind')).toBe('logo_light')
      expect(sent.get('name')).toBe(t('settings.imageKinds.logo_light'))
      expect((sent.get('image') as File).name).toBe('logo.png')

      await pickFile(inputs[0]!, new File(['png'], 'logo2.png', { type: 'image/png' }))
      expect(uploads(api).at(-2)).toMatchObject({ method: 'PUT', path: '/company-images/img-1/' })
    })

    it('shows the uploaded logo and deletes it', async () => {
      const { api } = backend([image()])
      api.delete('/company-images/img-1/')
      await open('/settings?tab=images')
      const logo = activeTab().root.querySelector('img')!
      expect(logo.getAttribute('src')).toBe('/api/v1/company-images/img-1/file/')
      await click(activeTab().button(t('common.delete')))
      await answerConfirm(t('common.delete'))
      expect(activeTab().root.querySelector('img')).toBeNull()
    })

    it('adds a named image for templates', async () => {
      const { api } = backend()
      api.post('/company-images/', image({ kind: 'additional', key: 'signature' }))
      await open('/settings?tab=images')
      await click(screen.button(t('settings.addImage')))
      const modal = dialog(t('settings.addImage'))
      await type(modal.input(t('common.name')), 'Unterschrift')
      await type(modal.input(t('settings.imageKey')), 'signature')
      await pickFile(
        modal.field(t('settings.imageFile')).querySelector('input')!,
        new File(['png'], 'sig.png'),
      )
      await click(modal.button(t('common.save')))
      const sent = api.lastBody('POST', '/company-images/') as FormData
      expect([sent.get('kind'), sent.get('key'), sent.get('name')]).toEqual([
        'additional',
        'signature',
        'Unterschrift',
      ])
    })
  })

  it('saves the timer behaviour for the whole app', async () => {
    const { api } = backend()
    const { pinia } = await open('/settings?tab=timeTracking')
    await toggleCheckbox(screen.checkbox(t('settings.timerCountsDuringBreak')))
    await choose(screen.field(t('settings.openStoppedTimeEntry')), t('common.yes'))
    await choose(
      screen.field(t('settings.timeRoundingEndDirection')),
      t('settings.roundingDirections.forwards'),
    )
    await click(screen.button(t('common.save')))
    expect(api.lastBody('PUT', '/settings/')).toMatchObject({
      timer_counts_during_break: true,
      open_stopped_time_entry: 'yes',
      time_rounding_end_direction: 'forwards',
    })
    const store = useSettingsStore(pinia)
    expect(store.timerCountsDuringBreak).toBe(true)
    expect(store.openStoppedTimeEntry).toBe('yes')
  })

  it('lists the default hourly rates', async () => {
    backend()
    await open('/settings?tab=rates')
    expect(activeTab().text()).toContain(t('rates.defaultsHint'))
    expect(activeTab().text()).toContain('95,00 €')
  })
})
