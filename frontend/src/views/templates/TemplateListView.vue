<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
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
  settingsApi, templatesApi, textBlocksApi, type DocumentTemplate, type TextBlock,
} from '../../api'
import { useNotify } from '../../composables/useNotify'
import { useConfirmDelete } from '../../composables/useConfirmDelete'
import { usePagination } from '../../composables/usePagination'
import { tableStateKeys } from '../../tableStateKeys'

const { t } = useI18n()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const importInput = ref<HTMLInputElement>()
const textBlockModal = ref<InstanceType<typeof AppModal>>()
const activeTab = ref('assignments')
const rows = ref<DocumentTemplate[]>([])
// Without an assignment the backend renders with the oldest template (or creates one).
const fallbackTemplate = computed(() => [...rows.value].sort((a, b) => a.created_at.localeCompare(b.created_at))[0])
const fallbackLabel = computed(() => fallbackTemplate.value
  ? t('designer.defaultTemplate', { name: fallbackTemplate.value.name })
  : t('designer.defaultTemplateAuto'))
const newTemplateModal = ref<InstanceType<typeof AppModal>>()
const newTemplateForm = ref({ name: '' })
const creatingTemplate = ref(false)
const textBlocks = ref<TextBlock[]>([])
const editingTextBlock = ref<TextBlock | null>(null)
const textBlockForm = ref<Partial<TextBlock>>({})
const loading = ref(true)
const assignments = ref<Record<string, string | null>>({})
const savingAssignments = ref(false)
const reportTypes = ['invoice', 'credit_note', 'quote', 'order', 'delivery_note', 'timesheet']
const textBlockPagination = usePagination(loadTextBlocks, 'name')
const textBlockSortOptions = [
  { label: t('common.name'), value: 'name' },
  { label: t('designer.textBlockKey'), value: 'key' },
]

onMounted(load)

async function loadTemplates() {
  rows.value = (await templatesApi.list('page_size=500&ordering=name')).results
}

async function loadTextBlocks() {
  const results = await textBlockPagination.fetchPage(textBlocksApi.list)
  if (results) textBlocks.value = results
}

async function load() {
  loading.value = true
  try {
    const [, , settings] = await Promise.all([
      loadTemplates(), textBlockPagination.start(), settingsApi.get(),
    ])
    assignments.value = { ...settings.template_assignments as Record<string, string | null> }
  } catch (e) {
    notify.error(e)
  } finally {
    loading.value = false
  }
}

async function saveAssignments() {
  savingAssignments.value = true
  try {
    await settingsApi.update({ template_assignments: assignments.value })
    notify.ok(t('common.saved'))
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
    await loadTextBlocks()
    textBlockModal.value?.close()
    notify.ok(t('common.saved'))
    textBlockForm.value = {}
  } catch (error) {
    notify.error(error)
  }
}

function removeTextBlock(textBlock: TextBlock) {
  confirmDelete(async () => {
    await textBlocksApi.remove(textBlock.id)
    await loadTextBlocks()
  })
}

function removeTemplate(template: DocumentTemplate) {
  confirmDelete(async () => {
    await templatesApi.remove(template.id)
    await loadTemplates()
  })
}

function openNewTemplate() {
  newTemplateForm.value = { name: '' }
  newTemplateModal.value?.open()
}

// Created only on confirm, so backing out leaves nothing behind.
async function createTemplate() {
  creatingTemplate.value = true
  try {
    const created = await templatesApi.create({ name: newTemplateForm.value.name.trim(), body_html: '' })
    newTemplateModal.value?.close()
    router.push(`/templates/${created.id}`)
  } catch (e) {
    notify.error(e)
  } finally {
    creatingTemplate.value = false
  }
}

async function importTemplate(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const imported = await templatesApi.importTemplate(JSON.parse(await file.text()))
    await loadTemplates()
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
          <Button :label="t('designer.newTemplate')" icon="pi pi-plus" @click="openNewTemplate" />
        </template>
        <Button v-else-if="activeTab === 'textBlocks'" :label="t('designer.newTextBlock')" icon="pi pi-plus" @click="openTextBlock()" />
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
                :placeholder="fallbackLabel"
                show-clear
                class="w-full"
              />
            </AppFormField>
          </div>
        </TabPanel>
        <TabPanel value="templates">
          <AppDataTable
            :rows="rows" :loading="loading"
            :state-key="tableStateKeys.documentTemplates"
            @row-click="(r: DocumentTemplate) => router.push(`/templates/${r.id}`)"
          >
            <Column class="app-text" field="name" :header="t('common.name')" sortable />
            <Column field="page_size" :header="t('designer.pageSize')" sortable />
            <Column :header="t('common.actions')" :reorderable-column="false">
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
          <AppDataTable
            :rows="textBlocks" :loading="textBlockPagination.loading.value" lazy
            :total-records="textBlockPagination.totalRecords.value" :first="textBlockPagination.first.value"
            :page-size="textBlockPagination.pageSize.value" :sort-field="textBlockPagination.sortField.value"
            :sort-order="textBlockPagination.sortOrder.value" :sort-options="textBlockSortOptions"
            :state-key="tableStateKeys.textBlocks" @state-restore="textBlockPagination.onRestore" @page="textBlockPagination.onPage" @sort="textBlockPagination.onSort" @row-click="openTextBlock"
          >
            <Column class="app-text" field="name" :header="t('common.name')" sortable />
            <Column field="key" :header="t('designer.textBlockKey')" sortable />
            <Column :header="t('common.actions')" :reorderable-column="false">
              <template #body="{ data }"><AppIconButton icon="pi pi-trash" severity="danger" @click.stop="removeTextBlock(data)" /></template>
            </Column>
          </AppDataTable>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <AppModal ref="newTemplateModal" :form="newTemplateForm" :title="t('designer.newTemplate')" :confirm-label="t('common.create')" :loading="creatingTemplate" @confirm="createTemplate">
      <form @submit.prevent="createTemplate">
        <AppFormField field="name" :label="t('common.name')" required><InputText v-model="newTemplateForm.name" class="w-full" autofocus /></AppFormField>
      </form>
    </AppModal>

    <AppModal ref="textBlockModal" :form="textBlockForm" :title="t('designer.textBlock')" @confirm="saveTextBlock">
      <div class="flex flex-col gap-4">
        <AppFormField field="name" :label="t('common.name')" required><InputText v-model="textBlockForm.name" class="w-full" /></AppFormField>
        <AppFormField :label="t('designer.textBlockKey')" required>
          <InputText v-model="textBlockForm.key" class="w-full font-mono" />
          <small class="text-surface-500">{{ t('designer.textBlockKeyHint') }}</small>
        </AppFormField>
        <AppFormField field="content" :label="t('designer.textBlockContent')" required><Textarea v-model="textBlockForm.content" rows="10" class="w-full font-mono" /></AppFormField>
        <p class="text-xs text-surface-500"><code v-text="`{{ text_blocks.${textBlockForm.key || 'key'} }}`" /></p>
      </div>
    </AppModal>
  </div>
</template>
