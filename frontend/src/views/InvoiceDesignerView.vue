<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import AppPageHeader from '../components/ui/AppPageHeader.vue'
import AppCodeEditor from '../components/ui/AppCodeEditor.vue'
import InvoicePreviewFrame from '../components/InvoicePreviewFrame.vue'
import InvoiceVariableBrowser, { type VariableGroup } from '../components/InvoiceVariableBrowser.vue'
import {
  companyImagesApi, templatesApi, textBlocksApi,
  type CompanyImage, type DocumentTemplate, type TextBlock,
} from '../api'
import { useNotify } from '../composables/useNotify'
import { useConfirmDelete } from '../composables/useConfirmDelete'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const id = route.params.id as string

const template = ref<DocumentTemplate | null>(null)
const saving = ref(false)
const previewKey = ref(0)
const previewMode = ref<'html' | 'pdf'>('html')
const previewModes = [
  { value: 'html' as const, label: 'HTML' },
  { value: 'pdf' as const, label: 'PDF' },
]
const pdfLoading = ref(false)
const pdfBlobUrl = ref<string | null>(null)
const pageSizes = [
  { value: 'A3', label: 'DIN A3 — 297 × 420 mm' },
  { value: 'A4', label: 'DIN A4 — 210 × 297 mm' },
  { value: 'A5', label: 'DIN A5 — 148 × 210 mm' },
  { value: 'LETTER', label: 'US Letter — 8.5 × 11 in' },
  { value: 'LEGAL', label: 'US Legal — 8.5 × 14 in' },
  { value: 'TABLOID', label: 'US Tabloid — 11 × 17 in' },
]
const mobileTab = ref('editor')
const editorSection = ref('general')
const mobileEditorSection = ref('general')
const headerEditor = ref<InstanceType<typeof AppCodeEditor>>()
const bodyEditor = ref<InstanceType<typeof AppCodeEditor>>()
const footerEditor = ref<InstanceType<typeof AppCodeEditor>>()
const mobileHeaderEditor = ref<InstanceType<typeof AppCodeEditor>>()
const mobileBodyEditor = ref<InstanceType<typeof AppCodeEditor>>()
const mobileFooterEditor = ref<InstanceType<typeof AppCodeEditor>>()
const images = ref<CompanyImage[]>([])
const textBlocks = ref<TextBlock[]>([])

const htmlPreviewUrl = computed(() => `${templatesApi.previewUrl(id)}?k=${previewKey.value}`)
const previewUrl = computed(() =>
  previewMode.value === 'pdf' && pdfBlobUrl.value ? pdfBlobUrl.value : htmlPreviewUrl.value,
)

async function loadPdfPreview() {
  pdfLoading.value = true
  try {
    // Revoke old blob
    if (pdfBlobUrl.value) {
      URL.revokeObjectURL(pdfBlobUrl.value)
      pdfBlobUrl.value = null
    }
    const res = await fetch(templatesApi.previewPdfUrl(id), { credentials: 'same-origin' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const blob = await res.blob()
    pdfBlobUrl.value = URL.createObjectURL(blob)
  } catch (e) {
    notify.error(e)
    previewMode.value = 'html'
  } finally {
    pdfLoading.value = false
  }
}

watch(previewMode, (mode) => {
  if (mode === 'pdf') loadPdfPreview()
})

const variableGroups = computed<VariableGroup[]>(() => [
  {
    label: t('designer.variableGroups.invoice'),
    entries: [
      'number', 'issue_date', 'due_date', 'status', 'subtotal', 'vat_rate',
      'vat_amount', 'total', 'currency', 'notes', 'amount_paid', 'remaining',
    ].map((field) => ({ label: field, code: `{{ invoice.${field} }}` })),
  },
  {
    label: t('designer.variableGroups.page'),
    entries: [
      'document_type', 'size', 'width', 'height', 'margin_top', 'margin_right', 'margin_bottom',
      'margin_left', 'font_size', 'primary_font', 'secondary_font',
      'primary_color', 'secondary_color', 'tertiary_color',
      'background_color', 'text_color',
    ].map((field) => ({ label: field, code: `{{ page.${field} }}` })),
  },
  {
    label: t('designer.variableGroups.customer'),
    entries: [
      'number', 'name', 'email', 'phone', 'website', 'vat_id',
      'buyer_reference', 'street', 'postal_code', 'city', 'country',
    ].map((field) => ({ label: field, code: `{{ customer.${field} }}` })),
  },
  {
    label: t('designer.variableGroups.company'),
    entries: [
      'company_name', 'street', 'postal_code', 'city', 'country', 'email',
      'phone', 'website', 'tax_id', 'vat_id', 'iban', 'bic', 'currency',
    ].map((field) => ({ label: field, code: `{{ company.${field} }}` })),
  },
  {
    label: t('designer.variableGroups.bankAccount'),
    entries: [
      'name', 'bank_name', 'account_holder', 'iban', 'bic',
    ].map((field) => ({ label: field, code: `{{ invoice.bank_account.${field} }}` })),
  },
  {
    label: t('designer.variableGroups.invoiceContacts'),
    entries: [
      { label: 'contact loop', code: '{% for contact in invoice_contacts %}\n{{ contact.name }}{% if not forloop.last %}, {% endif %}\n{% endfor %}' },
      { label: 'name', code: '{{ contact.name }}' },
      { label: 'role', code: '{{ contact.role }}' },
      { label: 'email', code: '{{ contact.email }}' },
      { label: 'phone', code: '{{ contact.phone }}' },
    ],
  },
  {
    label: t('designer.variableGroups.companyContacts'),
    entries: [
      { label: 'contact loop', code: '{% for contact in company_contacts %}\n{{ contact.name }} {{ contact.role }} {{ contact.email }} {{ contact.phone }}\n{% endfor %}' },
      { label: 'name', code: '{{ contact.name }}' },
      { label: 'role', code: '{{ contact.role }}' },
      { label: 'email', code: '{{ contact.email }}' },
      { label: 'phone', code: '{{ contact.phone }}' },
    ],
  },
  {
    label: t('designer.variableGroups.relations'),
    entries: [
      { label: 'project.number', code: '{{ project.number }}' },
      { label: 'project.name', code: '{{ project.name }}' },
      { label: 'contract.number', code: '{{ contract.number }}' },
      { label: 'contract.name', code: '{{ contract.name }}' },
    ],
  },
  {
    label: t('designer.variableGroups.formatting'),
    entries: [
      { label: 'date', code: '{% display_date invoice.issue_date %}' },
      { label: 'time', code: '{% display_time now %}' },
      { label: 'number', code: '{% display_number invoice.subtotal %}' },
      { label: 'money', code: '{% display_money invoice.total invoice.currency %}' },
    ],
  },
  {
    label: t('designer.variableGroups.lines'),
    entries: [
      { label: 'line loop', code: '{% for item in items %}\n{{ item.position }} {{ item.description }} {{ item.quantity }} {{ item.unit }} {% display_money item.total invoice.currency %}\n{% endfor %}' },
      { label: 'description', code: '{{ item.description }}' },
      { label: 'quantity', code: '{% display_number item.quantity %}' },
      { label: 'unit price', code: '{% display_money item.unit_price invoice.currency %}' },
      { label: 'total', code: '{% display_money item.total invoice.currency %}' },
    ],
  },
  {
    label: t('designer.variableGroups.textBlocks'),
    entries: textBlocks.value.map((block) => ({
      label: `${block.name} (${block.key})`,
      code: `{{ text_blocks.${block.key} }}`,
    })),
  },
  {
    label: t('designer.variableGroups.images'),
    entries: images.value.map((image) => ({
      label: image.name,
      code: `<img src="{{ images.${image.key} }}" alt="${image.name}">`,
    })),
  },
])

onMounted(async () => {
  const [invoiceTemplate, imagePage, textBlockPage] = await Promise.all([
    templatesApi.get(id), companyImagesApi.list(), textBlocksApi.list(),
  ])
  template.value = invoiceTemplate
  images.value = imagePage.results
  textBlocks.value = textBlockPage.results
})

function insertSnippet(code: string) {
  const mobile = window.innerWidth < 1024
  const section = mobile ? mobileEditorSection.value : editorSection.value
  const editors = mobile
    ? { header: mobileHeaderEditor.value, body: mobileBodyEditor.value, footer: mobileFooterEditor.value }
    : { header: headerEditor.value, body: bodyEditor.value, footer: footerEditor.value }
  const editor = editors[section as keyof typeof editors] ?? editors.body
  if (editor) editor.insert(code)
  else if (template.value) template.value.body_html += code
}

async function save() {
  if (!template.value) return
  saving.value = true
  try {
    template.value = await templatesApi.update(id, template.value)
    previewKey.value++
    if (previewMode.value === 'pdf') loadPdfPreview()
    notify.ok(t('common.save'))
  } catch (e) {
    notify.error(e)
  } finally {
    saving.value = false
  }
}

watch(() => template.value && [template.value.page_size, template.value.margin_top, template.value.margin_right, template.value.margin_bottom, template.value.margin_left], () => {
  // margins/size change → refresh preview after save only; keep manual
}, { deep: true })
</script>

<template>
  <div v-if="template" class="h-full flex flex-col">
    <AppPageHeader :title="template.name" :subtitle="t('designer.title')">
      <template #actions>
        <Button :label="t('common.delete')" text severity="danger" @click="confirmDelete(async () => { await templatesApi.remove(id); router.push('/templates') })" />
        <a :href="templatesApi.exportUrl(id)" download><Button :label="t('designer.exportTemplate')" icon="pi pi-download" severity="secondary" /></a>
        <SelectButton v-model="previewMode" :options="previewModes" option-label="label" option-value="value" :allow-empty="false" />
        <Button :label="t('common.save')" icon="pi pi-save" :loading="saving" @click="save" />
      </template>
    </AppPageHeader>

    <!-- Mobile: tabs -->
    <div class="lg:hidden flex-1 min-h-0 flex flex-col">
      <Tabs v-model:value="mobileTab" class="flex-1 min-h-0 flex flex-col">
        <TabList>
          <Tab value="editor">{{ t('designer.editor') }}</Tab>
          <Tab value="preview">{{ t('designer.preview') }}</Tab>
        </TabList>
        <TabPanels class="flex-1 min-h-0">
          <TabPanel value="editor" class="h-full">
            <Tabs v-model:value="mobileEditorSection">
              <TabList>
                <Tab value="general">{{ t('designer.general') }}</Tab>
                <Tab value="header">{{ t('designer.headerHtml') }}</Tab>
                <Tab value="body">{{ t('designer.bodyHtml') }}</Tab>
                <Tab value="footer">{{ t('designer.footerHtml') }}</Tab>
                <Tab value="css">CSS</Tab>
              </TabList>
              <TabPanels>
                <TabPanel value="general" class="h-[60vh] overflow-y-auto border border-surface-200 dark:border-surface-800 p-4">
                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl">
                    <label class="text-sm sm:col-span-2">{{ t('designer.templateName') }}<InputText v-model="template.name" class="w-full mt-1" /></label>
                    <label class="text-sm sm:col-span-2">{{ t('designer.pageSize') }}<Select v-model="template.page_size" :options="pageSizes" option-label="label" option-value="value" class="w-full mt-1" /></label>
                    <label class="text-sm">{{ t('designer.marginTop') }}<InputNumber v-model="template.margin_top" class="w-full mt-1" /></label>
                    <label class="text-sm">{{ t('designer.marginRight') }}<InputNumber v-model="template.margin_right" class="w-full mt-1" /></label>
                    <label class="text-sm">{{ t('designer.marginBottom') }}<InputNumber v-model="template.margin_bottom" class="w-full mt-1" /></label>
                    <label class="text-sm">{{ t('designer.marginLeft') }}<InputNumber v-model="template.margin_left" class="w-full mt-1" /></label>
                    <label class="text-sm">{{ t('designer.fontSize') }}<InputNumber v-model="template.font_size" :min="1" :max-fraction-digits="2" class="w-full mt-1" /></label>
                    <label class="text-sm">{{ t('designer.primaryFont') }}<InputText v-model="template.primary_font" class="w-full mt-1" /></label>
                    <label class="text-sm">{{ t('designer.secondaryFont') }}<InputText v-model="template.secondary_font" class="w-full mt-1" /></label>
                    <label v-for="field in ['primary_color', 'secondary_color', 'tertiary_color', 'background_color', 'text_color'] as const" :key="field" class="text-sm">
                      {{ t(`designer.${field}`) }}
                      <div class="flex gap-2 mt-1"><input v-model="template[field]" type="color" class="h-10 w-12 border border-surface-300 dark:border-surface-700" /><InputText v-model="template[field]" class="flex-1 min-w-0" /></div>
                    </label>
                  </div>
                </TabPanel>
                <TabPanel value="header" class="h-[60vh] border border-surface-200 dark:border-surface-800">
                  <AppCodeEditor ref="mobileHeaderEditor" v-model="template.header_html" language="html" />
                </TabPanel>
                <TabPanel value="body" class="h-[60vh] border border-surface-200 dark:border-surface-800">
                  <AppCodeEditor ref="mobileBodyEditor" v-model="template.body_html" language="html" />
                </TabPanel>
                <TabPanel value="footer" class="h-[60vh] border border-surface-200 dark:border-surface-800">
                  <AppCodeEditor ref="mobileFooterEditor" v-model="template.footer_html" language="html" />
                </TabPanel>
                <TabPanel value="css" class="h-[60vh] border border-surface-200 dark:border-surface-800">
                  <AppCodeEditor v-model="template.css" language="css" />
                </TabPanel>
              </TabPanels>
            </Tabs>
            <InvoiceVariableBrowser :groups="variableGroups" @insert="insertSnippet">
              <template #title>{{ t('designer.placeholders') }}</template>
            </InvoiceVariableBrowser>
          </TabPanel>
          <TabPanel value="preview" class="h-full min-h-96">
            <div v-if="pdfLoading" class="flex items-center justify-center h-full text-surface-500">
              <i class="pi pi-spin pi-spinner mr-2" />{{ t('designer.generatingPdf') }}
            </div>
            <InvoicePreviewFrame v-else :url="previewUrl" :mode="previewMode" />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>

    <!-- Desktop: split -->
    <div class="hidden lg:grid flex-1 min-h-0 grid-cols-2 gap-4">
      <div class="flex flex-col min-h-0 border border-surface-200 dark:border-surface-800">
        <Tabs v-model:value="editorSection" class="flex-1 min-h-0 flex flex-col">
          <TabList>
            <Tab value="general">{{ t('designer.general') }}</Tab>
            <Tab value="header">{{ t('designer.headerHtml') }}</Tab>
            <Tab value="body">{{ t('designer.bodyHtml') }}</Tab>
            <Tab value="footer">{{ t('designer.footerHtml') }}</Tab>
            <Tab value="css">CSS</Tab>
          </TabList>
          <TabPanels class="flex-1 min-h-0">
            <TabPanel value="general" class="h-full overflow-y-auto p-4">
              <div class="grid grid-cols-2 gap-4 max-w-2xl">
                <label class="text-sm col-span-2">{{ t('designer.templateName') }}<InputText v-model="template.name" class="w-full mt-1" /></label>
                <label class="text-sm col-span-2">{{ t('designer.pageSize') }}<Select v-model="template.page_size" :options="pageSizes" option-label="label" option-value="value" class="w-full mt-1" /></label>
                <label class="text-sm">{{ t('designer.marginTop') }}<InputNumber v-model="template.margin_top" class="w-full mt-1" /></label>
                <label class="text-sm">{{ t('designer.marginRight') }}<InputNumber v-model="template.margin_right" class="w-full mt-1" /></label>
                <label class="text-sm">{{ t('designer.marginBottom') }}<InputNumber v-model="template.margin_bottom" class="w-full mt-1" /></label>
                <label class="text-sm">{{ t('designer.marginLeft') }}<InputNumber v-model="template.margin_left" class="w-full mt-1" /></label>
                <label class="text-sm">{{ t('designer.fontSize') }}<InputNumber v-model="template.font_size" :min="1" :max-fraction-digits="2" class="w-full mt-1" /></label>
                <label class="text-sm">{{ t('designer.primaryFont') }}<InputText v-model="template.primary_font" class="w-full mt-1" /></label>
                <label class="text-sm">{{ t('designer.secondaryFont') }}<InputText v-model="template.secondary_font" class="w-full mt-1" /></label>
                <label v-for="field in ['primary_color', 'secondary_color', 'tertiary_color', 'background_color', 'text_color'] as const" :key="field" class="text-sm">
                  {{ t(`designer.${field}`) }}
                  <div class="flex gap-2 mt-1"><input v-model="template[field]" type="color" class="h-10 w-12 border border-surface-300 dark:border-surface-700" /><InputText v-model="template[field]" class="flex-1 min-w-0" /></div>
                </label>
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
      <div class="min-h-0 border border-surface-200 dark:border-surface-800">
        <div v-if="pdfLoading" class="flex items-center justify-center h-full text-surface-500">
          <i class="pi pi-spin pi-spinner mr-2" />{{ t('designer.generatingPdf') }}
        </div>
        <InvoicePreviewFrame v-else :url="previewUrl" :mode="previewMode" />
      </div>
    </div>
  </div>
</template>
