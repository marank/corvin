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
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppModal from '../../components/ui/AppModal.vue'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import {
  templatesApi, textBlocksApi, type InvoiceTemplate, type TextBlock,
} from '../../api'
import { useNotify } from '../../composables/useNotify'

const { t } = useI18n()
const router = useRouter()
const notify = useNotify()
const importInput = ref<HTMLInputElement>()
const textBlockModal = ref<InstanceType<typeof AppModal>>()
const activeTab = ref('templates')
const rows = ref<InvoiceTemplate[]>([])
const textBlocks = ref<TextBlock[]>([])
const editingTextBlock = ref<TextBlock | null>(null)
const textBlockForm = ref<Partial<TextBlock>>({})
const loading = ref(true)

async function load() {
  const [templatePage, textBlockPage] = await Promise.all([
    templatesApi.list(), textBlocksApi.list(),
  ])
  rows.value = templatePage.results
  textBlocks.value = textBlockPage.results
  loading.value = false
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
  } catch (error) {
    notify.error(error)
  }
}

async function removeTextBlock(textBlock: TextBlock) {
  try {
    await textBlocksApi.remove(textBlock.id)
    textBlocks.value = textBlocks.value.filter((item) => item.id !== textBlock.id)
  } catch (error) {
    notify.error(error)
  }
}

onMounted(load)

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
        <template v-if="activeTab === 'templates'">
          <Button :label="t('designer.importTemplate')" icon="pi pi-upload" @click="importInput?.click()" />
          <input ref="importInput" type="file" accept="application/json,.json" class="hidden" @change="importTemplate" />
        </template>
        <Button v-else :label="t('common.new')" icon="pi pi-plus" @click="openTextBlock()" />
      </template>
    </AppPageHeader>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="templates">{{ t('designer.templates') }}</Tab>
        <Tab value="textBlocks">{{ t('designer.textBlocks') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="templates">
          <AppDataTable :rows="rows" :loading="loading" @row-click="(r: InvoiceTemplate) => router.push(`/templates/${r.id}`)">
            <Column field="name" :header="t('common.name')" />
            <Column field="page_size" :header="t('designer.pageSize')" />
            <Column :header="t('common.status')">
              <template #body="{ data }"><Tag v-if="data.is_default" value="default" severity="info" /></template>
            </Column>
            <Column :header="t('common.actions')">
              <template #body="{ data }">
                <a :href="templatesApi.exportUrl(data.id)" download @click.stop>
                  <Button icon="pi pi-download" text size="small" :aria-label="t('designer.exportTemplate')" />
                </a>
              </template>
            </Column>
          </AppDataTable>
        </TabPanel>
        <TabPanel value="textBlocks">
          <AppDataTable :rows="textBlocks" :loading="loading" @row-click="openTextBlock">
            <Column field="name" :header="t('common.name')" />
            <Column field="key" :header="t('designer.textBlockKey')" />
            <Column :header="t('common.actions')">
              <template #body="{ data }"><Button icon="pi pi-trash" text size="small" severity="danger" @click.stop="removeTextBlock(data)" /></template>
            </Column>
          </AppDataTable>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <AppModal ref="textBlockModal" :title="t('designer.textBlock')" @confirm="saveTextBlock">
      <div class="flex flex-col gap-4">
        <AppFormField :label="t('common.name')" required><InputText v-model="textBlockForm.name" class="w-full" /></AppFormField>
        <AppFormField :label="t('designer.textBlockKey')" required><InputText v-model="textBlockForm.key" class="w-full font-mono" /></AppFormField>
        <AppFormField :label="t('designer.textBlockContent')" required><Textarea v-model="textBlockForm.content" rows="10" class="w-full font-mono" /></AppFormField>
        <p class="text-xs text-surface-500"><code v-text="`{{ text_blocks.${textBlockForm.key || 'key'} }}`" /></p>
      </div>
    </AppModal>
  </div>
</template>
