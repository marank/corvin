import { describe, expect, it } from 'vitest'
import ProjectListView from '../views/projects/ProjectListView.vue'
import ProjectDetailView from '../views/projects/ProjectDetailView.vue'
import type { Project } from '../api'
import { mockApi, page, reply } from './helpers/api'
import { noAttachments, overview } from './helpers/backend'
import { answerConfirm, choose, click, dialog, screen, toasts, type } from './helpers/dom'
import { customer, project } from './helpers/fixtures'
import { render, t } from './helpers/render'

describe('ProjectListView', () => {
  function backend() {
    const api = mockApi()
    api.get(
      '/projects/',
      page([
        project({ used_hours: 8.5, budget_hours: 10, budget_hours_percent: 85 }),
        project({ id: 'prj-2', name: 'Shop', status: 'on_hold', used_hours: 1 }),
      ]),
    )
    api.get('/customers/', page([customer()]))
    api.get('/customers/cus-1/', customer())
    return api
  }
  const lastQuery = (api: ReturnType<typeof backend>) =>
    Object.fromEntries(api.requests('GET', '/projects/').at(-1)!.query)

  it('shows used hours against the budget', async () => {
    backend()
    await render(ProjectListView, { path: '/projects' })
    expect(screen.row('Website').textContent).toContain('8:30 h / 10:00 h')
    expect(screen.row('Website').querySelector('[title="85 %"]')).not.toBeNull()
    expect(screen.row('Shop').textContent).toContain(t('projects.status.on_hold'))
    expect(screen.row('Shop').textContent).not.toContain('/')
  })

  it("shows a customer's projects from the overview link", async () => {
    const api = backend()
    await render(ProjectListView, { path: '/projects', url: '/projects?customer=cus-1' })
    expect(lastQuery(api)).toMatchObject({ customer: 'cus-1', ordering: 'name' })
    expect(screen.text()).toContain(`${t('projects.customer')}: Acme GmbH`)
    await click(screen.root.querySelector('.p-chip [data-pc-section="removeicon"]')!)
    expect(lastQuery(api).customer).toBeUndefined()
  })

  it('filters by status', async () => {
    const api = backend()
    await render(ProjectListView, { path: '/projects' })
    await click(screen.button(t('common.filter')))
    await choose(screen.field(t('common.status')), t('projects.status.done'))
    expect(lastQuery(api).status).toBe('done')
  })

  it('creates a project for a customer', async () => {
    const api = backend()
    api.post('/projects/', (call) => project(call.body as Partial<Project>))
    await render(ProjectListView, { path: '/projects' })
    await click(screen.button(t('projects.new')))
    const modal = dialog(t('projects.new'))
    await choose(modal.field(t('projects.customer')), 'Acme GmbH')
    await type(modal.input(t('common.name')), 'Intranet')
    await type(modal.input(t('projects.budgetHours')), '40')
    await click(modal.button(t('common.save')))
    expect(api.lastBody('POST', '/projects/')).toEqual({
      status: 'active',
      customer: 'cus-1',
      name: 'Intranet',
      budget_hours: 40,
    })
    expect(toasts()).toContain(t('common.created'))
  })

  it('names the missing customer on its field', async () => {
    const api = backend()
    api.post('/projects/', reply(400, { customer: ['This field is required.'] }))
    await render(ProjectListView, { path: '/projects' })
    await click(screen.button(t('projects.new')))
    await click(dialog(t('projects.new')).button(t('common.save')))
    expect(dialog(t('projects.new')).fieldError(t('projects.customer'))).toBe(
      'This field is required.',
    )
  })

  it('shows status on phone cards', async () => {
    backend()
    await render(ProjectListView, { path: '/projects', viewport: 'mobile' })
    expect(screen.text()).toContain(`Shop${t('projects.status.on_hold')}Acme GmbH`)
  })
})

describe('ProjectDetailView', () => {
  function backend(p: Project = project()) {
    const api = mockApi()
    api.get('/projects/prj-1/', p)
    api.get('/customers/', page([customer(), customer({ id: 'cus-2', name: 'Beta AG' })]))
    overview(api, { total: 600 })
    noAttachments(api)
    return api
  }
  const open = () => render(ProjectDetailView, { path: '/projects/:id', url: '/projects/prj-1' })

  it('shows hours and amount against the budget, and the project totals', async () => {
    backend(
      project({
        used_hours: 9,
        budget_hours: 10,
        budget_hours_percent: 90,
        used_amount: 450,
        budget_amount: 1000,
        budget_amount_percent: 45,
      }),
    )
    await open()
    expect(screen.text()).toContain('P-001 · Acme GmbH')
    expect(screen.text()).toContain(`${t('projects.usedHours')}9:00 h / 10:00 h`)
    expect(screen.text()).toContain(`${t('projects.usedAmount')}450,00 € / 1.000,00 €`)
    expect(screen.text()).toContain(`${t('overview.totalHours')}10:00 h`)
    const [hours, amount] = screen.root.querySelectorAll('[role="progressbar"]')
    expect(hours!.getAttribute('aria-valuenow')).toBe('90')
    expect(amount!.getAttribute('aria-valuenow')).toBe('45')
  })

  it('starts an invoice for this project', async () => {
    backend()
    const { router } = await open()
    await click(screen.button(t('overview.createInvoice')))
    expect(router.currentRoute.value.fullPath).toBe('/invoices/new?customer=cus-1&project=prj-1')
  })

  it('saves the master data', async () => {
    const api = backend()
    api.put('/projects/prj-1/', (call) => project(call.body as Partial<Project>))
    await open()
    await click(screen.button(t('overview.masterData')))
    await choose(screen.field(t('common.status')), t('projects.status.on_hold'))
    await type(screen.input(t('projects.budgetAmount')), '2500')
    await click(screen.button(t('common.save')))
    expect(api.lastBody('PUT', '/projects/prj-1/')).toMatchObject({
      status: 'on_hold',
      budget_amount: 2500,
    })
    expect(toasts()).toContain(t('common.saved'))
  })

  it('keeps the browser from closing the tab over unsaved changes', async () => {
    backend()
    await open()
    const unload = () => {
      const event = new Event('beforeunload', { cancelable: true })
      window.dispatchEvent(event)
      return event.defaultPrevented
    }
    expect(unload()).toBe(false)
    await click(screen.button(t('overview.masterData')))
    await type(screen.input(t('common.name')), 'Relaunch')
    expect(unload()).toBe(true)
  })

  it('shows the API error on the field', async () => {
    const api = backend()
    api.put('/projects/prj-1/', reply(400, { name: ['Name taken.'] }))
    await open()
    await click(screen.button(t('overview.masterData')))
    await click(screen.button(t('common.save')))
    expect(screen.fieldError(t('common.name'))).toBe('Name taken.')
  })

  it('deletes the project after confirmation', async () => {
    const api = backend()
    api.delete('/projects/prj-1/')
    const { router } = await open()
    await click(screen.button(t('common.delete')))
    await answerConfirm(t('common.delete'))
    expect(router.currentRoute.value.path).toBe('/projects')
    expect(api.requests('DELETE', '/projects/prj-1/')).toHaveLength(1)
  })

  it('offers the way back when the project is gone', async () => {
    const api = mockApi()
    api.get('/projects/prj-1/', reply(404, {}))
    await open()
    expect(screen.text()).toContain(t('common.loadFailed'))
  })
})
