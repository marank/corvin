<script setup lang="ts">
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = withDefaults(
  defineProps<{
    title: string
    size?: 'sm' | 'md' | 'lg' | 'xl'
    confirmLabel?: string
    showFooter?: boolean
    loading?: boolean
  }>(),
  { size: 'md', showFooter: true, loading: false },
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

function open() {
  visible.value = true
}
function close() {
  visible.value = false
  emit('closed')
}

defineExpose({ open, close })
</script>

<template>
  <Dialog
    v-model:visible="visible"
    :header="title"
    modal
    :class="widthClass"
    :pt="{ root: { class: 'm-2 sm:m-0' } }"
    @hide="emit('closed')"
  >
    <slot />
    <template v-if="showFooter" #footer>
      <slot name="footer">
        <Button :label="t('common.cancel')" text @click="close" />
        <Button
          :label="confirmLabel ?? t('common.save')"
          :loading="loading"
          @click="emit('confirm')"
        />
      </slot>
    </template>
  </Dialog>
</template>
