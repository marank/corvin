<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import Checkbox from 'primevue/checkbox'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import AppPageHeader from '../components/ui/AppPageHeader.vue'
import AppFormField from '../components/ui/AppFormField.vue'
import InvoicePreviewFrame from '../components/InvoicePreviewFrame.vue'
import { templatesApi, type InvoiceTemplate } from '../api'
import { useNotify } from '../composables/useNotify'

const { t } = useI18n()
const route = useRoute()
const notify = useNotify()
const id = Number(route.params.id)

const template = ref<InvoiceTemplate | null>(null)
const saving = ref(false)
const previewKey = ref(0)
const pageSizes = ['A4', 'LETTER']
const mobileTab = ref('editor')

const previewUrl = computed(() => `${templatesApi.previewUrl(id)}?k=${previewKey.value}`)

const placeholders = [
  'invoice.number', 'invoice.issue_date', 'invoice.due_date', 'invoice.status',
  'customer.name', 'customer.street', 'customer.postal_code', 'customer.city', 'customer.buyer_reference',
  'company.name', 'company.street', 'company.vat_id', 'company.iban',
  'items', 'invoice.subtotal', 'invoice.vat_amount', 'invoice.total',
]

onMounted(async () => {
  template.value = await templatesApi.get(id)
})

async function save() {
  if (!template.value) return
  saving.value = true
  try {
    template.value = await templatesApi.update(id, template.value)
    previewKey.value++
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
        <Select v-model="template.page_size" :options="pageSizes" class="w-28" />
        <Button :label="t('common.save')" icon="pi pi-save" :loading="saving" @click="save" />
      </template>
    </AppPageHeader>

    <!-- Mobile: tabs -->
    <div class="lg:hidden flex-1 min-h-0 flex flex-col">
      <Tabs v-model:value="mobileTab" class="flex-1 min-h-0 flex flex-col">
        <TabList>
          <Tab value="editor">{{ t('designer.editor') }}</Tab>
          <Tab value="preview">{{ t('designer.preview') }}</Tab>
          <Tab value="mail">{{ t('designer.mailSubject') }}</Tab>
        </TabList>
        <TabPanels class="flex-1 min-h-0">
          <TabPanel value="editor" class="h-full">
            <Textarea v-model="template.body_html" class="w-full h-full font-mono text-sm" auto-resize :rows="30" />
          </TabPanel>
          <TabPanel value="preview" class="h-full min-h-96">
            <InvoicePreviewFrame :url="previewUrl" />
          </TabPanel>
          <TabPanel value="mail">
            <AppFormField :label="t('designer.mailSubject')"><InputText v-model="template.mail_subject" class="w-full" /></AppFormField>
            <AppFormField :label="t('designer.mailBody')" class="mt-3"><Textarea v-model="template.mail_body" rows="8" class="w-full" /></AppFormField>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>

    <!-- Desktop: split -->
    <div class="hidden lg:grid flex-1 min-h-0 grid-cols-2 gap-4">
      <div class="flex flex-col min-h-0 border border-surface-200 dark:border-surface-800">
        <div class="flex gap-3 p-2 border-b border-surface-200 dark:border-surface-800 text-sm items-center">
          <span class="text-surface-500">{{ t('designer.margins') }}:</span>
          <InputNumber v-model="template.margin_top" class="w-16" size="small" />
          <InputNumber v-model="template.margin_right" class="w-16" size="small" />
          <InputNumber v-model="template.margin_bottom" class="w-16" size="small" />
          <InputNumber v-model="template.margin_left" class="w-16" size="small" />
          <label class="flex items-center gap-1 ms-auto"><Checkbox v-model="template.is_default" binary /> default</label>
        </div>
        <Textarea v-model="template.body_html" class="flex-1 w-full font-mono text-sm border-0" />
        <Textarea v-model="template.css" class="w-full font-mono text-sm border-0 border-t border-surface-200 dark:border-surface-800" :rows="6" placeholder="CSS" />
        <details class="p-2 border-t border-surface-200 dark:border-surface-800 text-xs">
          <summary class="cursor-pointer text-surface-500">{{ t('designer.placeholders') }}</summary>
          <code v-for="p in placeholders" :key="p" class="inline-block mr-3 mt-1">{{ '{' + '{' + p + '}' + '}' }}</code>
        </details>
        <div class="p-2 border-t border-surface-200 dark:border-surface-800 grid grid-cols-1 gap-2">
          <InputText v-model="template.mail_subject" :placeholder="t('designer.mailSubject')" class="w-full" />
          <Textarea v-model="template.mail_body" :placeholder="t('designer.mailBody')" rows="3" class="w-full" />
        </div>
      </div>
      <div class="min-h-0 border border-surface-200 dark:border-surface-800">
        <InvoicePreviewFrame :url="previewUrl" />
      </div>
    </div>
  </div>
</template>
