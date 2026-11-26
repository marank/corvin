import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TemplateListView from '../views/templates/TemplateListView.vue'
import InvoiceDesignerView from '../views/InvoiceDesignerView.vue'
import MailTemplateEditorView from '../views/templates/MailTemplateEditorView.vue'
import type { DocumentTemplate, MailTemplate, TextBlock } from '../api'
import { mockApi, page, reply } from './helpers/api'
import {
  activeTab,
  answerConfirm,
  choose,
  clearSelect,
  click,
  confirmText,
  dialog,
  screen,
  toasts,
  type,
} from './helpers/dom'
import { template } from './helpers/fixtures'
import { render, settle, t } from './helpers/render'
import { NOW } from './helpers/time'

const textBlock = (over: Partial<TextBlock> = {}): TextBlock => ({
  id: 'tb-1',
  name: 'Gruß',
  key: 'greeting',
  content: 'Mit freundlichen Grüßen',
  ...over,
})

const mailTemplate = (over: Partial<MailTemplate> = {}): MailTemplate => ({
  id: 'mt-2',
  name: 'Rechnung',
  subject: 'Rechnung {{ invoice.number }}',
  base: 'mt-1',
  html: '{% block inhalt %}<p>Anbei</p>{% endblock %}',
  slot_names: ['anrede', 'inhalt'],
  derived_count: 0,
  assigned_kinds: ['invoice'],
  created_at: '2026-01-01T10:00:00+01:00',
  updated_at: '2026-01-01T10:00:00+01:00',
  ...over,
})
const mailTemplates = [
  mailTemplate({
    id: 'mt-1',
    name: 'Standard-Layout',
    subject: '',
    base: null,
    html: '<p>{% block anrede %}Hallo{% endblock %}{% block inhalt %}{% endblock %}</p>',
    derived_count: 2,
    assigned_kinds: [],
  }),
  mailTemplate(),
  mailTemplate({
    id: 'mt-3',
    name: 'Zahlungserinnerung',
    assigned_kinds: ['payment_reminder'],
  }),
]

describe('TemplateListView', () => {
  const templates = [
    template({ id: 'tpl-2', name: 'Modern', created_at: '2026-05-01T10:00:00+02:00' }),
    template({ id: 'tpl-1', name: 'Klassisch', created_at: '2026-01-01T10:00:00+01:00' }),
  ]
  function backend(list: DocumentTemplate[] = templates) {
    const api = mockApi()
    api.get('/document-templates/', page(list))
    api.get('/mail-templates/', page(mailTemplates))
    api.get('/text-blocks/', page([textBlock()]))
    api.get('/settings/', {
      template_assignments: { invoice: 'tpl-2' },
      mail_template_assignments: { invoice: 'mt-2', payment_reminder: 'mt-3' },
    })
    return api
  }
  const open = () => render(TemplateListView, { path: '/templates' })

  it('assigns templates per document type and mail kind', async () => {
    const api = backend()
    api.put('/settings/', (call) => call.body)
    await open()
    expect(screen.field(t('designer.reportTypes.invoice')).textContent).toContain('Modern')
    expect(screen.field(t('designer.mailKinds.payment_reminder')).textContent).toContain(
      'Zahlungserinnerung',
    )
    await choose(screen.field(t('designer.reportTypes.quote')), 'Modern')
    await choose(screen.field(t('designer.mailKinds.payment_reminder')), 'Rechnung')
    await click(screen.button(t('common.save')))
    expect(api.lastBody('PUT', '/settings/')).toEqual({
      template_assignments: { invoice: 'tpl-2', quote: 'tpl-2' },
      mail_template_assignments: { invoice: 'mt-2', payment_reminder: 'mt-2' },
    })
    expect(toasts()).toContain(t('common.saved'))
  })

  it('lists the e-mail templates with base and use, and creates one on the layout', async () => {
    const api = backend()
    api.post('/mail-templates/', mailTemplate({ id: 'mt-9' }))
    const { router } = await open()
    await click(screen.button(t('designer.mailTemplates')))
    expect(activeTab().rows()).toContainEqual([
      'Rechnung',
      'Standard-Layout',
      t('designer.mailKinds.invoice'),
      '0',
      '',
    ])
    // Used ones stay: no delete button.
    expect(
      activeTab()
        .row('Standard-Layout')
        .querySelector(`[aria-label="${t('common.delete')}"]`),
    ).toBeNull()

    await click(screen.button(t('designer.newMailTemplate')))
    const modal = dialog(t('designer.newMailTemplate'))
    expect(modal.field(t('designer.mailBase')).textContent).toContain('Standard-Layout')
    await type(modal.input(t('common.name')), 'Mahnung')
    await click(modal.button(t('common.create')))
    expect(api.lastBody('POST', '/mail-templates/')).toEqual({ name: 'Mahnung', base: 'mt-1' })
    expect(router.currentRoute.value.path).toBe('/templates/mail/mt-9')
  })

  it('duplicates templates', async () => {
    const api = backend()
    api.post('/document-templates/tpl-2/duplicate/', template({ id: 'tpl-3' }))
    const { router } = await open()
    await click(screen.button(t('designer.templates')))
    await click(
      activeTab()
        .row('Modern')
        .querySelector(`[aria-label="${t('designer.duplicate')}"]`)!,
    )
    expect(router.currentRoute.value.path).toBe('/templates/tpl-3')
  })

  it('creates a template on confirm and opens it in the designer', async () => {
    const api = backend()
    api.post('/document-templates/', template({ id: 'tpl-9' }))
    const { router } = await open()
    await click(screen.button(t('designer.templates')))
    await click(screen.button(t('designer.newTemplate')))
    await type(dialog(t('designer.newTemplate')).input(t('common.name')), '  Winter  ')
    await click(dialog(t('designer.newTemplate')).button(t('common.create')))
    expect(api.lastBody('POST', '/document-templates/')).toEqual({ name: 'Winter', body_html: '' })
    expect(router.currentRoute.value.path).toBe('/templates/tpl-9')
  })

  it('exports each template and keeps the last one from being deleted', async () => {
    backend([template()])
    await open()
    await click(screen.button(t('designer.templates')))
    const row = activeTab().row('Standard')
    expect(
      row.querySelector(`[aria-label="${t('designer.exportTemplate')}"]`)!.getAttribute('href'),
    ).toBe('/api/v1/document-templates/tpl-1/export/')
    expect(row.querySelector(`[aria-label="${t('common.delete')}"]`)).toBeNull()
  })

  it('deletes a template', async () => {
    const api = backend()
    api.delete('/document-templates/tpl-2/')
    await open()
    await click(screen.button(t('designer.templates')))
    await click(
      activeTab()
        .row('Modern')
        .querySelector(`[aria-label="${t('common.delete')}"]`)!,
    )
    await answerConfirm(t('common.delete'))
    expect(api.requests('DELETE', '/document-templates/tpl-2/')).toHaveLength(1)
  })

  describe('import', () => {
    async function importFile(content: string) {
      const input = screen.root.querySelector<HTMLInputElement>(
        `input[aria-label="${t('designer.importTemplate')}"]`,
      )!
      Object.defineProperty(input, 'files', {
        value: [new File([content], 'tpl.json', { type: 'application/json' })],
        configurable: true,
      })
      input.dispatchEvent(new Event('change'))
      await settle()
    }

    it('imports a template file and opens it', async () => {
      const api = backend()
      api.post('/document-templates/import/', template({ id: 'tpl-imp' }))
      const { router } = await open()
      await click(screen.button(t('designer.templates')))
      await importFile('{"name": "Import", "body_html": "<p/>"}')
      expect(api.lastBody('POST', '/document-templates/import/')).toEqual({
        name: 'Import',
        body_html: '<p/>',
      })
      expect(toasts()).toContain(t('designer.importSuccess'))
      expect(router.currentRoute.value.path).toBe('/templates/tpl-imp')
    })

    it('refuses a file that is no JSON without calling the backend', async () => {
      const api = backend()
      const { router } = await open()
      await click(screen.button(t('designer.templates')))
      await importFile('not json')
      expect(api.requests('POST', '/document-templates/import/')).toHaveLength(0)
      expect(toasts()).toEqual([t('common.error')])
      expect(router.currentRoute.value.path).toBe('/templates')
    })
  })

  describe('text blocks', () => {
    it('adds a text block and shows a taken key on its field', async () => {
      const api = backend()
      api.post('/text-blocks/', reply(400, { key: ['A text block with this key exists.'] }))
      await open()
      await click(screen.button(t('designer.textBlocks')))
      await click(screen.button(t('designer.newTextBlock')))
      const modal = dialog(t('designer.textBlock'))
      await type(modal.input(t('common.name')), 'Gruß 2')
      await type(modal.input(t('designer.textBlockKey')), 'greeting')
      expect(modal.text()).toContain('{{ text_blocks.greeting }}')
      await type(modal.input(t('designer.textBlockContent')), 'Viele Grüße')
      await click(modal.button(t('common.save')))
      expect(api.lastBody('POST', '/text-blocks/')).toEqual({
        name: 'Gruß 2',
        key: 'greeting',
        content: 'Viele Grüße',
      })
      expect(dialog(t('designer.textBlock')).fieldError(t('designer.textBlockKey'))).toBe(
        'A text block with this key exists.',
      )
    })

    it('edits and deletes a text block', async () => {
      const api = backend()
      api.put('/text-blocks/tb-1/', (call) => call.body)
      api.delete('/text-blocks/tb-1/')
      await open()
      await click(screen.button(t('designer.textBlocks')))
      await click(activeTab().row('greeting'))
      await type(dialog(t('designer.textBlock')).input(t('designer.textBlockContent')), 'MfG')
      await click(dialog(t('designer.textBlock')).button(t('common.save')))
      expect(api.lastBody('PUT', '/text-blocks/tb-1/')).toMatchObject({ content: 'MfG' })

      await click(
        activeTab()
          .row('greeting')
          .querySelector(`[aria-label="${t('common.delete')}"]`)!,
      )
      await answerConfirm(t('common.delete'))
      expect(api.requests('DELETE', '/text-blocks/tb-1/')).toHaveLength(1)
    })
  })
})

describe('InvoiceDesignerView', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date', 'setTimeout', 'clearTimeout'], now: NOW })
    URL.createObjectURL = vi.fn(() => 'blob:preview')
    URL.revokeObjectURL = vi.fn()
  })
  afterEach(() => {
    // jsdom has neither; the PDF preview needs them.
    Reflect.deleteProperty(URL, 'createObjectURL')
    Reflect.deleteProperty(URL, 'revokeObjectURL')
  })

  function backend() {
    const api = mockApi()
    api.get('/document-templates/tpl-1/', template())
    api.get(
      '/company-images/',
      page([{ id: 'img', kind: 'additional', key: 'sig', name: 'Sig "A"', image: '', url: '' }]),
    )
    api.get('/text-blocks/', page([textBlock()]))
    api.post(
      '/document-templates/tpl-1/preview/',
      (call) => `<p>${(call.body as DocumentTemplate).name}</p>`,
    )
    api.post(
      '/document-templates/tpl-1/preview-pdf/',
      new Blob(['%PDF'], { type: 'application/pdf' }),
    )
    return api
  }
  async function open() {
    const view = await render(InvoiceDesignerView, {
      path: '/templates/:id',
      url: '/templates/tpl-1',
    })
    await vi.advanceTimersByTimeAsync(400)
    await settle()
    return view
  }
  const previewFrame = () => screen.root.querySelector<HTMLIFrameElement>('iframe')!
  const exportButton = () => screen.button(t('designer.exportTemplate'))

  it('previews the template as it is being edited, without saving it', async () => {
    const api = backend()
    await open()
    expect(previewFrame().getAttribute('srcdoc')).toBe('<p>Standard</p>')
    expect(previewFrame().getAttribute('sandbox')).toBe('allow-same-origin')

    await type(screen.input(t('designer.templateName')), 'Winter')
    expect(api.requests('POST', '/document-templates/tpl-1/preview/')).toHaveLength(1)
    await vi.advanceTimersByTimeAsync(400)
    await settle()
    expect(api.lastBody('POST', '/document-templates/tpl-1/preview/')).toMatchObject({
      name: 'Winter',
    })
    expect(previewFrame().getAttribute('srcdoc')).toBe('<p>Winter</p>')
    expect(api.requests('PUT', '/document-templates/tpl-1/')).toHaveLength(0)
  })

  it('keeps the last good preview and says why the new one failed', async () => {
    const api = backend()
    await open()
    api.post('/document-templates/tpl-1/preview/', reply(400, { detail: "Unclosed tag 'for'." }))
    await type(screen.input(t('designer.templateName')), 'Kaputt')
    await vi.advanceTimersByTimeAsync(400)
    await settle()
    expect(screen.text()).toContain(t('designer.previewStale', { error: "Unclosed tag 'for'." }))
    expect(previewFrame().getAttribute('srcdoc')).toBe('<p>Standard</p>')
  })

  it('switches to a PDF preview', async () => {
    const api = backend()
    await open()
    await click(screen.button('PDF'))
    expect(api.requests('POST', '/document-templates/tpl-1/preview-pdf/')).toHaveLength(1)
    expect(previewFrame().getAttribute('src')).toBe('blob:preview')
  })

  it('exports only the saved state', async () => {
    const api = backend()
    api.put('/document-templates/tpl-1/', (call) => call.body)
    await open()
    expect(exportButton().hasAttribute('disabled')).toBe(false)
    await type(screen.input(t('designer.primaryFont')), 'Lato')
    expect(exportButton().hasAttribute('disabled')).toBe(true)
    await click(screen.button(t('common.save')))
    expect(api.lastBody('PUT', '/document-templates/tpl-1/')).toMatchObject({
      primary_font: 'Lato',
    })
    expect(exportButton().hasAttribute('disabled')).toBe(false)
  })

  it('inserts a placeholder into the open HTML editor', async () => {
    const api = backend()
    api.put('/document-templates/tpl-1/', (call) => call.body)
    await open()
    await click(screen.button(t('designer.headerHtml')))
    await click(screen.button('company_name'))
    await click(screen.button(t('common.save')))
    expect(api.lastBody('PUT', '/document-templates/tpl-1/')).toMatchObject({
      header_html: '{{ company.company_name }}',
    })
  })

  it('offers text blocks and images, with the image name escaped', async () => {
    backend()
    await open()
    expect(screen.button('Gruß (greeting)').getAttribute('title')).toBe(
      '{{ text_blocks.greeting }}',
    )
    expect(screen.button('Sig "A"').getAttribute('title')).toBe(
      '<img src="{{ images.sig }}" alt="Sig &quot;A&quot;">',
    )
  })

  it('saves the room for header and footer', async () => {
    const api = backend()
    api.put('/document-templates/tpl-1/', (call) => call.body)
    await open()
    expect(screen.text()).toContain(t('designer.marginsHint').slice(0, 30))
    await type(screen.input(t('designer.headerHeight')), '24')
    await type(screen.input(t('designer.footerHeight')), '28')
    await click(screen.button(t('common.save')))
    expect(api.lastBody('PUT', '/document-templates/tpl-1/')).toMatchObject({
      header_height: 24,
      footer_height: 28,
    })
  })

  it('shows save errors on the field', async () => {
    const api = backend()
    api.put(
      '/document-templates/tpl-1/',
      reply(400, { margin_top: ['Ensure this value is greater than or equal to 0.'] }),
    )
    await open()
    await click(screen.button(t('common.save')))
    expect(screen.fieldError(t('designer.marginTop'))).toBe(
      'Ensure this value is greater than or equal to 0.',
    )
  })

  it('deletes the template without asking about unsaved changes', async () => {
    const api = backend()
    api.delete('/document-templates/tpl-1/')
    const { router } = await open()
    await type(screen.input(t('designer.templateName')), 'Weg damit')
    await click(screen.button(t('common.delete')))
    await answerConfirm(t('common.delete'))
    expect(router.currentRoute.value.path).toBe('/templates')
    expect(confirmText()).toBe('')
  })
})

describe('MailTemplateEditorView', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date', 'setTimeout', 'clearTimeout'], now: NOW })
  })

  function backend(own: MailTemplate = mailTemplate()) {
    const api = mockApi()
    api.get(`/mail-templates/${own.id}/`, own)
    api.get('/mail-templates/', page([...mailTemplates, own]))
    api.get('/company-images/', page([]))
    api.get('/text-blocks/', page([textBlock()]))
    api.post(`/mail-templates/${own.id}/preview/`, (call) => {
      const body = call.body as MailTemplate
      return { subject: `S: ${body.subject}`, html: `<pre>${body.html}</pre>` }
    })
    return api
  }
  async function open(id = 'mt-2') {
    const view = await render(MailTemplateEditorView, {
      path: '/templates/mail/:id',
      url: `/templates/mail/${id}`,
    })
    await vi.advanceTimersByTimeAsync(400)
    await settle()
    return view
  }
  async function waitForPreview() {
    await vi.advanceTimersByTimeAsync(400)
    await settle()
  }

  it('edits one HTML and previews the unsaved state', async () => {
    const api = backend()
    await open()
    expect(screen.hasButton(t('designer.mailHtml'))).toBe(true)
    expect(screen.hasButton('inhalt')).toBe(false)
    expect(screen.root.querySelector('iframe')!.getAttribute('srcdoc')).toBe(
      '<pre>{% block inhalt %}<p>Anbei</p>{% endblock %}</pre>',
    )

    await type(screen.input(t('designer.mailSubject')), 'Neu {{ invoice.number }}')
    await waitForPreview()
    expect(api.lastBody('POST', '/mail-templates/mt-2/preview/')).toEqual({
      name: 'Rechnung',
      subject: 'Neu {{ invoice.number }}',
      base: 'mt-1',
      html: '{% block inhalt %}<p>Anbei</p>{% endblock %}',
    })
    expect(screen.text()).toContain('S: Neu {{ invoice.number }}')
  })

  it("writes out the base's blocks when an empty template gets a base", async () => {
    const api = backend(mailTemplate({ id: 'mt-9', name: 'Neu', base: null, html: '' }))
    await open('mt-9')
    await choose(screen.field(t('designer.mailBase')), 'Standard-Layout')
    await waitForPreview()
    expect(api.lastBody('POST', '/mail-templates/mt-9/preview/')).toMatchObject({
      base: 'mt-1',
      html:
        '{% block anrede %}{{ block.super }}{% endblock %}\n\n' +
        '{% block inhalt %}{{ block.super }}{% endblock %}',
    })
  })

  it('keeps written HTML when the base changes', async () => {
    const api = backend()
    await open()
    await clearSelect(screen.field(t('designer.mailBase')))
    await waitForPreview()
    expect(api.lastBody('POST', '/mail-templates/mt-2/preview/')).toMatchObject({
      base: null,
      html: '{% block inhalt %}<p>Anbei</p>{% endblock %}',
    })
  })

  it('saves, and keeps a base of others from being deleted', async () => {
    const api = backend(mailTemplates[0])
    api.put('/mail-templates/mt-1/', (call) => ({ ...mailTemplates[0], ...(call.body as object) }))
    await open('mt-1')
    expect(screen.hasButton(t('common.delete'))).toBe(false)
    await type(screen.input(t('designer.templateName')), 'Rahmen')
    await click(screen.button(t('common.save')))
    expect(api.lastBody('PUT', '/mail-templates/mt-1/')).toMatchObject({
      name: 'Rahmen',
      base: null,
    })
    expect(toasts()).toContain(t('common.saved'))
  })
})
