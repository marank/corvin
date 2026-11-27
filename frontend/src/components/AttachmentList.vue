<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import FileUpload from 'primevue/fileupload'
import { attachmentsApi, type Attachment } from '../api'
import { useNotify } from '../composables/useNotify'
import { useConfirmDelete } from '../composables/useConfirmDelete'
import AppEmptyState from './ui/AppEmptyState.vue'
import AppIconButton from './ui/AppIconButton.vue'
import AppDateTimeDisplay from './ui/AppDateTimeDisplay.vue'
import AttachmentPreview from './AttachmentPreview.vue'

const props = defineProps<{ model: string; objectId: string }>()
const { t } = useI18n()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const items = ref<Attachment[]>([])
const contentType = ref<number | null>(null)
const uploading = ref(false)
const preview = ref<InstanceType<typeof AttachmentPreview>>()

async function load() {
  try {
    const map = await attachmentsApi.contentTypes()
    contentType.value = map[props.model] ?? null
    if (contentType.value === null) return
    items.value = (await attachmentsApi.list(contentType.value, props.objectId)).results
  } catch (e) {
    notify.error(e)
  }
}
watch(() => props.objectId, load)
onMounted(load)

async function onUpload(ev: { files: File | File[] }) {
  if (contentType.value === null) return
  const files = Array.isArray(ev.files) ? ev.files : [ev.files]
  uploading.value = true
  try {
    for (const f of files) {
      await attachmentsApi.upload(contentType.value, props.objectId, f)
    }
    notify.ok(t('common.uploaded'))
  } catch (e) {
    notify.error(e)
  } finally {
    uploading.value = false
    void load()
  }
}

function remove(a: Attachment) {
  confirmDelete(async () => {
    await attachmentsApi.remove(a.id)
    await load()
  })
}
</script>

<template>
  <div>
    <FileUpload
      mode="basic"
      auto
      :multiple="true"
      :custom-upload="true"
      :disabled="uploading"
      @uploader="onUpload"
      :choose-label="t('common.upload')"
      choose-icon="pi pi-upload"
    />
    <AppEmptyState v-if="!items.length" />
    <ul v-else class="mt-3 divide-y divide-surface-200 dark:divide-surface-800">
      <li v-for="a in items" :key="a.id" class="flex items-center gap-3 py-2">
        <i class="pi pi-paperclip" />
        <button
          v-if="a.preview"
          type="button"
          class="text-sm text-primary truncate flex-1 text-left cursor-pointer"
          @click="preview?.open(a)"
        >
          {{ a.name }}
        </button>
        <a v-else :href="a.url" :download="a.name" class="text-sm text-primary truncate flex-1">{{
          a.name
        }}</a>
        <AppDateTimeDisplay
          class="text-xs text-surface-400"
          :value="a.uploaded_at"
          type="datetime"
        />
        <AppIconButton icon="pi pi-trash" severity="danger" @click="remove(a)" />
      </li>
    </ul>
    <AttachmentPreview ref="preview" />
  </div>
</template>
