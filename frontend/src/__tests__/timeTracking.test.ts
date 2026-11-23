import { describe, expect, it } from 'vitest'
import TimeTrackingView from '../views/TimeTrackingView.vue'
import type { TimeEntry } from '../api'
import { mockApi, page, reply } from './helpers/api'
import {
  answerConfirm,
  choose,
  click,
  dialog,
  isDialogOpen,
  pressEnter,
  screen,
  type,
  typeOnly,
} from './helpers/dom'
import { contract, customer, project, runningEntry, timeEntry } from './helpers/fixtures'
import { render, t } from './helpers/render'

const entries = [
  timeEntry({ id: 'te-1', description: 'Homepage', duration_minutes: 120 }),
  timeEntry({
    id: 'te-2',
    description: 'Review',
    start_datetime: '2026-11-20T14:00:00+01:00',
    end_datetime: '2026-11-20T14:30:00+01:00',
    duration_minutes: 30,
    invoice: 'inv-1',
  }),
  timeEntry({
    id: 'te-3',
    description: 'Hosting',
    start_datetime: '2026-11-19T09:00:00+01:00',
    end_datetime: '2026-11-19T10:00:00+01:00',
    duration_minutes: 60,
    billable: false,
  }),
]

function backend(
  running: ReturnType<typeof runningEntry> | null = null,
  list: TimeEntry[] = entries,
) {
  const api = mockApi()
  api.get('/time-tracking/', page(list))
  api.get('/time-tracking/summary/', { count: list.length, total_minutes: 210 })
  // The backend's timer: stop, pause and resume change what /active/ returns.
  const timer = { running }
  api.get('/time-tracking/active/', () => timer.running)
  api.post('/time-tracking/stop/', () => {
    timer.running = null
    return timeEntry({ id: 'te-run' })
  })
  api.post('/time-tracking/pause/', () => (timer.running = runningEntry({ is_paused: true })))
  api.post('/time-tracking/resume/', () => (timer.running = runningEntry()))
  api.get('/settings/', {})
  api.get('/customers/', page([customer(), customer({ id: 'cus-2', name: 'Beta AG' })]))
  api.get('/customers/cus-1/', customer())
  api.get('/projects/', page([project()]))
  api.get('/support-contracts/', page([]))
  return api
}

const open = (url = '/time') => render(TimeTrackingView, { path: '/time', url })
const lastQuery = (api: ReturnType<typeof backend>) =>
  Object.fromEntries(api.requests('GET', '/time-tracking/').at(-1)!.query)

describe('TimeTrackingView', () => {
  describe('the list', () => {
    it('groups the newest entries by day with the day total', async () => {
      const api = backend()
      await open()
      expect(lastQuery(api)).toEqual({ page: '1', page_size: '50', ordering: '-start_datetime' })
      const text = screen.text()
      expect(text).toMatch(/Fr\.?, 20\.11\.2026 ?2:30 h/)
      expect(text).toMatch(/Do\.?, 19\.11\.2026 ?1:00 h/)
      expect(text).toContain(`${t('time.entries', 3)} · 3:30 h`)
    })

    it('marks invoiced entries and does not offer to delete them', async () => {
      backend()
      await open()
      expect(screen.row('Review').textContent).toContain(t('time.invoiced'))
      expect(screen.row('Review').querySelector('button')).toBeNull()
      expect(screen.row('Homepage').querySelector('button')).not.toBeNull()
    })

    it('shows uninvoiced work of this week from the dashboard link', async () => {
      const api = backend()
      await open('/time?status=open&from=2026-11-23')
      expect(lastQuery(api)).toMatchObject({
        invoice__isnull: 'true',
        start_datetime__date__gte: '2026-11-23',
      })
      expect(
        api.requests('GET', '/time-tracking/summary/').at(-1)!.query.get('invoice__isnull'),
      ).toBe('true')
      expect(screen.text()).toContain(`${t('time.period')}: 23.11.2026 – …`)
      expect(screen.text()).toContain(`${t('common.status')}: ${t('time.statuses.open')}`)
    })

    it('filters by period and removes the period chip as one', async () => {
      const api = backend()
      await open()
      await click(screen.button(t('common.filter')))
      await type(screen.input(t('time.period')), '1.11.')
      const to = screen.field(t('time.period')).querySelectorAll('input')[1]!
      await type(to, '30.11.')
      expect(lastQuery(api)).toMatchObject({
        start_datetime__date__gte: '2026-11-01',
        start_datetime__date__lte: '2026-11-30',
      })
      await click(screen.root.querySelector('.p-chip [data-pc-section="removeicon"]')!)
      expect(lastQuery(api).start_datetime__date__gte).toBeUndefined()
      expect(lastQuery(api).start_datetime__date__lte).toBeUndefined()
    })

    it("shows a project's entries from its overview link", async () => {
      const api = backend()
      api.get('/projects/prj-1/', project())
      await open('/time?project=prj-1')
      expect(lastQuery(api).project).toBe('prj-1')
      expect(screen.text()).toContain(`${t('projects.project')}: Website`)
    })

    it('filters invoiced entries', async () => {
      const api = backend()
      await open()
      await click(screen.button(t('common.filter')))
      await choose(screen.field(t('common.status')), t('time.statuses.invoiced'))
      expect(lastQuery(api).invoice__isnull).toBe('false')
    })

    it('deletes an entry after confirmation and reloads', async () => {
      const api = backend()
      api.delete('/time-tracking/te-1/')
      await open()
      await click(screen.row('Homepage').querySelector('button')!)
      await answerConfirm(t('common.delete'))
      expect(api.requests('DELETE', '/time-tracking/te-1/')).toHaveLength(1)
      expect(api.requests('GET', '/time-tracking/').length).toBeGreaterThan(1)
    })

    it('shows a running entry as running instead of its duration', async () => {
      backend(null, [timeEntry({ is_running: true, end_datetime: null, description: 'Now' })])
      await open()
      expect(screen.row('Now').textContent).toContain(t('time.timerRunning'))
    })

    it('shows cards on a phone', async () => {
      backend()
      await render(TimeTrackingView, { path: '/time', viewport: 'mobile' })
      expect(screen.text()).toContain('Homepage')
      expect(screen.text()).toContain('20.11.2026 09:00')
    })
  })

  describe('the timer buttons', () => {
    it('stops a running timer and reloads the list', async () => {
      const api = backend(runningEntry())
      await open()
      const loads = api.requests('GET', '/time-tracking/').length
      await click(screen.button(t('time.stopTimer')))
      expect(api.requests('POST', '/time-tracking/stop/')).toHaveLength(1)
      expect(api.requests('GET', '/time-tracking/').length).toBe(loads + 1)
      expect(screen.hasButton(t('time.startTimer'))).toBe(true)
    })

    it('pauses and resumes a running timer', async () => {
      const api = backend(runningEntry())
      await open()
      await click(screen.button(t('time.pauseTimer')))
      await click(screen.button(t('time.resumeTimer')))
      expect(api.requests('POST', '/time-tracking/resume/')).toHaveLength(1)
    })

    it('shows the error when the timer cannot be stopped', async () => {
      const api = backend(runningEntry())
      api.post('/time-tracking/stop/', reply(400, { detail: 'Overlaps another entry.' }))
      await open()
      await click(screen.button(t('time.stopTimer')))
      expect(document.body.textContent).toContain('Overlaps another entry.')
      expect(screen.hasButton(t('time.stopTimer'))).toBe(true)
    })
  })

  describe('a manual entry', () => {
    async function newEntry() {
      const api = backend()
      api.post('/time-tracking/', (call) => timeEntry(call.body as Partial<TimeEntry>))
      await open()
      await click(screen.button(t('time.new')))
      return { api, modal: dialog(t('time.new')) }
    }

    it('starts now and ends after the typed duration', async () => {
      const { api, modal } = await newEntry()
      expect(modal.input(t('time.start')).value).toBe('23.11.2026 09:15')
      await type(modal.input(t('time.duration')), '1,5')
      expect(modal.input(t('time.duration')).value).toBe('01:30')
      expect(modal.input(t('time.end')).value).toBe('23.11.2026 10:45')
      await choose(modal.field(t('projects.customer')), 'Acme GmbH')
      await type(modal.input(t('time.description')), 'Workshop')
      await click(modal.button(t('common.save')))

      expect(api.lastBody('POST', '/time-tracking/')).toEqual({
        customer: 'cus-1',
        project: null,
        visit: null,
        contract: null,
        start_datetime: new Date(2026, 10, 23, 9, 15).toISOString(),
        end_datetime: new Date(2026, 10, 23, 10, 45).toISOString(),
        breaks: [],
        description: 'Workshop',
        billable: true,
      })
      expect(isDialogOpen(t('time.new'))).toBe(false)
    })

    it('works out the duration from typed start and end, minus breaks', async () => {
      const { api, modal } = await newEntry()
      await type(modal.input(t('time.start')), '20.11. 8')
      await type(modal.input(t('time.end')), '1030')
      expect(modal.input(t('time.end')).value).toBe('20.11.2026 10:30')
      expect(modal.input(t('time.duration')).value).toBe('02:30')

      await click(modal.button(t('time.addBreak')))
      const breakInputs = modal.root.querySelectorAll<HTMLInputElement>(
        '[role="group"] input[placeholder="' + t('time.dateTimePlaceholder') + '"]',
      )
      await type(breakInputs[2]!, '20.11. 9')
      await type(breakInputs[3]!, '20.11. 915')
      expect(modal.input(t('time.duration')).value).toBe('02:15')
      expect(modal.input(t('time.end')).value).toBe('20.11.2026 10:30')

      await click(modal.button(t('common.save')))
      expect(api.lastBody('POST', '/time-tracking/')).toMatchObject({
        start_datetime: new Date(2026, 10, 20, 8, 0).toISOString(),
        end_datetime: new Date(2026, 10, 20, 10, 30).toISOString(),
        breaks: [
          {
            start_datetime: new Date(2026, 10, 20, 9, 0).toISOString(),
            end_datetime: new Date(2026, 10, 20, 9, 15).toISOString(),
          },
        ],
      })
    })

    it('a longer duration moves the end, keeping breaks in', async () => {
      const { modal } = await newEntry()
      await type(modal.input(t('time.start')), '20.11. 8')
      await click(modal.button(t('time.addBreak')))
      const inputs = modal.root.querySelectorAll<HTMLInputElement>(
        'input[placeholder="' + t('time.dateTimePlaceholder') + '"]',
      )
      await type(inputs[2]!, '20.11. 9')
      await type(inputs[3]!, '20.11. 930')
      await type(modal.input(t('time.duration')), '2')
      await pressEnter(modal.input(t('time.duration')))
      expect(modal.input(t('time.end')).value).toBe('20.11.2026 10:30')
    })

    it('removes a break again', async () => {
      const { modal } = await newEntry()
      await click(modal.button(t('time.addBreak')))
      expect(modal.buttons(t('common.delete'))).toHaveLength(1)
      await click(modal.button(t('common.delete')))
      expect(modal.buttons(t('common.delete'))).toHaveLength(0)
    })

    it('refuses a duration it cannot read and keeps the old one', async () => {
      const { modal } = await newEntry()
      await type(modal.input(t('time.duration')), '2')
      await type(modal.input(t('time.duration')), 'lots')
      expect(modal.input(t('time.duration')).getAttribute('aria-invalid')).toBe('true')
      expect(modal.input(t('time.end')).value).toBe('23.11.2026 11:15')
    })

    it('says while typing what a date will be read as, and refuses nonsense', async () => {
      const { modal } = await newEntry()
      await typeOnly(modal.input(t('time.end')), '2.11. 18')
      expect(modal.field(t('time.end')).textContent).toContain('→ 02.11.2026 18:00')
      await typeOnly(modal.input(t('time.end')), 'soon')
      expect(modal.field(t('time.end')).textContent).toContain(t('time.inputUnreadable'))
      await type(modal.input(t('time.end')), 'soon')
      expect(modal.input(t('time.end')).getAttribute('aria-invalid')).toBe('true')
    })

    it('shows the backend error on the field', async () => {
      const { api, modal } = await newEntry()
      api.post('/time-tracking/', reply(400, { end_datetime: ['End must be after start.'] }))
      await click(modal.button(t('common.save')))
      expect(dialog(t('time.new')).fieldError(t('time.end'))).toBe('End must be after start.')
    })

    it("offers the customer's active contracts", async () => {
      const { api, modal } = await newEntry()
      api.get('/support-contracts/', page([contract()]))
      await choose(modal.field(t('projects.customer')), 'Acme GmbH')
      expect(Object.fromEntries(api.requests('GET', '/support-contracts/').at(-1)!.query)).toEqual({
        customer: 'cus-1',
        active: 'true',
        page_size: '100',
      })
      await choose(modal.field(t('time.coveredByContract')), 'Wartung')
      await click(modal.button(t('common.save')))
      expect(api.lastBody('POST', '/time-tracking/')).toMatchObject({ contract: 'ctr-1' })
    })
  })

  it('edits an existing entry and shows its rounded times', async () => {
    const api = backend()
    api.put('/time-tracking/te-1/', (call) => call.body)
    await open()
    await click(screen.row('Homepage'))
    // No entry from the list is changed by just opening it.
    const modal = dialog(t('time.editEntry'))
    expect(modal.input(t('time.start')).value).toBe('20.11.2026 09:00')
    expect(modal.input(t('time.duration')).value).toBe('02:00')
    expect(modal.field(t('time.normalizedDuration')).textContent).toContain('—')

    await type(modal.input(t('time.end')), '20.11. 1145')
    await click(modal.button(t('common.save')))
    expect(api.lastBody('PUT', '/time-tracking/te-1/')).toMatchObject({
      customer: 'cus-1',
      project: 'prj-1',
      start_datetime: '2026-11-20T09:00:00+01:00',
      end_datetime: new Date(2026, 10, 20, 11, 45).toISOString(),
    })
  })

  it('shows the rounded start, end and duration of an entry', async () => {
    backend(null, [
      timeEntry({
        normalized_start_datetime: '2026-11-20T09:00:00+01:00',
        normalized_end_datetime: '2026-11-20T11:15:00+01:00',
      }),
    ])
    await open()
    await click(screen.row('Homepage'))
    const modal = dialog(t('time.editEntry'))
    expect(modal.field(t('time.normalizedStart')).textContent).toContain('20.11.2026 09:00')
    expect(modal.field(t('time.normalizedDuration')).textContent).toContain('02:15')
  })
})
