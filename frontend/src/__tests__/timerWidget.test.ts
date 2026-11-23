import { describe, expect, it } from 'vitest'
import TimerWidget from '../components/TimerWidget.vue'
import type { RunningEntry } from '../api'
import { mockApi, page, reply } from './helpers/api'
import { choose, click, dialog, isDialogOpen, screen, toasts, type } from './helpers/dom'
import { customer, project, runningEntry, timeEntry } from './helpers/fixtures'
import { render, t } from './helpers/render'

function backend(settings: Record<string, unknown>, running: RunningEntry | null = runningEntry()) {
  const api = mockApi()
  api.get('/settings/', settings)
  api.get('/time-tracking/active/', running)
  api.get('/customers/', page([customer(), customer({ id: 'cus-2', name: 'Beta AG' })]))
  api.get(
    '/projects/',
    page([
      project(),
      project({ id: 'prj-2', name: 'Shop', customer: 'cus-2', customer_name: 'Beta AG' }),
    ]),
  )
  api.get('/support-contracts/', page([]))
  api.post('/time-tracking/stop/', timeEntry({ id: 'te-run', description: 'Support' }))
  return api
}

const open = () => render(TimerWidget)

describe('TimerWidget', () => {
  it('stays hidden without a running timer', async () => {
    backend({}, null)
    await open()
    expect(screen.hasButton(t('time.startTimer'))).toBe(false)
  })

  it('can always be shown, to start a timer from anywhere', async () => {
    backend({ always_show_timer_widget: true }, null)
    await open()
    expect(screen.text()).toContain('00:00:00')
    expect(screen.hasButton(t('time.startTimer'))).toBe(true)
  })

  it('shows the running time and what it is for', async () => {
    backend({})
    await open()
    expect(screen.text()).toContain('01:15:00')
    expect(screen.text()).toContain('Support')
  })

  it('pauses and resumes', async () => {
    const api = backend({})
    api.post('/time-tracking/pause/', runningEntry({ is_paused: true }))
    api.post('/time-tracking/resume/', runningEntry())
    await open()
    await click(screen.button(t('time.pauseTimer')))
    expect(api.requests('POST', '/time-tracking/pause/')).toHaveLength(1)
    await click(screen.button(t('time.resumeTimer')))
    expect(api.requests('POST', '/time-tracking/resume/')).toHaveLength(1)
    expect(screen.hasButton(t('time.pauseTimer'))).toBe(true)
  })

  it('shows an error when pausing fails', async () => {
    const api = backend({})
    api.post('/time-tracking/pause/', reply(500, 'Server Error'))
    await open()
    await click(screen.button(t('time.pauseTimer')))
    expect(toasts()).toEqual([t('common.error')])
  })

  it('asks after stopping whether to open the entry, and saves it', async () => {
    const api = backend({ open_stopped_time_entry: 'ask' })
    api.put('/time-tracking/te-run/', (call) => ({
      ...timeEntry({ id: 'te-run' }),
      ...(call.body as object),
    }))
    await open()
    await click(screen.button(t('time.stopTimer')))
    expect(dialog(t('time.openStoppedEntryTitle')).text()).toContain(
      t('time.openStoppedEntryPrompt'),
    )
    await click(dialog(t('time.openStoppedEntryTitle')).button(t('common.yes')))

    const modal = dialog(t('time.editEntry'))
    expect(modal.input(t('time.description')).value).toBe('Support')
    await type(modal.input(t('time.description')), 'Support call')
    await click(modal.button(t('common.save')))

    expect(api.lastBody('PUT', '/time-tracking/te-run/')).toMatchObject({
      description: 'Support call',
      customer: 'cus-1',
    })
    expect(isDialogOpen(t('time.editEntry'))).toBe(false)
  })

  it('leaves the stopped entry alone when told no', async () => {
    backend({ open_stopped_time_entry: 'ask' })
    await open()
    await click(screen.button(t('time.stopTimer')))
    await click(dialog(t('time.openStoppedEntryTitle')).button(t('common.no')))
    expect(isDialogOpen(t('time.openStoppedEntryTitle'))).toBe(false)
    expect(isDialogOpen(t('time.editEntry'))).toBe(false)
  })

  it('opens the stopped entry directly or not at all, as configured', async () => {
    backend({ open_stopped_time_entry: 'yes' })
    await open()
    await click(screen.button(t('time.stopTimer')))
    expect(isDialogOpen(t('time.editEntry'))).toBe(true)
  })

  it('does not open the stopped entry when configured so', async () => {
    backend({ open_stopped_time_entry: 'no' })
    await open()
    await click(screen.button(t('time.stopTimer')))
    expect(isDialogOpen(t('time.openStoppedEntryTitle'))).toBe(false)
    expect(isDialogOpen(t('time.editEntry'))).toBe(false)
  })

  describe('starting', () => {
    it('starts with description and the project, filling in its customer', async () => {
      const api = backend({ always_show_timer_widget: true }, null)
      api.post('/time-tracking/start/', runningEntry({ project_name: 'Shop' }))
      await open()
      await click(screen.button(t('time.startTimer')))
      const modal = dialog(t('time.startTimer'))
      await type(modal.input(t('time.description')), '  Hotline  ')
      await choose(modal.field(t('projects.project')), 'Shop')
      await click(modal.button(t('time.startNow')))

      expect(api.lastBody('POST', '/time-tracking/start/')).toEqual({
        customer: 'cus-2',
        project: 'prj-2',
        description: 'Hotline',
      })
      expect(isDialogOpen(t('time.startTimer'))).toBe(false)
      expect(screen.hasButton(t('time.stopTimer'))).toBe(true)
    })

    it('shows the field error and stays open when the start is refused', async () => {
      const api = backend({ always_show_timer_widget: true }, null)
      api.post('/time-tracking/start/', reply(400, { customer: ['A customer is required.'] }))
      await open()
      await click(screen.button(t('time.startTimer')))
      await click(dialog(t('time.startTimer')).button(t('time.startNow')))
      expect(dialog(t('time.startTimer')).fieldError(t('projects.customer'))).toBe(
        'A customer is required.',
      )
    })

    it('keeps customer and project for the next start, but not the description', async () => {
      const api = backend({ always_show_timer_widget: true }, null)
      api.post('/time-tracking/start/', runningEntry())
      await open()
      await click(screen.button(t('time.startTimer')))
      let modal = dialog(t('time.startTimer'))
      await type(modal.input(t('time.description')), 'First')
      await choose(modal.field(t('projects.customer')), 'Beta AG')
      await click(modal.button(t('time.startNow')))
      await click(screen.button(t('time.stopTimer')))

      await click(screen.button(t('time.startTimer')))
      modal = dialog(t('time.startTimer'))
      expect(modal.input(t('time.description')).value).toBe('')
      await click(modal.button(t('time.startNow')))
      expect(api.lastBody('POST', '/time-tracking/start/')).toMatchObject({ customer: 'cus-2' })
    })
  })
})
