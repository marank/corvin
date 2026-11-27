<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import { attachmentsApi, type Attachment } from '../api'
import { useNotify } from '../composables/useNotify'
import AppModal from './ui/AppModal.vue'
import AppMarkdown from './ui/AppMarkdown.vue'

// Shows an attachment the backend marked as safe to preview (`preview`): Markdown with raw
// HTML escaped, text as plain text, images and PDFs from a blob URL.
const { t } = useI18n()
const notify = useNotify()
const modal = ref<InstanceType<typeof AppModal>>()
const shown = ref<Attachment>()
const text = ref<string>()
const blobUrl = ref<string>()

function decode(buffer: ArrayBuffer): string {
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(buffer)
  } catch {
    // Older exports from Windows tools.
    return new TextDecoder('windows-1252').decode(buffer)
  }
}

function reset() {
  if (blobUrl.value) URL.revokeObjectURL(blobUrl.value)
  blobUrl.value = undefined
  text.value = undefined
}

async function open(a: Attachment) {
  reset()
  shown.value = a
  modal.value?.open()
  try {
    const blob = await attachmentsApi.content(a)
    if (shown.value !== a) return
    if (a.preview === 'markdown' || a.preview === 'text')
      text.value = decode(await blob.arrayBuffer())
    else blobUrl.value = URL.createObjectURL(blob)
  } catch (e) {
    notify.error(e)
  }
}

onBeforeUnmount(reset)
defineExpose({ open })
</script>

<template>
  <AppModal ref="modal" :title="shown?.name ?? ''" size="xl" @closed="reset">
    <div v-if="shown" class="max-h-[70vh] overflow-auto">
      <template v-if="text !== undefined">
        <AppMarkdown v-if="shown.preview === 'markdown'" :source="text" />
        <pre v-else class="text-sm whitespace-pre-wrap break-words font-mono">{{ text }}</pre>
      </template>
      <img
        v-else-if="blobUrl && shown.preview === 'image'"
        :src="blobUrl"
        :alt="shown.name"
        class="max-w-full mx-auto"
      />
      <iframe
        v-else-if="blobUrl && shown.preview === 'pdf'"
        :src="blobUrl"
        :title="shown.name"
        class="w-full h-[70vh] border-0"
      />
    </div>
    <template #footer>
      <Button :label="t('common.close')" text @click="modal?.close()" />
      <Button
        as="a"
        :href="shown?.url"
        :download="shown?.name"
        :label="t('common.download')"
        icon="pi pi-download"
      />
    </template>
  </AppModal>
</template>
