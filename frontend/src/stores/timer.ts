import { defineStore } from 'pinia'
import type { TimeEntry } from '../api'
import { api } from '../api/client'
import { useSettingsStore } from './settings'

export interface RunningEntry {
  id: string
  customer: string | null
  customer_name: string | null
  project: string | null
  project_name: string | null
  start_datetime: string
  breaks: { id: string; start_datetime: string; end_datetime: string | null }[]
  is_paused: boolean
  description: string
}

function _formatElapsed(ms: number): string {
  const s = Math.floor(ms / 1000)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

export const useTimerStore = defineStore('timer', {
  state: () => ({
    running: null as RunningEntry | null,
    elapsed: 0,
    breakElapsed: 0,
    _interval: null as ReturnType<typeof setInterval> | null,
    version: 0,
  }),
  getters: {
    elapsedText: (state) => _formatElapsed(state.elapsed),
    breakElapsedText: (state) => _formatElapsed(state.breakElapsed),
  },
  actions: {
    async refresh() {
      this.running = await api.get<RunningEntry | null>(
        '/api/v1/time-tracking/active/',
      )
      this._tick()
    },
    _tick() {
      if (this._interval) clearInterval(this._interval)
      if (!this.running) {
        this.elapsed = 0
        this.breakElapsed = 0
        return
      }
      const settings = useSettingsStore()
      settings.load()
      const calc = () => {
        const running = this.running
        if (!running) return
        const start = new Date(running.start_datetime).getTime()
        const breaks = [...(running.breaks || [])].sort(
          (a, b) => new Date(a.start_datetime).getTime() - new Date(b.start_datetime).getTime()
        )
        let totalBreakMs = 0
        let activeEnd = Date.now()
        let currentBreakMs = 0
        for (const b of breaks) {
          const bs = new Date(b.start_datetime).getTime()
          const be = b.end_datetime ? new Date(b.end_datetime).getTime() : null
          if (be) {
            totalBreakMs += be - bs
          } else {
            activeEnd = bs
            currentBreakMs = Date.now() - bs
            break
          }
        }
        this.breakElapsed = Math.max(0, currentBreakMs)
        if (settings.timerCountsDuringBreak) {
          this.elapsed = Math.max(0, Date.now() - start)
        } else {
          this.elapsed = Math.max(0, activeEnd - start - totalBreakMs)
        }
      }
      calc()
      this._interval = setInterval(calc, 1000)
    },
    async start(customer: string | null = null, project: string | null = null, description = '') {
      this.running = await api.post<RunningEntry>(
        '/api/v1/time-tracking/start/',
        { customer, project, description },
      )
      this.version++
      this._tick()
    },
    async stop(): Promise<TimeEntry | null> {
      if (!this.running) return null
      const entry = await api.post<TimeEntry>('/api/v1/time-tracking/stop/')
      this.running = null
      this.elapsed = 0
      this.breakElapsed = 0
      this.version++
      if (this._interval) clearInterval(this._interval)
      return entry
    },
    async pause() {
      if (!this.running) return
      this.running = await api.post<RunningEntry>('/api/v1/time-tracking/pause/')
      this.version++
      this._tick()
    },
    async resume() {
      if (!this.running) return
      this.running = await api.post<RunningEntry>('/api/v1/time-tracking/resume/')
      this.version++
      this._tick()
    },
  },
})
