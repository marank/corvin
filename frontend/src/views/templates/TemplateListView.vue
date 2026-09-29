<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import Textarea from 'primevue/textarea'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppIconButton from '../../components/ui/AppIconButton.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppModal from '../../components/ui/AppModal.vue'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import Select from 'primevue/select'
import {
  settingsApi, templatesApi, textBlocksApi, type InvoiceTemplate, type TextBlock,
} from '../../api'
import { useNotify } from '../../composables/useNotify'
import { useConfirmDelete } from '../../composables/useConfirmDelete'

const { t } = useI18n()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const importInput = ref<HTMLInputElement>()
const textBlockModal = ref<InstanceType<typeof AppModal>>()
const activeTab = ref('assignments')
const rows = ref<InvoiceTemplate[]>([])
const textBlocks = ref<TextBlock[]>([])
const editingTextBlock = ref<TextBlock | null>(null)
const textBlockForm = ref<Partial<TextBlock>>({})
const loading = ref(true)
const assignments = ref<Record<string, string | null>>({})
const savingAssignments = ref(false)
const reportTypes = ['invoice', 'credit_note', 'quote', 'order', 'delivery_note', 'timesheet']

async function load() {
  const [templatePage, textBlockPage, settings] = await Promise.all([
    templatesApi.list(), textBlocksApi.list(), settingsApi.get(),
  ])
  rows.value = templatePage.results
  textBlocks.value = textBlockPage.results
  assignments.value = { ...settings.template_assignments as Record<string, string | null> }
  loading.value = false
}

async function saveAssignments() {
  savingAssignments.value = true
  try {
    await settingsApi.update({ template_assignments: assignments.value })
    notify.ok(t('common.save'))
  } catch (e) {
    notify.error(e)
  } finally {
    savingAssignments.value = false
  }
}

function openTextBlock(textBlock?: TextBlock) {
  editingTextBlock.value = textBlock ?? null
  textBlockForm.value = textBlock ? { ...textBlock } : {}
  textBlockModal.value?.open()
}

async function saveTextBlock() {
  try {
    if (editingTextBlock.value) {
      await textBlocksApi.update(editingTextBlock.value.id, textBlockForm.value)
    } else {
      await textBlocksApi.create(textBlockForm.value)
    }
    await load()
    textBlockModal.value?.close()
    textBlockForm.value = {}
  } catch (error) {
    notify.error(error)
  }
}

function removeTextBlock(textBlock: TextBlock) {
  confirmDelete(async () => {
    await textBlocksApi.remove(textBlock.id)
    textBlocks.value = textBlocks.value.filter((item) => item.id !== textBlock.id)
  })
}

function removeTemplate(template: InvoiceTemplate) {
  confirmDelete(async () => {
    await templatesApi.remove(template.id)
    rows.value = rows.value.filter((item) => item.id !== template.id)
  })
}

onMounted(load)

async function createTemplate() {
  try {
    const created = await templatesApi.create({ name: t('common.new'), body_html: '' })
    router.push(`/templates/${created.id}`)
  } catch (e) {
    notify.error(e)
  }
}

async function importTemplate(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const imported = await templatesApi.importTemplate(JSON.parse(await file.text()))
    await load()
    notify.ok(t('designer.importSuccess'))
    router.push(`/templates/${imported.id}`)
  } catch (error) {
    notify.error(error)
  } finally {
    input.value = ''
  }
}
</script>

<template>
  <div>
    <AppPageHeader :title="t('nav.templates')">
      <template #actions>
        <template v-if="activeTab === 'assignments'">
          <Button :label="t('common.save')" :loading="savingAssignments" @click="saveAssignments" />
        </template>
        <template v-else-if="activeTab === 'templates'">
          <Button :label="t('designer.importTemplate')" icon="pi pi-upload" @click="importInput?.click()" />
          <input ref="importInput" type="file" accept="application/json,.json" class="hidden" @change="importTemplate" />
          <Button :label="t('common.new')" icon="pi pi-plus" @click="createTemplate" />
        </template>
        <Button v-else-if="activeTab === 'textBlocks'" :label="t('common.new')" icon="pi pi-plus" @click="openTextBlock()" />
      </template>
    </AppPageHeader>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="assignments">{{ t('designer.assignments') }}</Tab>
        <Tab value="templates">{{ t('designer.templates') }}</Tab>
        <Tab value="textBlocks">{{ t('designer.textBlocks') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="assignments">
          <p class="text-sm text-surface-500 mb-4 pt-4">{{ t('designer.assignmentsHint') }}</p>
          <div class="flex flex-col gap-4 max-w-lg">
            <AppFormField v-for="rt in reportTypes" :key="rt" :label="t(`designer.reportTypes.${rt}`)">
              <Select
                v-model="assignments[rt]"
                :options="rows"
                option-label="name"
                option-value="id"
                :placeholder="t('designer.noTemplate')"
                show-clear
                class="w-full"
              />
            </AppFormField>
          </div>
        </TabPanel>
        <TabPanel value="templates">
          <AppDataTable :rows="rows" :loading="loading" @row-click="(r: InvoiceTemplate) => router.push(`/templates/${r.id}`)">
            <Column field="name" :header="t('common.name')" />
            <Column field="page_size" :header="t('designer.pageSize')" />
            <Column :header="t('common.actions')">
              <template #body="{ data }">
                <a :href="templatesApi.exportUrl(data.id)" download @click.stop>
                  <AppIconButton icon="pi pi-download" :aria-label="t('designer.exportTemplate')" />
                </a>
                <AppIconButton icon="pi pi-trash" severity="danger" @click.stop="removeTemplate(data)" />
              </template>
            </Column>
          </AppDataTable>
        </TabPanel>
        <TabPanel value="textBlocks">
          <AppDataTable :rows="textBlocks" :loading="loading" @row-click="openTextBlock">
            <Column field="name" :header="t('common.name')" />
            <Column field="key" :header="t('designer.textBlockKey')" />
            <Column :header="t('common.actions')">
              <template #body="{ data }"><AppIconButton icon="pi pi-trash" severity="danger" @click.stop="removeTextBlock(data)" /></template>
            </Column>
          </AppDataTable>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <AppModal ref="textBlockModal" :title="t('designer.textBlock')" @confirm="saveTextBlock">
      <div class="flex flex-col gap-4">
        <AppFormField :label="t('common.name')" required><InputText v-model="textBlockForm.name" class="w-full" /></AppFormField>
        <AppFormField :label="t('designer.textBlockKey')" required>
          <InputText v-model="textBlockForm.key" class="w-full font-mono" />
          <small class="text-surface-500">{{ t('designer.textBlockKeyHint') }}</small>
        </AppFormField>
        <AppFormField :label="t('designer.textBlockContent')" required><Textarea v-model="textBlockForm.content" rows="10" class="w-full font-mono" /></AppFormField>
        <p class="text-xs text-surface-500"><code v-text="`{{ text_blocks.${textBlockForm.key || 'key'} }}`" /></p>
      </div>
    </AppModal>
  </div>
</template>
