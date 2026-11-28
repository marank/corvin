<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useLoadFailed } from '../composables/useLoadFailed'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import Select from 'primevue/select'
import AppSegmented from '../components/ui/AppSegmented.vue'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import AppFormField from '../components/ui/AppFormField.vue'
import AppLoadState from '../components/ui/AppLoadState.vue'
import AppPageHeader from '../components/ui/AppPageHeader.vue'
import AppCodeEditor from '../components/ui/AppCodeEditor.vue'
import InvoicePreviewFrame from '../components/InvoicePreviewFrame.vue'
import InvoiceVariableBrowser from '../components/InvoiceVariableBrowser.vue'
import { templateVariableGroups } from '../composables/templateVariables'
import {
  companyImagesApi,
  templatesApi,
  textBlocksApi,
  type CompanyImage,
  type DocumentTemplate,
  type TextBlock,
} from '../api'
import { ApiError } from '../api/client'
import { errorText } from '../composables/formErrors'
import { useNotify } from '../composables/useNotify'
import { useConfirmDelete } from '../composables/useConfirmDelete'
import { useTabQuery } from '../composables/useTabQuery'
import { useUnsavedChanges } from '../composables/useUnsavedChanges'
import { pageSizeValues } from '../utils/enums'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const id = route.params.id as string

const template = ref<DocumentTemplate | null>(null)
const { isDirty, markSaved } = useUnsavedChanges(template)
const saving = ref(false)
const previewMode = ref<'html' | 'pdf'>('html')
const previewModes = [
  { value: 'html' as const, label: 'HTML' },
  { value: 'pdf' as const, label: 'PDF' },
]
const pdfLoading = ref(false)
const pdfBlobUrl = ref<string | null>(null)
const pageSizeLabels: Record<(typeof pageSizeValues)[number], string> = {
  A3: 'DIN A3 — 297 × 420 mm',
  A4: 'DIN A4 — 210 × 297 mm',
  A5: 'DIN A5 — 148 × 210 mm',
  LETTER: 'US Letter — 8.5 × 11 in',
  LEGAL: 'US Legal — 8.5 × 14 in',
  TABLOID: 'US Tabloid — 11 × 17 in',
}
const pageSizes = pageSizeValues.map((value) => ({ value, label: pageSizeLabels[value] }))
const colorFields = [
  'primary_color',
  'secondary_color',
  'tertiary_color',
  'background_color',
  'text_color',
] as const
// Below lg one column at a time (editor or preview); one set of editors serves both layouts.
const mobileTab = ref('editor')
const editorSection = useTabQuery('general', ['general', 'header', 'body', 'footer', 'css'])
const headerEditor = ref<InstanceType<typeof AppCodeEditor>>()
const bodyEditor = ref<InstanceType<typeof AppCodeEditor>>()
const footerEditor = ref<InstanceType<typeof AppCodeEditor>>()
const images = ref<CompanyImage[]>([])
const textBlocks = ref<TextBlock[]>([])

// The preview renders the unsaved state: every change re-renders it after a short pause.
const previewHtml = ref<string>()
// Set while the latest draft fails to render (e.g. a half-typed tag); the last good preview stays.
const previewError = ref<string | null>(null)
let previewTimer: ReturnType<typeof setTimeout> | undefined
let previewRun = 0

async function renderPdfPreview(draft: DocumentTemplate, run: number) {
  pdfLoading.value = !pdfBlobUrl.value
  const blob = await templatesApi.previewDraftPdf(id, draft)
  if (run !== previewRun) return
  if (pdfBlobUrl.value) URL.revokeObjectURL(pdfBlobUrl.value)
  pdfBlobUrl.value = URL.createObjectURL(blob)
}

async function renderHtmlPreview(draft: DocumentTemplate, run: number) {
  const html = await templatesApi.previewDraft(id, draft)
  if (run !== previewRun) return
  previewHtml.value = html
}

async function refreshPreview() {
  if (!template.value) return
  const run = ++previewRun
  const draft = { ...template.value }
  try {
    if (previewMode.value === 'pdf') await renderPdfPreview(draft, run)
    else await renderHtmlPreview(draft, run)
    if (run !== previewRun) return
    previewError.value = null
  } catch (e) {
    if (run === previewRun) {
      previewError.value = e instanceof ApiError && e.data ? errorText(e.data) : t('common.error')
    }
  } finally {
    if (run === previewRun) pdfLoading.value = false
  }
}

watch(
  template,
  () => {
    clearTimeout(previewTimer)
    previewTimer = setTimeout(() => void refreshPreview(), previewMode.value === 'pdf' ? 1200 : 400)
  },
  { deep: true },
)
watch(previewMode, refreshPreview)
onBeforeUnmount(() => {
  clearTimeout(previewTimer)
  if (pdfBlobUrl.value) URL.revokeObjectURL(pdfBlobUrl.value)
})

const variableGroups = computed(() =>
  templateVariableGroups(t, { textBlocks: textBlocks.value, images: images.value, page: true }),
)

const loadFailed = useLoadFailed(async () => {
  const [invoiceTemplate, imagePage, textBlockPage] = await Promise.all([
    templatesApi.get(id),
    companyImagesApi.list(),
    textBlocksApi.list(),
  ])
  template.value = invoiceTemplate
  markSaved()
  images.value = imagePage.results
  textBlocks.value = textBlockPage.results
})

function insertSnippet(code: string) {
  const editors = { header: headerEditor.value, body: bodyEditor.value, footer: footerEditor.value }
  const editor = editors[editorSection.value as keyof typeof editors] ?? editors.body
  if (editor) editor.insert(code)
  else if (template.value) template.value.body_html += code
}

function remove() {
  confirmDelete(async () => {
    await templatesApi.remove(id)
    markSaved() // nothing left to lose: don't ask about unsaved changes on the way out
    void router.push('/templates?tab=templates')
  })
}

function exportTemplate() {
  window.location.assign(templatesApi.exportUrl(id))
}

async function save() {
  if (!template.value) return
  saving.value = true
  try {
    template.value = await templatesApi.update(id, template.value)
    markSaved()
    notify.ok(t('common.saved'))
  } catch (e) {
    notify.error(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div v-if="template" class="h-full flex flex-col">
    <AppPageHeader
      back-to="/templates?tab=templates"
      :back-label="t('nav.templates')"
      :title="template.name"
      :subtitle="t('designer.title')"
    >
      <template #actions>
        <Button :label="t('common.delete')" text severity="danger" @click="remove" />
        <!-- The export is the saved template; unsaved edits would be missing from the file. -->
        <span :title="isDirty ? t('designer.exportSaveFirst') : undefined">
          <Button
            :label="t('designer.exportTemplate')"
            icon="iconify lucide--download"
            severity="secondary"
            :disabled="isDirty"
            @click="exportTemplate"
          />
        </span>
        <AppSegmented v-model="previewMode" :options="previewModes" />
        <Button
          :label="t('common.save')"
          icon="iconify lucide--save"
          :loading="saving"
          @click="save"
        />
      </template>
    </AppPageHeader>

    <Tabs v-model:value="mobileTab" class="lg:hidden">
      <TabList>
        <Tab value="editor">{{ t('designer.editor') }}</Tab>
        <Tab value="preview">{{ t('designer.preview') }}</Tab>
      </TabList>
    </Tabs>

    <div class="flex-1 min-h-0 flex flex-col lg:grid lg:grid-cols-2 gap-4">
      <div
        class="flex-col flex-1 min-h-[70vh] lg:min-h-0 border border-surface-200 dark:border-surface-800"
        :class="mobileTab === 'editor' ? 'flex' : 'hidden lg:flex'"
      >
        <Tabs v-model:value="editorSection" scrollable class="flex-1 min-h-0 flex flex-col">
          <TabList>
            <Tab value="general">{{ t('designer.general') }}</Tab>
            <Tab value="header">{{ t('designer.headerHtml') }}</Tab>
            <Tab value="body">{{ t('designer.bodyHtml') }}</Tab>
            <Tab value="footer">{{ t('designer.footerHtml') }}</Tab>
            <Tab value="css">{{ t('designer.css') }}</Tab>
          </TabList>
          <TabPanels class="flex-1 min-h-0">
            <TabPanel value="general" class="h-full overflow-y-auto p-4">
              <div class="grid grid-cols-[repeat(auto-fill,minmax(11rem,1fr))] gap-4 max-w-2xl">
                <AppFormField field="name" :label="t('designer.templateName')" class="col-span-full"
                  ><InputText v-model="template.name" class="w-full"
                /></AppFormField>
                <AppFormField
                  field="page_size"
                  :label="t('designer.pageSize')"
                  class="col-span-full"
                  ><Select
                    v-model="template.page_size"
                    :options="pageSizes"
                    option-label="label"
                    option-value="value"
                    class="w-full"
                /></AppFormField>
                <AppFormField field="margin_top" :label="t('designer.marginTop')"
                  ><InputNumber v-model="template.margin_top" :min="0" fluid
                /></AppFormField>
                <AppFormField field="margin_right" :label="t('designer.marginRight')"
                  ><InputNumber v-model="template.margin_right" :min="0" fluid
                /></AppFormField>
                <AppFormField field="margin_bottom" :label="t('designer.marginBottom')"
                  ><InputNumber v-model="template.margin_bottom" :min="0" fluid
                /></AppFormField>
                <AppFormField field="margin_left" :label="t('designer.marginLeft')"
                  ><InputNumber v-model="template.margin_left" :min="0" fluid
                /></AppFormField>
                <AppFormField field="header_height" :label="t('designer.headerHeight')"
                  ><InputNumber v-model="template.header_height" :min="0" fluid
                /></AppFormField>
                <AppFormField field="footer_height" :label="t('designer.footerHeight')"
                  ><InputNumber v-model="template.footer_height" :min="0" fluid
                /></AppFormField>
                <p class="col-span-full text-sm text-surface-500">
                  {{ t('designer.marginsHint') }}
                </p>
                <AppFormField field="font_size" :label="t('designer.fontSize')"
                  ><InputNumber
                    v-model="template.font_size"
                    :min="1"
                    :max-fraction-digits="2"
                    fluid
                /></AppFormField>
                <AppFormField field="primary_font" :label="t('designer.primaryFont')"
                  ><InputText v-model="template.primary_font" class="w-full"
                /></AppFormField>
                <AppFormField field="secondary_font" :label="t('designer.secondaryFont')"
                  ><InputText v-model="template.secondary_font" class="w-full"
                /></AppFormField>
                <AppFormField
                  v-for="field in colorFields"
                  :key="field"
                  :field="field"
                  :label="t(`designer.${field}`)"
                >
                  <div class="flex gap-2">
                    <input
                      v-model="template[field]"
                      type="color"
                      :aria-label="t(`designer.${field}`)"
                      class="h-10 w-12 border border-surface-300 dark:border-surface-700"
                    /><InputText v-model="template[field]" class="flex-1 min-w-0" />
                  </div>
                </AppFormField>
              </div>
            </TabPanel>
            <TabPanel value="header" class="h-full">
              <AppCodeEditor ref="headerEditor" v-model="template.header_html" language="html" />
            </TabPanel>
            <TabPanel value="body" class="h-full">
              <AppCodeEditor ref="bodyEditor" v-model="template.body_html" language="html" />
            </TabPanel>
            <TabPanel value="footer" class="h-full">
              <AppCodeEditor ref="footerEditor" v-model="template.footer_html" language="html" />
            </TabPanel>
            <TabPanel value="css" class="h-full">
              <AppCodeEditor v-model="template.css" language="css" />
            </TabPanel>
          </TabPanels>
        </Tabs>
        <InvoiceVariableBrowser :groups="variableGroups" @insert="insertSnippet">
          <template #title>{{ t('designer.placeholders') }}</template>
        </InvoiceVariableBrowser>
      </div>
      <div
        class="flex-col flex-1 min-h-[70vh] lg:min-h-0 border border-surface-200 dark:border-surface-800"
        :class="mobileTab === 'preview' ? 'flex' : 'hidden lg:flex'"
      >
        <Message v-if="previewError" severity="warn" size="small" class="m-2">{{
          t('designer.previewStale', { error: previewError })
        }}</Message>
        <div v-if="pdfLoading" class="flex flex-1 items-center justify-center text-surface-500">
          <i class="iconify lucide--loader-circle animate-spin mr-2" />{{
            t('designer.generatingPdf')
          }}
        </div>
        <InvoicePreviewFrame
          v-else
          class="flex-1 min-h-0"
          :url="pdfBlobUrl ?? undefined"
          :html="previewHtml"
          :mode="previewMode"
        />
      </div>
    </div>
  </div>
  <AppLoadState
    v-else
    :failed="loadFailed"
    back-to="/templates?tab=templates"
    :back-label="t('nav.templates')"
  />
</template>
