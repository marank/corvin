import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h, type PropType } from 'vue'
import DashboardView from '../views/DashboardView.vue'
import TasksView from '../views/TasksView.vue'
import type { Task } from '../api'
import { mockApi, page, reply } from './helpers/api'
import { pickers } from './helpers/backend'
import { answerConfirm, choose, click, dialog, screen, toasts, type } from './helpers/dom'
import { task } from './helpers/fixtures'
import { render, t } from './helpers/render'

// jsdom has no canvas: the chart shows the data it was given as text instead.
const Chart = defineComponent({
  props: {
    type: { type: String, required: true },
    data: {
      type: Object as PropType<{ labels: string[]; datasets: { data: number[] }[] }>,
      required: true,
    },
  },
  setup: (props) => () =>
    h(
      'figure',
      { 'data-chart': props.type },
      `${props.data.labels.join(',')}=${props.data.datasets[0]!.data.join(',')}`,
    ),
})

describe('DashboardView', () => {
  const stats = {
    revenue_by_month: [
      { month: '2026-10-01', total: 1200 },
      { month: '2026-11-01', total: 0 },
    ],
    hours_by_customer: [
      { customer__name: 'Acme GmbH', hours: 12 },
      { customer__name: null, hours: 2 },
    ],
    uninvoiced_hours: 7.5,
    week_hours: 31.25,
    open_invoices: { total: 2380, count: 3 },
    overdue: { total: 238, count: 1 },
    contracts: [
      {
        id: 4,
        name: 'Wartung',
        period_start: '2026-11-01',
        period_end: '2026-11-30',
        used_hours: 3,
        included_hours: 10,
        overage_hours: 0,
      },
    ],
    budget_warnings: [
      {
        id: 9,
        name: 'Relaunch',
        customer: 'Acme GmbH',
        budget_hours_percent: 130,
        budget_amount_percent: null,
      },
    ],
    timer_running: null,
  }
  const open = () => render(DashboardView, { stubs: { Chart } })

  it('shows the key figures, each linking to its list', async () => {
    mockApi().get('/stats/dashboard', stats)
    await open()
    const kpi = (label: string) => screen.button(new RegExp(`^${label}`))
    expect(kpi(t('dashboard.weekHours')).textContent).toContain('31:15 h')
    expect(kpi(t('dashboard.weekHours')).getAttribute('href')).toBe('/time?from=2026-11-23')
    expect(kpi(t('dashboard.uninvoiced')).getAttribute('href')).toBe('/time?status=open')
    expect(kpi(t('dashboard.openInvoices')).textContent).toContain('2.380,00 €')
    expect(kpi(t('dashboard.openInvoices')).textContent).toContain(
      t('dashboard.invoiceCount', { n: 3 }, 3),
    )
    expect(kpi(t('dashboard.overdue')).getAttribute('href')).toBe('/invoices?receivable=overdue')
    expect(kpi(t('dashboard.overdue')).textContent).toContain(
      t('dashboard.invoiceCount', { n: 1 }, 1),
    )
  })

  it("links the week's hours to this week's Monday, also on a Sunday", async () => {
    vi.setSystemTime(new Date(2026, 10, 29, 20, 0))
    mockApi().get('/stats/dashboard', stats)
    await open()
    expect(screen.button(new RegExp(`^${t('dashboard.weekHours')}`)).getAttribute('href')).toBe(
      '/time?from=2026-11-23',
    )
  })

  it('charts revenue per month and hours per customer', async () => {
    mockApi().get('/stats/dashboard', stats)
    await open()
    expect(screen.root.querySelector('[data-chart="bar"]')!.textContent).toMatch(
      /^Okt\.? 2026,Nov\.? 2026=1200,0$/,
    )
    expect(screen.root.querySelector('[data-chart="doughnut"]')!.textContent).toBe(
      `Acme GmbH,${t('dashboard.noCustomer')}=12,2`,
    )
  })

  it('shows empty states instead of empty charts', async () => {
    mockApi().get('/stats/dashboard', {
      ...stats,
      revenue_by_month: [{ month: '2026-11-01', total: 0 }],
      hours_by_customer: [],
      contracts: [],
      budget_warnings: [],
    })
    await open()
    expect(screen.root.querySelector('figure')).toBeNull()
    expect(screen.text()).toContain(t('dashboard.noRevenue'))
    expect(screen.text()).toContain(t('dashboard.noHours'))
    expect(screen.text()).not.toContain(t('dashboard.budgetWarnings'))
  })

  it('warns about projects over budget and shows contract usage', async () => {
    mockApi().get('/stats/dashboard', stats)
    await open()
    expect(screen.button('Relaunch').getAttribute('href')).toBe('/projects/9')
    const bars = screen.root.querySelectorAll('[role="progressbar"]')
    expect(bars[0]!.getAttribute('aria-valuenow')).toBe('100')
    expect(screen.button('Wartung').getAttribute('href')).toBe('/contracts/4')
    expect(screen.text()).toContain(`${t('contracts.used')}: 3:00 h`)
  })

  it('reports when the figures cannot be loaded', async () => {
    mockApi().get('/stats/dashboard', reply(500, 'boom'))
    await open()
    expect(toasts()).toEqual([t('common.error')])
  })
})

describe('TasksView', () => {
  function backend(tasks: Task[]) {
    const api = pickers(mockApi())
    api.get('/tasks/', page(tasks))
    return api
  }
  const tasks = [
    task({ id: 't1', title: 'Backup prüfen', due_date: '2026-11-20', priority: 'high' }),
    task({
      id: 't2',
      number: 'A-002',
      title: 'Rechnung schreiben',
      due_date: '2026-11-20',
      status: 'done',
    }),
    task({ id: 't3', number: 'A-003', title: 'Server tauschen', due_date: '2026-11-30' }),
  ]

  it('marks open tasks past their due date', async () => {
    const api = backend(tasks)
    await render(TasksView, { path: '/tasks' })
    expect(api.requests('GET', '/tasks/')[0]!.query.get('ordering')).toBe('position')
    const due = (title: string) => screen.row(title).querySelector('.text-danger')
    expect(due('Backup prüfen')).not.toBeNull()
    expect(due('Rechnung schreiben')).toBeNull()
    expect(due('Server tauschen')).toBeNull()
    expect(screen.row('Backup prüfen').textContent).toContain(t('tasks.priorities.high'))
  })

  it('ticks a task off right away', async () => {
    const api = backend(tasks)
    api.patch('/tasks/t1/', (call) => call.body)
    await render(TasksView, { path: '/tasks' })
    await click(screen.row('Backup prüfen').querySelector(`[aria-label="${t('tasks.markDone')}"]`)!)
    expect(api.lastBody('PATCH', '/tasks/t1/')).toEqual({ status: 'done' })
    expect(screen.row('Backup prüfen').textContent).toContain(t('tasks.status.done'))
  })

  it('puts the task back when ticking it off fails', async () => {
    const api = backend(tasks)
    api.patch('/tasks/t2/', reply(403, { detail: 'Forbidden.' }))
    await render(TasksView, { path: '/tasks' })
    await click(
      screen.row('Rechnung schreiben').querySelector(`[aria-label="${t('tasks.reopen')}"]`)!,
    )
    expect(screen.row('Rechnung schreiben').textContent).toContain(t('tasks.status.done'))
    expect(toasts().join()).toContain('Forbidden.')
  })

  it('creates a task with due date and priority', async () => {
    const api = backend([])
    api.post('/tasks/', (call) => call.body)
    await render(TasksView, { path: '/tasks' })
    await click(screen.button(t('tasks.new')))
    const modal = dialog(t('tasks.new'))
    await type(modal.input(t('tasks.task')), 'Firewall prüfen')
    await choose(modal.field(t('projects.customer')), 'Beta AG')
    await type(modal.input(t('tasks.dueDate')), '27')
    await choose(modal.field(t('tasks.priority')), t('tasks.priorities.high'))
    await click(modal.button(t('common.save')))
    expect(api.lastBody('POST', '/tasks/')).toEqual({
      title: 'Firewall prüfen',
      customer: 'cus-2',
      due_date: '2026-11-27',
      priority: 'high',
      status: 'open',
    })
  })

  it('edits a task', async () => {
    const api = backend(tasks)
    api.put('/tasks/t3/', (call) => call.body)
    await render(TasksView, { path: '/tasks' })
    await click(screen.row('Server tauschen'))
    const modal = dialog(`${t('tasks.edit')} · A-003`)
    await choose(modal.field(t('common.status')), t('tasks.status.in_progress'))
    // The description is Markdown, on its own tab.
    await click(modal.button(t('time.description')))
    await type(
      modal.root.querySelector<HTMLTextAreaElement>(
        `textarea[aria-label="${t('time.description')}"]`,
      )!,
      '- alten Server abbauen',
    )
    await click(modal.button(t('common.save')))
    expect(api.lastBody('PUT', '/tasks/t3/')).toMatchObject({
      id: 't3',
      status: 'in_progress',
      description: '- alten Server abbauen',
    })
  })

  it('filters by priority', async () => {
    const api = backend(tasks)
    await render(TasksView, { path: '/tasks', url: '/tasks?customer=cus-1' })
    await click(screen.button(/^Filter/))
    await choose(screen.field(t('tasks.priority')), t('tasks.priorities.low'))
    expect(Object.fromEntries(api.requests('GET', '/tasks/').at(-1)!.query)).toMatchObject({
      customer: 'cus-1',
      priority: 'low',
    })
  })

  it('deletes a task', async () => {
    const api = backend(tasks)
    api.delete('/tasks/t3/')
    await render(TasksView, { path: '/tasks' })
    await click(
      screen.row('Server tauschen').querySelector(`[aria-label="${t('common.delete')}"]`)!,
    )
    await answerConfirm(t('common.delete'))
    expect(api.requests('DELETE', '/tasks/t3/')).toHaveLength(1)
  })

  it('ticks tasks off on a phone, too', async () => {
    const api = backend(tasks)
    api.patch('/tasks/t3/', (call) => call.body)
    await render(TasksView, { path: '/tasks', viewport: 'mobile' })
    const buttons = screen.buttons(t('tasks.markDone'))
    await click(buttons[1]!)
    expect(api.lastBody('PATCH', '/tasks/t3/')).toEqual({ status: 'done' })
  })
})
