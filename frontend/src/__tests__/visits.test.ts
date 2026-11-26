import { describe, expect, it } from 'vitest'
import VisitListView from '../views/visits/VisitListView.vue'
import VisitDetailView from '../views/visits/VisitDetailView.vue'
import type { Attachment } from '../api'
import { mockApi, page, reply } from './helpers/api'
import { pickers } from './helpers/backend'
import {
  activeTab,
  answerConfirm,
  choose,
  click,
  confirmText,
  dialog,
  screen,
  toasts,
  type,
} from './helpers/dom'
import { customer, timeEntry, visit } from './helpers/fixtures'
import { render, settle, t } from './helpers/render'

describe('VisitListView', () => {
  function backend() {
    const api = pickers(mockApi())
    api.get(
      '/visits/',
      page([visit(), visit({ id: 'vis-2', customer_name: 'Beta AG', location: 'Potsdam' })]),
    )
    api.get('/customers/cus-1/', customer())
    return api
  }

  it('lists the latest visits first', async () => {
    const api = backend()
    await render(VisitListView, { path: '/visits' })
    expect(api.requests('GET', '/visits/')[0]!.query.get('ordering')).toBe('-date')
    expect(screen.rows()[0]).toEqual([
      'B-001',
      '20.11.2026',
      '09:00–12:00',
      'Acme GmbH',
      '',
      'Berlin',
      '',
    ])
  })

  it("narrows to a customer's visits from the overview link", async () => {
    const api = backend()
    await render(VisitListView, { path: '/visits', url: '/visits?customer=cus-1' })
    expect(api.requests('GET', '/visits/').at(-1)!.query.get('customer')).toBe('cus-1')
    await click(screen.button(/^Filter/))
    await click(screen.button(t('common.clearFilters')))
    expect(api.requests('GET', '/visits/').at(-1)!.query.get('customer')).toBeNull()
  })

  it('records a visit for today', async () => {
    const api = backend()
    api.post('/visits/', (call) => call.body)
    await render(VisitListView, { path: '/visits' })
    await click(screen.button(t('visits.new')))
    const modal = dialog(t('visits.new'))
    expect(modal.input(t('common.date')).value).toBe('23.11.2026')
    await choose(modal.field(t('projects.customer')), 'Acme GmbH')
    await type(modal.input(t('visits.arrival')), '08:30')
    await type(modal.input(t('visits.location')), 'Serverraum')
    await click(modal.button(t('common.save')))
    expect(api.lastBody('POST', '/visits/')).toEqual({
      date: '2026-11-23',
      customer: 'cus-1',
      arrival: '08:30',
      location: 'Serverraum',
    })
    expect(toasts()).toContain(t('common.created'))
  })

  it('shows a missing customer on its field', async () => {
    const api = backend()
    api.post('/visits/', reply(400, { customer: ['This field is required.'] }))
    await render(VisitListView, { path: '/visits' })
    await click(screen.button(t('visits.new')))
    await click(dialog(t('visits.new')).button(t('common.save')))
    expect(dialog(t('visits.new')).fieldError(t('projects.customer'))).toBe(
      'This field is required.',
    )
  })

  it('opens a visit', async () => {
    backend()
    const { router } = await render(VisitListView, { path: '/visits' })
    await click(screen.row('Potsdam'))
    expect(router.currentRoute.value.path).toBe('/visits/vis-2')
  })

  it('shows date and place on phone cards', async () => {
    backend()
    await render(VisitListView, { path: '/visits', viewport: 'mobile' })
    expect(screen.text()).toContain('Beta AG20.11.2026 · Potsdam')
  })
})

/** The report's Markdown editor (on its tab). */
const reportText = () =>
  screen.root.querySelector<HTMLTextAreaElement>(`textarea[aria-label="${t('visits.report')}"]`)!

describe('VisitDetailView', () => {
  const attachment = (over: Partial<Attachment> = {}): Attachment => ({
    id: 'att-1',
    file: 'report.pdf',
    url: '/api/v1/attachments/att-1/file/',
    name: 'report.pdf',
    uploaded_at: '2026-11-20T12:00:00+01:00',
    content_type: 4,
    object_id: 'vis-1',
    ...over,
  })

  function backend(attachments: Attachment[] = []) {
    const api = pickers(mockApi())
    const state = { attachments }
    api.get('/visits/vis-1/', visit())
    api.get(
      '/time-tracking/',
      page([timeEntry({ description: 'Router getauscht', visit: 'vis-1' })]),
    )
    api.get('/attachments/content_types/', { onsitevisit: 4 })
    api.get('/attachments/', () => page(state.attachments))
    return { api, state }
  }
  const open = () => render(VisitDetailView, { path: '/visits/:id', url: '/visits/vis-1' })

  it('shows the visit with its time entries', async () => {
    const { api } = backend()
    await open()
    expect(screen.text()).toContain('Acme GmbH — 20.11.2026')
    expect(screen.text()).toContain('B-001 · Berlin')
    expect(screen.input(t('visits.arrival')).value).toBe('09:00')
    expect(activeTab('last').row('Router getauscht').textContent).toContain('2:00 h')
    expect(api.requests('GET', '/time-tracking/')[0]!.query.get('visit')).toBe('vis-1')
  })

  it('saves the report', async () => {
    const { api } = backend()
    api.put('/visits/vis-1/', (call) => call.body)
    await open()
    await click(screen.button(t('visits.report')))
    await type(reportText(), 'Switch ersetzt.')
    await click(screen.button(t('common.save')))
    expect(api.lastBody('PUT', '/visits/vis-1/')).toMatchObject({ notes: 'Switch ersetzt.' })
    expect(toasts()).toContain(t('common.saved'))
  })

  it('asks before leaving an unsaved report', async () => {
    backend()
    const { router } = await open()
    await click(screen.button(t('visits.report')))
    await type(reportText(), 'Halb fertig')
    await click(screen.button(t('nav.visits')))
    expect(confirmText()).toContain(t('common.unsavedMessage'))
    await answerConfirm(t('common.keepEditing'))
    expect(router.currentRoute.value.path).toBe('/visits/vis-1')
  })

  it('uploads attachments and deletes them', async () => {
    const { api, state } = backend()
    api.post('/attachments/', (call) => {
      const form = call.body as FormData
      state.attachments = [attachment({ name: (form.get('file') as File).name })]
      return state.attachments[0]
    })
    api.delete('/attachments/att-1/', () => {
      state.attachments = []
      return reply(204)
    })
    await open()
    await click(screen.button(t('customers.attachments')))
    const input = activeTab('last').root.querySelector<HTMLInputElement>('input[type=file]')!
    Object.defineProperty(input, 'files', {
      value: [new File(['%PDF'], 'report.pdf', { type: 'application/pdf' })],
    })
    input.dispatchEvent(new Event('change'))
    await settle()

    const sent = api.lastBody('POST', '/attachments/') as FormData
    expect([sent.get('content_type'), sent.get('object_id')]).toEqual(['4', 'vis-1'])
    expect(api.requests('POST', '/attachments/')[0]!.headers['Content-Type']).toBeUndefined()
    expect(toasts()).toContain(t('common.uploaded'))
    expect(activeTab('last').button('report.pdf').getAttribute('href')).toBe(
      '/api/v1/attachments/att-1/file/',
    )

    await click(activeTab('last').button(t('common.delete')))
    await answerConfirm(t('common.delete'))
    expect(activeTab('last').text()).toContain(t('common.empty'))
  })

  it('reports a failed upload', async () => {
    const { api } = backend()
    api.post('/attachments/', reply(413, 'Request Entity Too Large'))
    await open()
    await click(screen.button(t('customers.attachments')))
    const input = activeTab('last').root.querySelector<HTMLInputElement>('input[type=file]')!
    Object.defineProperty(input, 'files', { value: [new File(['x'], 'huge.iso')] })
    input.dispatchEvent(new Event('change'))
    await settle()
    expect(toasts()).toEqual([t('common.error')])
  })

  it('deletes the visit', async () => {
    const { api } = backend()
    api.delete('/visits/vis-1/')
    const { router } = await open()
    await click(screen.button(t('common.delete')))
    await answerConfirm(t('common.delete'))
    expect(router.currentRoute.value.path).toBe('/visits')
  })

  it('offers the way back when the visit is gone', async () => {
    mockApi().get('/visits/vis-1/', reply(404, {}))
    await open()
    expect(screen.text()).toContain(t('common.loadFailed'))
  })
})
