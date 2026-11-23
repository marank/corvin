import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useTimerStore } from '../stores/timer'
import { mockApi, reply } from './helpers/api'
import { runningEntry, timeEntry } from './helpers/fixtures'
import { settle } from './helpers/render'
import { NOW } from './helpers/time'

// NOW is 09:15; the running entry started at 08:00.
function backend(settings: Record<string, unknown> = {}) {
  const api = mockApi()
  api.get('/settings/', settings)
  return api
}

async function refreshWith(entry: ReturnType<typeof runningEntry> | null, settings = {}) {
  const api = backend(settings)
  api.get('/time-tracking/active/', entry)
  const timer = useTimerStore()
  await timer.refresh()
  await settle()
  return { api, timer }
}

describe('timer store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers({ now: NOW })
  })

  it('counts the running time every second', async () => {
    const { timer } = await refreshWith(runningEntry())
    expect(timer.elapsedText).toBe('01:15:00')
    vi.advanceTimersByTime(61_000)
    expect(timer.elapsedText).toBe('01:16:01')
  })

  it('shows nothing without a running timer', async () => {
    const { timer } = await refreshWith(null)
    expect(timer.running).toBeNull()
    expect(timer.elapsedText).toBe('00:00:00')
  })

  it('leaves finished breaks out of the working time', async () => {
    const { timer } = await refreshWith(
      runningEntry({
        breaks: [
          // Out of order on purpose: breaks are taken by their start.
          {
            id: 'b2',
            start_datetime: '2026-11-23T09:00:00+01:00',
            end_datetime: '2026-11-23T09:05:00+01:00',
          },
          {
            id: 'b1',
            start_datetime: '2026-11-23T08:30:00+01:00',
            end_datetime: '2026-11-23T08:40:00+01:00',
          },
        ],
      }),
    )
    expect(timer.elapsedText).toBe('01:00:00')
  })

  it('stands still during an open break and counts the break instead', async () => {
    const { timer } = await refreshWith(
      runningEntry({
        is_paused: true,
        breaks: [{ id: 'b1', start_datetime: '2026-11-23T09:00:00+01:00', end_datetime: null }],
      }),
    )
    expect(timer.elapsedText).toBe('01:00:00')
    expect(timer.breakElapsedText).toBe('00:15:00')
    vi.advanceTimersByTime(60_000)
    expect(timer.elapsedText).toBe('01:00:00')
    expect(timer.breakElapsedText).toBe('00:16:00')
  })

  it('keeps counting through breaks when the settings say so', async () => {
    const { timer } = await refreshWith(
      runningEntry({
        is_paused: true,
        breaks: [{ id: 'b1', start_datetime: '2026-11-23T09:00:00+01:00', end_datetime: null }],
      }),
      { timer_counts_during_break: true },
    )
    vi.advanceTimersByTime(1000)
    expect(timer.elapsedText).toBe('01:15:01')
  })

  it('starts with customer, project and description', async () => {
    const api = backend()
    api.post('/time-tracking/start/', runningEntry({ start_datetime: NOW.toISOString() }))
    const timer = useTimerStore()
    await timer.start('cus-1', 'prj-1', 'Support')
    expect(api.lastBody('POST', '/time-tracking/start/')).toEqual({
      customer: 'cus-1',
      project: 'prj-1',
      description: 'Support',
    })
    expect(timer.version).toBe(1)
    vi.advanceTimersByTime(5000)
    expect(timer.elapsedText).toBe('00:00:05')
  })

  it('pauses, resumes and stops', async () => {
    const { api, timer } = await refreshWith(runningEntry())
    api.post('/time-tracking/pause/', runningEntry({ is_paused: true }))
    api.post('/time-tracking/resume/', runningEntry())
    api.post('/time-tracking/stop/', timeEntry({ id: 'te-run' }))

    await timer.pause()
    expect(timer.running?.is_paused).toBe(true)
    await timer.resume()
    expect(timer.running?.is_paused).toBe(false)
    const stopped = await timer.stop()

    expect(stopped?.id).toBe('te-run')
    expect(timer.lastStopped?.id).toBe('te-run')
    expect(timer.running).toBeNull()
    expect(timer.elapsedText).toBe('00:00:00')
    expect(timer.version).toBe(3)
    // The clock stops with the timer.
    vi.advanceTimersByTime(5000)
    expect(timer.elapsedText).toBe('00:00:00')
  })

  it('does not call the backend to pause or stop a timer that is not running', async () => {
    const { api, timer } = await refreshWith(null)
    await timer.pause()
    await timer.resume()
    expect(await timer.stop()).toBeNull()
    expect(api.calls.filter((c) => c.method === 'POST')).toHaveLength(0)
  })

  it('keeps running when stopping fails', async () => {
    const { api, timer } = await refreshWith(runningEntry())
    api.post('/time-tracking/stop/', reply(400, { detail: 'Overlaps another entry.' }))
    await expect(timer.stop()).rejects.toMatchObject({ status: 400 })
    expect(timer.running).not.toBeNull()
    expect(timer.lastStopped).toBeNull()
  })
})
