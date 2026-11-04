import { computed, onBeforeUnmount, onMounted, ref, type Ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useI18n } from 'vue-i18n'

/** Asks before throwing away unsaved input; resolves to true when the user agrees. */
export function useConfirmDiscard() {
  const confirm = useConfirm()
  const { t } = useI18n()
  return () => new Promise<boolean>((resolve) => {
    confirm.require({
      header: t('common.unsavedTitle'),
      message: t('common.unsavedMessage'),
      icon: 'pi pi-exclamation-triangle',
      rejectLabel: t('common.keepEditing'),
      rejectProps: { text: true },
      acceptLabel: t('common.discard'),
      acceptClass: 'p-button-danger',
      accept: () => resolve(true),
      reject: () => resolve(false),
      onHide: () => resolve(false),
    })
  })
}

/**
 * Guards a page form: leaving the route or closing the tab with changes since the
 * last markSaved() asks first. Call markSaved() after loading and after saving.
 */
export function useUnsavedChanges(form: Ref<unknown>, enabled: () => boolean = () => true) {
  const saved = ref(JSON.stringify(form.value))
  const isDirty = computed(() => enabled() && JSON.stringify(form.value) !== saved.value)
  const confirmDiscard = useConfirmDiscard()

  function markSaved() {
    saved.value = JSON.stringify(form.value)
  }

  const onBeforeUnload = (event: BeforeUnloadEvent) => {
    if (!isDirty.value) return
    event.preventDefault()
    event.returnValue = ''
  }
  onMounted(() => window.addEventListener('beforeunload', onBeforeUnload))
  onBeforeUnmount(() => window.removeEventListener('beforeunload', onBeforeUnload))
  onBeforeRouteLeave(() => (isDirty.value ? confirmDiscard() : true))

  return { isDirty, markSaved }
}
