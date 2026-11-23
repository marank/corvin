import { defineStore } from 'pinia'
import { authApi, type User } from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as User | null,
    checked: false,
  }),
  actions: {
    async check() {
      try {
        this.user = await authApi.me()
      } catch {
        this.user = null
      } finally {
        this.checked = true
      }
    },
    async login(username: string, password: string, otpCode = '') {
      this.user = await authApi.login(username, password, otpCode)
    },
    async logout() {
      await authApi.logout()
      this.user = null
    },
  },
})
