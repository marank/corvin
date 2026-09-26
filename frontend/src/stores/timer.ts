import { defineStore } from 'pinia'
import { api } from '../api/client'

export interface RunningEntry {
  id: number
  project: number
  project_name: string
  date: string
  start_time: string
  description: string
}

export const useTimerStore = defineStore('timer', {
  state: () => ({
    running: null as RunningEntry | null,
    elapsed: 0,
    _interval: null as ReturnType<typeof setInterval> | null,
  }),
  actions: {
    async refresh() {
      this.running = await api.get<RunningEntry | null>(
        '/api/v1/time-entries/active/',
      )
      this._tick()
    },
    _tick() {
      if (this._interval) clearInterval(this._interval)
      if (!this.running) {
        this.elapsed = 0
        return
      }
      const start = new Date(
        `${this.running.date}T${this.running.start_time}`,
      ).getTime()
      this._interval = setInterval(() => {
        this.elapsed = Math.max(0, Date.now() - start)
      }, 1000)
    },
    async start(project: number, description = '') {
      this.running = await api.post<RunningEntry>(
        '/api/v1/time-entries/start_timer/',
        { project, description },
      )
      this._tick()
    },
    async stop() {
      if (!this.running) return
      await api.post(`/api/v1/time-entries/${this.running.id}/stop/`)
      this.running = null
      this.elapsed = 0
      if (this._interval) clearInterval(this._interval)
    },
  },
})
