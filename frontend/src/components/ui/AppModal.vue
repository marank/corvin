<script setup lang="ts">
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import { ref, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { clearFormErrors } from '../../composables/formErrors'
import { useConfirmDiscard } from '../../composables/useUnsavedChanges'

const props = withDefaults(
  defineProps<{
    title: string
    size?: 'sm' | 'md' | 'lg' | 'xl'
    confirmLabel?: string
    showFooter?: boolean
    loading?: boolean
    // The edited object; closing via X, Esc or Cancel after changing it asks first.
    form?: unknown
  }>(),
  { size: 'md', confirmLabel: undefined, showFooter: true, loading: false, form: undefined },
)
const emit = defineEmits<{ confirm: []; closed: [] }>()
const { t } = useI18n()
const visible = ref(false)

const widthClass = computed(
  () =>
    ({
      sm: 'w-full sm:max-w-sm',
      md: 'w-full sm:max-w-lg',
      lg: 'w-full sm:max-w-2xl',
      xl: 'w-full sm:max-w-4xl',
    })[props.size],
)

const confirmDiscard = useConfirmDiscard()
let snapshot = ''

function open() {
  clearFormErrors()
  visible.value = true
  // Callers usually fill the form right before open(); take the snapshot once props caught up.
  void nextTick(() => {
    snapshot = JSON.stringify(props.form)
  })
}
// Programmatic close (after saving). The Dialog's @hide emits `closed` for every path.
function close() {
  visible.value = false
}
// User-initiated close: X, Esc, Cancel.
async function requestClose() {
  if (
    props.form !== undefined &&
    JSON.stringify(props.form) !== snapshot &&
    !(await confirmDiscard())
  )
    return
  close()
}

defineExpose({ open, close })
</script>

<template>
  <Dialog
    :visible="visible"
    @update:visible="(value: boolean) => (value ? (visible = true) : requestClose())"
    :header="title"
    modal
    :class="widthClass"
    :pt="{ root: { class: 'm-2 sm:m-0' } }"
    @hide="emit('closed')"
  >
    <slot />
    <template v-if="showFooter" #footer>
      <slot name="footer">
        <Button :label="t('common.cancel')" text @click="requestClose" />
        <Button
          :label="confirmLabel ?? t('common.save')"
          :loading="loading"
          @click="emit('confirm')"
        />
      </slot>
    </template>
  </Dialog>
</template>
