<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import AppCodeEditor from '../../components/ui/AppCodeEditor.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppLoadState from '../../components/ui/AppLoadState.vue'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import InvoicePreviewFrame from '../../components/InvoicePreviewFrame.vue'
import InvoiceVariableBrowser from '../../components/InvoiceVariableBrowser.vue'
import {
  companyImagesApi,
  mailTemplatesApi,
  textBlocksApi,
  type CompanyImage,
  type MailTemplate,
  type TextBlock,
} from '../../api'
import { ApiError } from '../../api/client'
import { errorText } from '../../composables/formErrors'
import { templateVariableGroups } from '../../composables/templateVariables'
import { useConfirmDelete } from '../../composables/useConfirmDelete'
import { useLoadFailed } from '../../composables/useLoadFailed'
import { useNotify } from '../../composables/useNotify'
import { useTabQuery } from '../../composables/useTabQuery'
import { useUnsavedChanges } from '../../composables/useUnsavedChanges'

// An e-mail template: its HTML, with a base only blocks overriding the base's (prefilled
// with every block of the base). The preview renders the unsaved state.
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const id = route.params.id as string

const template = ref<MailTemplate | null>(null)
const { markSaved } = useUnsavedChanges(template)
const others = ref<MailTemplate[]>([])
const images = ref<CompanyImage[]>([])
const textBlocks = ref<TextBlock[]>([])
const saving = ref(false)
const section = useTabQuery('general', ['general', 'html'])

const base = computed(() => others.value.find((other) => other.id === template.value?.base))
// Bases on offer: any other template (the backend refuses loops).
const baseOptions = computed(() => others.value.filter((other) => other.id !== id))
const canDelete = computed(
  () => !!template.value && !template.value.assigned_kinds.length && !template.value.derived_count,
)

const variableGroups = computed(() =>
  templateVariableGroups(t, { textBlocks: textBlocks.value, images: images.value, mail: true }),
)
const editor = ref<InstanceType<typeof AppCodeEditor>>()

function insertSnippet(code: string) {
  if (editor.value) editor.value.insert(code)
  else if (template.value) template.value.html += code
}

// Every block of the base, keeping its content until replaced (as the backend prefills).
function blocksOf(baseTemplate: MailTemplate) {
  return baseTemplate.slot_names
    .map((name) => `{% block ${name} %}{{ block.super }}{% endblock %}`)
    .join('\n\n')
}

// Choosing a base for an empty template writes out the base's blocks to fill in.
watch(base, (chosen) => {
  if (chosen && template.value && !template.value.html.trim())
    template.value.html = blocksOf(chosen)
})

const previewSubject = ref('')
const previewHtml = ref<string>()
const previewError = ref<string | null>(null)
let previewTimer: ReturnType<typeof setTimeout> | undefined
let previewRun = 0

async function refreshPreview() {
  if (!template.value) return
  const run = ++previewRun
  try {
    const { subject, html, base: baseId, name } = template.value
    const preview = await mailTemplatesApi.preview(id, { subject, html, base: baseId, name })
    if (run !== previewRun) return
    previewSubject.value = preview.subject
    previewHtml.value = preview.html
    previewError.value = null
  } catch (e) {
    if (run === previewRun)
      previewError.value = e instanceof ApiError && e.data ? errorText(e.data) : t('common.error')
  }
}

watch(
  template,
  () => {
    clearTimeout(previewTimer)
    previewTimer = setTimeout(() => void refreshPreview(), 400)
  },
  { deep: true },
)
onBeforeUnmount(() => clearTimeout(previewTimer))

const loadFailed = useLoadFailed(async () => {
  const [loaded, list, imagePage, textBlockPage] = await Promise.all([
    mailTemplatesApi.get(id),
    mailTemplatesApi.list('page_size=500&ordering=name'),
    companyImagesApi.list(),
    textBlocksApi.list(),
  ])
  template.value = loaded
  others.value = list.results
  images.value = imagePage.results
  textBlocks.value = textBlockPage.results
  markSaved()
})

async function save() {
  if (!template.value) return
  saving.value = true
  try {
    template.value = await mailTemplatesApi.update(id, template.value)
    markSaved()
    notify.ok(t('common.saved'))
  } catch (e) {
    notify.error(e)
  } finally {
    saving.value = false
  }
}

function remove() {
  confirmDelete(async () => {
    await mailTemplatesApi.remove(id)
    markSaved()
    void router.push('/templates?tab=mailTemplates')
  })
}
</script>

<template>
  <div v-if="template" class="h-full flex flex-col">
    <AppPageHeader
      back-to="/templates?tab=mailTemplates"
      :back-label="t('nav.templates')"
      :title="template.name"
      :subtitle="t('designer.mailTemplate')"
    >
      <template #actions>
        <Button
          v-if="canDelete"
          :label="t('common.delete')"
          text
          severity="danger"
          @click="remove"
        />
        <Button
          :label="t('common.save')"
          icon="iconify lucide--save"
          :loading="saving"
          @click="save"
        />
      </template>
    </AppPageHeader>

    <div class="flex-1 min-h-0 flex flex-col lg:grid lg:grid-cols-2 gap-4">
      <div
        class="flex flex-col flex-1 min-h-[70vh] lg:min-h-0 border border-surface-200 dark:border-surface-800"
      >
        <Tabs v-model:value="section" scrollable class="flex-1 min-h-0 flex flex-col">
          <TabList>
            <Tab value="general">{{ t('designer.general') }}</Tab>
            <Tab value="html">{{ t('designer.mailHtml') }}</Tab>
          </TabList>
          <TabPanels class="flex-1 min-h-0">
            <TabPanel value="general" class="h-full overflow-y-auto p-4">
              <div class="flex flex-col gap-4 max-w-2xl">
                <AppFormField field="name" :label="t('designer.templateName')" required
                  ><InputText v-model="template.name" class="w-full"
                /></AppFormField>
                <AppFormField field="subject" :label="t('designer.mailSubject')"
                  ><InputText v-model="template.subject" class="w-full font-mono text-sm"
                /></AppFormField>
                <AppFormField field="base" :label="t('designer.mailBase')">
                  <Select
                    v-model="template.base"
                    :options="baseOptions"
                    option-label="name"
                    option-value="id"
                    show-clear
                    :placeholder="t('designer.noBase')"
                    class="w-full"
                  />
                </AppFormField>
                <p class="text-sm text-surface-500">
                  {{ template.base ? t('designer.blocksHint') : t('designer.mailHtmlHint') }}
                </p>
              </div>
            </TabPanel>
            <TabPanel value="html" class="h-full">
              <AppCodeEditor ref="editor" v-model="template.html" language="html" />
            </TabPanel>
          </TabPanels>
        </Tabs>
        <InvoiceVariableBrowser :groups="variableGroups" @insert="insertSnippet">
          <template #title>{{ t('designer.placeholders') }}</template>
        </InvoiceVariableBrowser>
      </div>
      <div
        class="flex flex-col flex-1 min-h-[70vh] lg:min-h-0 border border-surface-200 dark:border-surface-800"
      >
        <Message v-if="previewError" severity="warn" size="small" class="m-2">{{
          t('designer.previewStale', { error: previewError })
        }}</Message>
        <div class="px-3 py-2 text-sm border-b border-surface-200 dark:border-surface-800 truncate">
          <span class="text-surface-500">{{ t('designer.mailSubject') }}:</span>
          {{ previewSubject }}
        </div>
        <InvoicePreviewFrame class="flex-1 min-h-0" :html="previewHtml" />
      </div>
    </div>
  </div>
  <AppLoadState
    v-else
    :failed="loadFailed"
    back-to="/templates?tab=mailTemplates"
    :back-label="t('nav.templates')"
  />
</template>
