import { useConfirm } from 'primevue/useconfirm'
import { useI18n } from 'vue-i18n'
import { useNotify } from './useNotify'

export function useConfirmDelete() {
  const confirm = useConfirm()
  const notify = useNotify()
  const { t } = useI18n()

  return function confirmDelete(action: () => Promise<unknown>) {
    confirm.require({
      header: t('common.delete'),
      message: t('common.deleteConfirm'),
      icon: 'pi pi-trash',
      rejectLabel: t('common.cancel'),
      rejectProps: { text: true },
      acceptLabel: t('common.delete'),
      acceptClass: 'p-button-danger',
      // The backend refuses some deletes (e.g. protected relations); say so instead of failing silently.
      accept: async () => {
        try {
          await action()
          notify.ok(t('common.deleted'))
        } catch (e) {
          notify.error(e)
        }
      },
    })
  }
}
