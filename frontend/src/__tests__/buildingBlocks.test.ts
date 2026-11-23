import { describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent, h, ref } from 'vue'
import { ApiError } from '../api/client'
import { customersApi, invoicesApi, templatesApi } from '../api'
import { usePagination } from '../composables/usePagination'
import { useFormattingStore } from '../stores/formatting'
import { getCurrencyName, getCurrencySymbol } from '../currencies'
import AppMoneyDisplay from '../components/ui/AppMoneyDisplay.vue'
import AppNumberDisplay from '../components/ui/AppNumberDisplay.vue'
import AppDateInput from '../components/ui/AppDateInput.vue'
import AppDateTimeInput from '../components/ui/AppDateTimeInput.vue'
import AppDurationDisplay from '../components/ui/AppDurationDisplay.vue'
import AppDateTimeDisplay from '../components/ui/AppDateTimeDisplay.vue'
import AppCodeEditor from '../components/ui/AppCodeEditor.vue'
import InvoicePreviewFrame from '../components/InvoicePreviewFrame.vue'
import { mockApi, page, reply } from './helpers/api'
import { click, screen, type, typeOnly } from './helpers/dom'
import { render, settle, t } from './helpers/render'

describe('API client', () => {
  it('sends the CSRF token, the UI language and JSON', async () => {
    document.cookie = 'csrftoken=tok%2Fen'
    const api = mockApi()
    api.post('/customers/', { id: 'c' })
    await customersApi.create({ name: 'X' })
    const call = api.requests('POST', '/customers/')[0]!
    expect(call.headers).toEqual({
      'Content-Type': 'application/json',
      'X-CSRFToken': 'tok/en',
      'Accept-Language': 'de',
    })
    expect(call.body).toEqual({ name: 'X' })
  })

  it('turns error responses into ApiError with the parsed body', async () => {
    mockApi().get('/customers/c/', reply(404, { detail: 'Not found.' }))
    await expect(customersApi.get('c')).rejects.toEqual(
      expect.objectContaining({ status: 404, data: { detail: 'Not found.' } }),
    )
  })

  it('keeps a non-JSON error body as text', async () => {
    mockApi().get('/customers/c/', reply(502, 'Bad Gateway'))
    const error = (await customersApi.get('c').catch((e: unknown) => e)) as ApiError
    expect(error).toBeInstanceOf(ApiError)
    expect(error.data).toBe('Bad Gateway')
  })

  it('reads 204 as no content', async () => {
    mockApi().delete('/customers/c/')
    await expect(customersApi.remove('c')).resolves.toBeUndefined()
  })

  it('returns binary previews as a blob, and their errors as ApiError', async () => {
    const api = mockApi()
    api.post('/document-templates/t/preview-pdf/', new Blob(['%PDF']))
    expect(await (await templatesApi.previewDraftPdf('t', {})).text()).toBe('%PDF')
    api.post('/document-templates/t/preview-pdf/', reply(400, { detail: 'Broken.' }))
    await expect(templatesApi.previewDraftPdf('t', {})).rejects.toMatchObject({
      data: { detail: 'Broken.' },
    })
    api.post('/document-templates/t/preview-pdf/', reply(500, 'oops'))
    await expect(templatesApi.previewDraftPdf('t', {})).rejects.toMatchObject({ data: 'oops' })
  })

  it('builds the download links', () => {
    expect(invoicesApi.pdfUrl('i')).toBe('/api/v1/invoices/i/pdf/')
    expect(templatesApi.previewPdfUrl('t')).toBe('/api/v1/document-templates/t/preview-pdf/')
  })
})

describe('usePagination', () => {
  it('asks for the page, its size and the ordering', async () => {
    const request = vi.fn(() => Promise.resolve(page([1, 2], 2)))
    const pagination = usePagination(() => undefined, '-date')
    expect(await pagination.fetchPage(request, new URLSearchParams({ q: 'x' }))).toEqual([1, 2])
    expect(request).toHaveBeenCalledWith('q=x&page=1&page_size=50&ordering=-date')
    expect(pagination.totalRecords.value).toBe(2)
  })

  it('goes back to the last page when the list got shorter', async () => {
    const request = vi.fn((query: string) =>
      Promise.resolve(page(query.includes('page=3') ? [] : ['x'], 51)),
    )
    const pagination = usePagination(() => undefined)
    pagination.page.value = 3
    expect(await pagination.fetchPage(request)).toEqual(['x'])
    expect(pagination.page.value).toBe(2)
  })

  it('starts over at page one when the page is gone', async () => {
    const request = vi.fn((query: string) =>
      query.includes('page=4')
        ? Promise.reject(new ApiError(404, { detail: 'Invalid page.' }))
        : Promise.resolve(page(['first'])),
    )
    const pagination = usePagination(() => undefined)
    pagination.page.value = 4
    expect(await pagination.fetchPage(request)).toEqual(['first'])
    expect(pagination.page.value).toBe(1)
  })

  it('passes other errors on', async () => {
    const pagination = usePagination(() => undefined)
    await expect(
      pagination.fetchPage(() => Promise.reject(new ApiError(500, null))),
    ).rejects.toBeInstanceOf(ApiError)
    expect(pagination.loading.value).toBe(false)
  })

  it('drops an answer that a newer request overtook', async () => {
    let resolveFirst!: (value: ReturnType<typeof page<string>>) => void
    const pagination = usePagination(() => undefined)
    const first = pagination.fetchPage(
      () => new Promise<ReturnType<typeof page<string>>>((r) => (resolveFirst = r)),
    )
    const second = await pagination.fetchPage(() => Promise.resolve(page(['new'])))
    resolveFirst(page(['old']))
    expect(await first).toBeNull()
    expect(second).toEqual(['new'])
  })

  it('reloads on page, size, sort and restored table state', () => {
    const load = vi.fn()
    const pagination = usePagination(load, 'name')
    pagination.onRestore({ page: 3, pageSize: 20, field: '', order: -1 })
    expect(load).not.toHaveBeenCalled() // not started yet
    expect([pagination.page.value, pagination.ordering.value]).toEqual([3, 'name'])
    void pagination.start()
    pagination.onPage({ page: 4, pageSize: 20 })
    expect(pagination.first.value).toBe(60)
    pagination.onPage({ page: 4, pageSize: 50 }) // a new page size starts over
    expect(pagination.page.value).toBe(1)
    pagination.onSort({ field: 'total', order: -1 })
    expect(pagination.ordering.value).toBe('-total')
    pagination.onRestore({ page: 0, pageSize: 10, field: 'number', order: 1 })
    expect([pagination.page.value, pagination.ordering.value]).toEqual([1, 'number'])
    pagination.refresh()
    expect(load).toHaveBeenCalledTimes(6)
  })
})

describe('money, numbers and durations', () => {
  async function show(component: object, props: Record<string, unknown>, settings = {}) {
    const pinia = createPinia()
    setActivePinia(pinia)
    useFormattingStore(pinia).apply(settings)
    const { wrapper } = await render(defineComponent({ setup: () => () => h(component, props) }), {
      pinia,
    })
    const text = screen.text()
    wrapper.unmount()
    return text
  }

  it('formats amounts the way the settings say', async () => {
    expect(await show(AppMoneyDisplay, { amount: 1234.5 })).toBe('1.234,50 €')
    expect(
      await show(
        AppMoneyDisplay,
        { amount: '1234.5', currency: 'USD' },
        {
          decimal_separator: '.',
          thousands_separator: ',',
          currency_position: 'before',
          currency_space: false,
        },
      ),
    ).toBe('$1,234.50')
    expect(
      await show(
        AppMoneyDisplay,
        { amount: 9, currency: '' },
        { currency: 'CHF', currency_display: 'code' },
      ),
    ).toBe('9,00 CHF')
  })

  it('shows a dash for missing or unreadable numbers', async () => {
    expect(await show(AppNumberDisplay, { value: null })).toBe('—')
    expect(await show(AppNumberDisplay, { value: 'abc' })).toBe('—')
    expect(await show(AppNumberDisplay, { value: 12.5, mode: 'percent' })).toBe('12,5%')
  })

  it('rounds durations to whole minutes before splitting hours', async () => {
    expect(await show(AppDurationDisplay, { minutes: 119.6 })).toBe('2:00 h')
    expect(await show(AppDurationDisplay, { minutes: null })).toBe('—')
  })

  it('shows dates, times and date-times in the configured format', async () => {
    const settings = { date_format: 'YYYY-MM-DD', time_format: 'h:mm A' }
    expect(await show(AppDateTimeDisplay, { value: '2026-11-02' }, settings)).toBe('2026-11-02')
    expect(await show(AppDateTimeDisplay, { value: '14:30', type: 'time' }, settings)).toBe(
      '2:30 PM',
    )
    expect(
      await show(AppDateTimeDisplay, { value: '2026-11-02T14:30:00+01:00', type: 'datetime' }),
    ).toBe('02.11.2026 14:30')
    expect(await show(AppDateTimeDisplay, { value: 'garbage' })).toBe('—')
  })

  it('falls back to the defaults for empty settings', () => {
    setActivePinia(createPinia())
    const formatting = useFormattingStore()
    formatting.apply({ date_format: '', currency: null, currency_space: false })
    expect([formatting.dateFormat, formatting.currency, formatting.currencySpace]).toEqual([
      'DD.MM.YYYY',
      'EUR',
      false,
    ])
  })

  it('loads the settings only once', async () => {
    setActivePinia(createPinia())
    const api = mockApi()
    api.get('/settings/', { currency: 'USD' })
    const formatting = useFormattingStore()
    await formatting.load()
    await formatting.load()
    expect(formatting.currency).toBe('USD')
    expect(api.requests('GET', '/settings/')).toHaveLength(1)
  })

  it('names currencies, and survives unknown codes', () => {
    document.documentElement.lang = 'de'
    expect(getCurrencyName('EUR')).toBe('Euro')
    expect(getCurrencySymbol('EUR')).toBe('€')
    expect(getCurrencyName('not a code')).toBe('not a code')
    expect(getCurrencySymbol('??')).toBe('??')
  })
})

describe('typed date inputs', () => {
  function host(component: object, initial: string | null) {
    const value = ref(initial)
    const Host = defineComponent({
      setup: () => () =>
        h('div', [
          h(component, {
            modelValue: value.value,
            'onUpdate:modelValue': (v: string | null) => (value.value = v),
          }),
          h('output', String(value.value)),
        ]),
    })
    return { Host, value }
  }
  const input = () => screen.root.querySelector<HTMLInputElement>('input')!

  it('reads a typed date on Enter, resets on Esc and clears when emptied', async () => {
    const { Host, value } = host(AppDateInput, '2026-11-02')
    await render(Host)
    expect(input().value).toBe('02.11.2026')
    await typeOnly(input(), '5')
    expect(screen.text()).toContain('→ 05.11.2026')
    input().dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await settle()
    expect(input().value).toBe('02.11.2026')
    await type(input(), 'heute')
    expect(value.value).toBe('2026-11-23')
    await type(input(), '')
    expect(value.value).toBeNull()
    await type(input(), '31.02.')
    expect(input().getAttribute('aria-invalid')).toBe('true')
    expect(value.value).toBeNull()
  })

  it('picks a date from the calendar', async () => {
    const { Host, value } = host(AppDateInput, '2026-11-02')
    await render(Host)
    await click(screen.button(t('time.pickDate')))
    const day = [...document.querySelectorAll('[data-pc-section="day"] span, td span')].find(
      (el) => el.textContent.trim() === '17',
    )!
    await click(day)
    expect(value.value).toBe('2026-11-17')
    expect(input().value).toBe('17.11.2026')
  })

  it('steps the hour and minute of a date-time with the mouse wheel', async () => {
    const start = new Date(2026, 10, 2, 18, 0).toISOString()
    const { Host, value } = host(AppDateTimeInput, start)
    await render(Host)
    await click(screen.button(t('time.pickDateTime')))
    const hour = document.querySelector('[data-pc-section="hourpicker"]')!
    hour.dispatchEvent(new WheelEvent('wheel', { deltaY: -100, bubbles: true, cancelable: true }))
    await settle()
    expect(input().value).toBe('02.11.2026 19:00')
    const minute = document.querySelector('[data-pc-section="minutepicker"]')!
    minute.dispatchEvent(new WheelEvent('wheel', { deltaY: 100, bubbles: true, cancelable: true }))
    await settle()
    expect(new Date(value.value!)).toEqual(new Date(2026, 10, 2, 18, 59))
  })

  it('clears a date-time and reads "jetzt"', async () => {
    const { Host, value } = host(AppDateTimeInput, null)
    await render(Host)
    await type(input(), 'jetzt')
    expect(new Date(value.value!)).toEqual(new Date(2026, 10, 23, 9, 15))
    await type(input(), ' ')
    expect(value.value).toBeNull()
  })
})

describe('AppCodeEditor', () => {
  it('edits the model, follows outside changes and inserts at the cursor', async () => {
    const value = ref('<p>Hi</p>')
    const editor = ref<InstanceType<typeof AppCodeEditor>>()
    const Host = defineComponent({
      setup: () => () =>
        h('div', [
          h(AppCodeEditor, {
            ref: editor,
            modelValue: value.value,
            language: 'css',
            'onUpdate:modelValue': (v: string) => (value.value = v),
          }),
        ]),
    })
    await render(Host)
    expect(screen.root.querySelector('.cm-content')!.textContent).toBe('<p>Hi</p>')
    value.value = 'body {}'
    await settle()
    expect(screen.root.querySelector('.cm-content')!.textContent).toBe('body {}')
    editor.value!.insert('/* x */')
    expect(value.value).toBe('/* x */body {}')
    // Switching to dark mode swaps the editor theme without losing the text.
    document.documentElement.classList.add('dark')
    await settle()
    document.documentElement.classList.remove('dark')
    expect(value.value).toBe('/* x */body {}')
  })
})

describe('InvoicePreviewFrame', () => {
  it('shows HTML in a sandbox and PDFs as they are', async () => {
    await render(
      defineComponent({ setup: () => () => h(InvoicePreviewFrame, { html: '<p>x</p>' }) }),
    )
    const frame = screen.root.querySelector('iframe')!
    expect(frame.getAttribute('sandbox')).toBe('allow-same-origin')
    expect(frame.getAttribute('srcdoc')).toBe('<p>x</p>')
    frame.dispatchEvent(new Event('load'))
    await render(
      defineComponent({
        setup: () => () => h(InvoicePreviewFrame, { url: 'blob:pdf', mode: 'pdf' }),
      }),
    )
    const pdf = screen.root.querySelectorAll('iframe')
    expect(pdf[pdf.length - 1]!.getAttribute('sandbox')).toBeNull()
  })
})
