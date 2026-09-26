import { defineStore } from 'pinia'
import { api } from '../api/client'

export interface User {
  id: number
  username: string
  email: string
  totp_enabled: boolean
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as User | null,
    checked: false,
  }),
  actions: {
    async check() {
      try {
        this.user = await api.get<User>('/api/v1/auth/me')
      } catch {
        this.user = null
      } finally {
        this.checked = true
      }
    },
    async login(username: string, password: string, otpCode = '') {
      this.user = await api.post<User>('/api/v1/auth/login', {
        username,
        password,
        otp_code: otpCode,
      })
    },
    async logout() {
      await api.post('/api/v1/auth/logout')
      this.user = null
    },
  },
})
