<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import FileUpload from 'primevue/fileupload'
import { attachmentsApi, type Attachment } from '../api'
import { useNotify } from '../composables/useNotify'
import AppEmptyState from './ui/AppEmptyState.vue'
import AppIconButton from './ui/AppIconButton.vue'
import AppDateTimeDisplay from './ui/AppDateTimeDisplay.vue'

const props = defineProps<{ model: string; objectId: string }>()
const { t } = useI18n()
const notify = useNotify()
const items = ref<Attachment[]>([])
const contentType = ref<number | null>(null)

async function load() {
  const map = await attachmentsApi.contentTypes()
  contentType.value = map[props.model] ?? null
  if (contentType.value === null) return
  items.value = (await attachmentsApi.list(contentType.value, props.objectId)).results
}
watch(() => props.objectId, load)
onMounted(load)

async function onUpload(ev: { files: File | File[] }) {
  if (contentType.value === null) return
  const files = Array.isArray(ev.files) ? ev.files : [ev.files]
  for (const f of files) {
    await attachmentsApi.upload(contentType.value, props.objectId, f)
  }
  load()
}

async function remove(a: Attachment) {
  await attachmentsApi.remove(a.id)
  notify.ok(t('common.deleted'))
  load()
}
</script>

<template>
  <div>
    <FileUpload mode="basic" auto :multiple="true" :custom-upload="true" @uploader="onUpload" :choose-label="t('common.create')" />
    <AppEmptyState v-if="!items.length" />
    <ul v-else class="mt-3 divide-y divide-surface-200 dark:divide-surface-800">
      <li v-for="a in items" :key="a.id" class="flex items-center gap-3 py-2">
        <i class="pi pi-paperclip" />
        <a :href="a.url" target="_blank" class="text-sm text-primary truncate flex-1">{{ a.name }}</a>
        <AppDateTimeDisplay class="text-xs text-surface-400" :value="a.uploaded_at" type="datetime" />
        <AppIconButton icon="pi pi-trash" severity="danger" @click="remove(a)" />
      </li>
    </ul>
  </div>
</template>
