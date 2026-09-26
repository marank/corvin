import { useToast } from 'primevue/usetoast'
import { ApiError } from '../api/client'

export function useNotify() {
  const toast = useToast()
  return {
    ok(summary: string) {
      toast.add({ severity: 'success', summary, life: 2500 })
    },
    error(err: unknown, fallback = 'Error') {
      let detail = fallback
      if (err instanceof ApiError && err.data && typeof err.data === 'object') {
        detail = Object.entries(err.data as Record<string, unknown>)
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
          .join('\n')
      }
      toast.add({ severity: 'error', summary: fallback, detail, life: 5000 })
    },
  }
}
