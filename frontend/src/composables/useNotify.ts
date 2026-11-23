import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { ApiError } from '../api/client'
import { clearFormErrors, errorText, isFieldShown, setFormErrors } from './formErrors'

const GENERAL_KEYS = ['detail', 'non_field_errors']

export function useNotify() {
  const toast = useToast()
  const { t } = useI18n()
  return {
    ok(summary: string) {
      clearFormErrors()
      toast.add({ severity: 'success', summary, life: 2500 })
    },
    error(err: unknown, summary?: string) {
      if (!(err instanceof ApiError && err.data && typeof err.data === 'object')) {
        toast.add({ severity: 'error', summary: summary ?? t('common.error'), life: 5000 })
        return
      }
      // A bare list of messages (e.g. a model ValidationError) has no fields to map to.
      if (Array.isArray(err.data)) {
        clearFormErrors()
        toast.add({
          severity: 'error',
          summary: summary ?? t('common.error'),
          detail: errorText(err.data) || undefined,
          life: 5000,
        })
        return
      }
      const data = err.data as Record<string, unknown>
      setFormErrors(data)
      // Errors for visible fields appear inline; the toast carries the rest.
      const lines = Object.entries(data)
        .filter(([key]) => GENERAL_KEYS.includes(key) || !isFieldShown(key))
        .map(([key, value]) =>
          GENERAL_KEYS.includes(key) ? errorText(value) : `${key}: ${errorText(value)}`,
        )
      toast.add({
        severity: 'error',
        summary: summary ?? (lines.length ? t('common.error') : t('common.checkInput')),
        detail: lines.join('\n') || undefined,
        life: 5000,
      })
    },
  }
}
