<script setup lang="ts">
import { useTabQuery } from '../../composables/useTabQuery'
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
  mailKinds,
  mailTemplatesApi,
  settingsApi,
  templatesApi,
  textBlocksApi,
  type DocumentTemplate,
  type MailTemplate,
  type TextBlock,
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
const activeTab = useTabQuery('assignments', [
  'assignments',
  'templates',
  'mailTemplates',
  'textBlocks',
])
const rows = ref<DocumentTemplate[]>([])
const mailRows = ref<MailTemplate[]>([])
const mailNames = computed(() => new Map(mailRows.value.map((row) => [row.id, row.name])))
const newMailModal = ref<InstanceType<typeof AppModal>>()
const newMailForm = ref<{ name: string; base: string | null }>({ name: '', base: null })
const newTemplateModal = ref<InstanceType<typeof AppModal>>()
const newTemplateForm = ref({ name: '' })
const creatingTemplate = ref(false)
const textBlocks = ref<TextBlock[]>([])
const editingTextBlock = ref<TextBlock | null>(null)
const textBlockForm = ref<Partial<TextBlock>>({})
const loading = ref(true)
const assignments = ref<Record<string, string | null>>({})
// Every mail kind always has a template (the defaults to begin with).
const mailAssignments = ref<Record<string, string>>({})
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

async function loadMailTemplates() {
  mailRows.value = (await mailTemplatesApi.list('page_size=500&ordering=name')).results
}

async function loadTextBlocks() {
  const results = await textBlockPagination.fetchPage(textBlocksApi.list)
  if (results) textBlocks.value = results
}

async function load() {
  loading.value = true
  try {
    // The mail templates first: listing them creates missing defaults and assignments.
    await loadMailTemplates()
    const [, , settings] = await Promise.all([
      loadTemplates(),
      textBlockPagination.start(),
      settingsApi.get(),
    ])
    assignments.value = { ...(settings.template_assignments as Record<string, string | null>) }
    mailAssignments.value = {
      ...(settings.mail_template_assignments as Record<string, string>),
    }
  } catch (e) {
    notify.error(e)
  } finally {
    loading.value = false
  }
}

async function saveAssignments() {
  savingAssignments.value = true
  try {
    await settingsApi.update({
      template_assignments: assignments.value,
      mail_template_assignments: mailAssignments.value,
    })
    await loadMailTemplates()
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

async function duplicateTemplate(template: DocumentTemplate) {
  try {
    const copy = await templatesApi.duplicate(template.id)
    void router.push(`/templates/${copy.id}`)
  } catch (e) {
    notify.error(e)
  }
}

async function duplicateMailTemplate(template: MailTemplate) {
  try {
    const copy = await mailTemplatesApi.duplicate(template.id)
    void router.push(`/templates/mail/${copy.id}`)
  } catch (e) {
    notify.error(e)
  }
}

function removeMailTemplate(template: MailTemplate) {
  confirmDelete(async () => {
    await mailTemplatesApi.remove(template.id)
    await loadMailTemplates()
  })
}

// A new template builds on the base most templates use (the layout), if there is one.
function openNewMail() {
  const counts = new Map<string, number>()
  for (const row of mailRows.value)
    if (row.base) counts.set(row.base, (counts.get(row.base) ?? 0) + 1)
  const base = [...counts].sort((a, b) => b[1] - a[1])[0]?.[0] ?? null
  newMailForm.value = { name: '', base }
  newMailModal.value?.open()
}

async function createMailTemplate() {
  creatingTemplate.value = true
  try {
    const created = await mailTemplatesApi.create({
      name: newMailForm.value.name.trim(),
      base: newMailForm.value.base,
    })
    newMailModal.value?.close()
    void router.push(`/templates/mail/${created.id}`)
  } catch (e) {
    notify.error(e)
  } finally {
    creatingTemplate.value = false
  }
}

function openNewTemplate() {
  newTemplateForm.value = { name: '' }
  newTemplateModal.value?.open()
}

// Created only on confirm, so backing out leaves nothing behind.
async function createTemplate() {
  creatingTemplate.value = true
  try {
    const created = await templatesApi.create({
      name: newTemplateForm.value.name.trim(),
      body_html: '',
    })
    newTemplateModal.value?.close()
    void router.push(`/templates/${created.id}`)
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
    void router.push(`/templates/${imported.id}`)
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
          <Button
            :label="t('designer.importTemplate')"
            icon="iconify lucide--upload"
            @click="importInput?.click()"
          />
          <input
            ref="importInput"
            type="file"
            accept="application/json,.json"
            :aria-label="t('designer.importTemplate')"
            class="hidden"
            @change="importTemplate"
          />
          <Button
            :label="t('designer.newTemplate')"
            icon="iconify lucide--plus"
            @click="openNewTemplate"
          />
        </template>
        <Button
          v-else-if="activeTab === 'mailTemplates'"
          :label="t('designer.newMailTemplate')"
          icon="iconify lucide--plus"
          @click="openNewMail"
        />
        <Button
          v-else-if="activeTab === 'textBlocks'"
          :label="t('designer.newTextBlock')"
          icon="iconify lucide--plus"
          @click="openTextBlock()"
        />
      </template>
    </AppPageHeader>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="assignments">{{ t('designer.assignments') }}</Tab>
        <Tab value="templates">{{ t('designer.templates') }}</Tab>
        <Tab value="mailTemplates">{{ t('designer.mailTemplates') }}</Tab>
        <Tab value="textBlocks">{{ t('designer.textBlocks') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="assignments">
          <p class="text-sm text-surface-500 mb-4 pt-4">{{ t('designer.assignmentsHint') }}</p>
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-4xl">
            <section class="flex flex-col gap-4">
              <h2 class="font-semibold">{{ t('designer.assignmentsDocuments') }}</h2>
              <AppFormField
                v-for="rt in reportTypes"
                :key="rt"
                :field="rt"
                :label="t(`designer.reportTypes.${rt}`)"
                :required="rt === 'invoice'"
              >
                <!-- Invoices always have a template; the other types have none yet. -->
                <Select
                  v-model="assignments[rt]"
                  :options="rows"
                  option-label="name"
                  option-value="id"
                  :show-clear="rt !== 'invoice'"
                  class="w-full"
                />
              </AppFormField>
            </section>
            <section class="flex flex-col gap-4">
              <h2 class="font-semibold">{{ t('designer.assignmentsMails') }}</h2>
              <AppFormField
                v-for="kind in mailKinds"
                :key="kind"
                :field="kind"
                :label="t(`designer.mailKinds.${kind}`)"
                required
              >
                <Select
                  v-model="mailAssignments[kind]"
                  :options="mailRows"
                  option-label="name"
                  option-value="id"
                  class="w-full"
                />
              </AppFormField>
            </section>
          </div>
        </TabPanel>
        <TabPanel value="templates" class="pt-4">
          <AppDataTable
            :rows="rows"
            :loading="loading"
            :state-key="tableStateKeys.documentTemplates"
            @row-click="(r: DocumentTemplate) => router.push(`/templates/${r.id}`)"
          >
            <Column class="app-text" field="name" :header="t('common.name')" sortable />
            <Column field="page_size" :header="t('designer.pageSize')" sortable />
            <Column header-style="width: 7.5rem" :reorderable-column="false">
              <template #body="{ data }">
                <AppIconButton
                  icon="iconify lucide--copy"
                  :label="t('designer.duplicate')"
                  @click.stop="duplicateTemplate(data)"
                />
                <AppIconButton
                  icon="iconify lucide--download"
                  :href="templatesApi.exportUrl(data.id)"
                  download
                  :label="t('designer.exportTemplate')"
                  @click.stop
                />
                <!-- At least one template has to stay; the backend refuses deleting the last one. -->
                <AppIconButton
                  v-if="rows.length > 1"
                  icon="iconify lucide--trash-2"
                  severity="danger"
                  @click.stop="removeTemplate(data)"
                />
              </template>
            </Column>
          </AppDataTable>
        </TabPanel>
        <TabPanel value="mailTemplates" class="pt-4">
          <AppDataTable
            :rows="mailRows"
            :loading="loading"
            :state-key="tableStateKeys.mailTemplates"
            @row-click="(r: MailTemplate) => router.push(`/templates/mail/${r.id}`)"
          >
            <Column class="app-text" field="name" :header="t('common.name')" sortable />
            <Column class="app-text" :header="t('designer.mailBase')">
              <template #body="{ data }">{{ data.base ? mailNames.get(data.base) : '—' }}</template>
            </Column>
            <Column class="app-text" :header="t('designer.usedFor')">
              <template #body="{ data }">{{
                data.assigned_kinds
                  .map((kind: string) => t(`designer.mailKinds.${kind}`))
                  .join(', ')
              }}</template>
            </Column>
            <Column class="app-text" field="subject" :header="t('invoices.mailSubject')" hidden />
            <Column class="app-num" field="derived_count" :header="t('designer.derived')" />
            <Column header-style="width: 5.5rem" :reorderable-column="false">
              <template #body="{ data }">
                <AppIconButton
                  icon="iconify lucide--copy"
                  :label="t('designer.duplicate')"
                  @click.stop="duplicateMailTemplate(data)"
                />
                <!-- Assigned templates and bases of others stay; the backend refuses. -->
                <AppIconButton
                  v-if="!data.assigned_kinds.length && !data.derived_count"
                  icon="iconify lucide--trash-2"
                  severity="danger"
                  @click.stop="removeMailTemplate(data)"
                />
              </template>
            </Column>
          </AppDataTable>
        </TabPanel>
        <TabPanel value="textBlocks" class="pt-4">
          <AppDataTable
            :rows="textBlocks"
            :loading="textBlockPagination.loading.value"
            lazy
            :total-records="textBlockPagination.totalRecords.value"
            :first="textBlockPagination.first.value"
            :page-size="textBlockPagination.pageSize.value"
            :sort-field="textBlockPagination.sortField.value"
            :sort-order="textBlockPagination.sortOrder.value"
            :sort-options="textBlockSortOptions"
            :state-key="tableStateKeys.textBlocks"
            @state-restore="textBlockPagination.onRestore"
            @page="textBlockPagination.onPage"
            @sort="textBlockPagination.onSort"
            @row-click="openTextBlock"
          >
            <Column class="app-text" field="name" :header="t('common.name')" sortable />
            <Column field="key" :header="t('designer.textBlockKey')" sortable />
            <Column
              class="app-text"
              field="content"
              :header="t('designer.textBlockContent')"
              hidden
            />
            <Column :reorderable-column="false">
              <template #body="{ data }"
                ><AppIconButton
                  icon="iconify lucide--trash-2"
                  severity="danger"
                  @click.stop="removeTextBlock(data)"
              /></template>
            </Column>
          </AppDataTable>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <AppModal
      ref="newTemplateModal"
      :form="newTemplateForm"
      :title="t('designer.newTemplate')"
      :confirm-label="t('common.create')"
      :loading="creatingTemplate"
      @confirm="createTemplate"
    >
      <form @submit.prevent="createTemplate">
        <AppFormField field="name" :label="t('common.name')" required>
          <!-- eslint-disable-next-line vuejs-accessibility/no-autofocus -- the dialog's only field, opened on purpose to type a name. -->
          <InputText v-model="newTemplateForm.name" class="w-full" autofocus />
        </AppFormField>
      </form>
    </AppModal>

    <AppModal
      ref="newMailModal"
      :form="newMailForm"
      :title="t('designer.newMailTemplate')"
      :confirm-label="t('common.create')"
      :loading="creatingTemplate"
      @confirm="createMailTemplate"
    >
      <form class="flex flex-col gap-4" @submit.prevent="createMailTemplate">
        <AppFormField field="name" :label="t('common.name')" required>
          <!-- eslint-disable-next-line vuejs-accessibility/no-autofocus -- opened on purpose to type a name. -->
          <InputText v-model="newMailForm.name" class="w-full" autofocus />
        </AppFormField>
        <AppFormField field="base" :label="t('designer.mailBase')">
          <Select
            v-model="newMailForm.base"
            :options="mailRows"
            option-label="name"
            option-value="id"
            show-clear
            :placeholder="t('designer.noBase')"
            class="w-full"
          />
        </AppFormField>
      </form>
    </AppModal>

    <AppModal
      ref="textBlockModal"
      :form="textBlockForm"
      :title="t('designer.textBlock')"
      @confirm="saveTextBlock"
    >
      <div class="flex flex-col gap-4">
        <AppFormField field="name" :label="t('common.name')" required
          ><InputText v-model="textBlockForm.name" class="w-full"
        /></AppFormField>
        <AppFormField field="key" :label="t('designer.textBlockKey')" required>
          <InputText v-model="textBlockForm.key" class="w-full font-mono" />
          <small class="text-surface-500">{{ t('designer.textBlockKeyHint') }}</small>
        </AppFormField>
        <AppFormField field="content" :label="t('designer.textBlockContent')" required
          ><Textarea v-model="textBlockForm.content" rows="10" class="w-full font-mono"
        /></AppFormField>
        <p class="text-xs text-surface-500">
          <code v-text="`{{ text_blocks.${textBlockForm.key || 'key'} }}`" />
        </p>
      </div>
    </AppModal>
  </div>
</template>
