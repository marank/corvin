import { useConfirm } from 'primevue/useconfirm'
import { useI18n } from 'vue-i18n'

export function useConfirmDelete() {
  const confirm = useConfirm()
  const { t } = useI18n()

  return function confirmDelete(action: () => Promise<unknown>) {
    confirm.require({
      header: t('common.delete'),
      message: t('common.deleteConfirm'),
      icon: 'pi pi-trash',
      rejectLabel: t('common.cancel'),
      acceptLabel: t('common.delete'),
      acceptClass: 'p-button-danger',
      accept: action,
    })
  }
}
