<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import ProgressBar from 'primevue/progressbar'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppMoneyDisplay from '../../components/ui/AppMoneyDisplay.vue'
import AppNumberDisplay from '../../components/ui/AppNumberDisplay.vue'
import AttachmentList from '../../components/AttachmentList.vue'
import CustomerSelect from '../../components/CustomerSelect.vue'
import { projectsApi, type Project } from '../../api'
import { useNotify } from '../../composables/useNotify'
import { useConfirmDelete } from '../../composables/useConfirmDelete'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const id = route.params.id as string
const project = ref<Project | null>(null)
const form = ref<Partial<Project>>({})
const saving = ref(false)
const statuses = ['active', 'on_hold', 'done']

async function load() {
  project.value = await projectsApi.get(id)
  form.value = { ...project.value }
}
onMounted(load)

async function save() {
  saving.value = true
  try {
    project.value = await projectsApi.update(id, form.value)
    notify.ok(t('common.save'))
  } catch (e) {
    notify.error(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div v-if="project">
    <AppPageHeader :title="project.name" :subtitle="project.customer_name">
      <template #actions>
        <Button :label="t('common.delete')" text severity="danger" @click="confirmDelete(async () => { await projectsApi.remove(id); router.push('/projects') })" />
        <Button :label="t('common.save')" :loading="saving" @click="save" />
      </template>
    </AppPageHeader>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl">
      <AppFormField :label="t('common.number')"><InputText v-model="form.number" class="w-full" readonly /></AppFormField>
      <AppFormField :label="t('projects.customer')"><CustomerSelect v-model="form.customer" /></AppFormField>
      <AppFormField :label="t('common.name')"><InputText v-model="form.name" class="w-full" /></AppFormField>
      <AppFormField :label="t('common.status')">
        <Select v-model="form.status" :options="statuses" class="w-full">
          <template #option="{ option }">{{ t(`projects.status.${option}`) }}</template>
          <template #value="{ value }">{{ value ? t(`projects.status.${value}`) : '' }}</template>
        </Select>
      </AppFormField>
      <AppFormField :label="t('customers.rounding')"><InputNumber v-model="form.rounding_increment_minutes" :min="0" class="w-full" /></AppFormField>
      <AppFormField :label="t('projects.budgetHours')"><InputNumber v-model="form.budget_hours" class="w-full" /></AppFormField>
      <AppFormField :label="t('projects.budgetAmount')"><InputNumber v-model="form.budget_amount" mode="currency" currency="EUR" class="w-full" /></AppFormField>
      <AppFormField :label="t('time.description')" class="md:col-span-2"><Textarea v-model="form.description" rows="3" class="w-full" /></AppFormField>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl mt-6">
      <div class="border border-surface-200 dark:border-surface-800 p-4">
        <div class="flex justify-between text-sm mb-1">
          <span>{{ t('projects.usedHours') }}</span>
          <span><AppNumberDisplay :value="project.used_hours" :minimum-fraction-digits="1" :maximum-fraction-digits="1" /> / <AppNumberDisplay :value="project.budget_hours" />h</span>
        </div>
        <ProgressBar :value="project.budget_hours_percent ?? 0" :show-value="false" :pt="{ value: { class: (project.budget_hours_percent ?? 0) >= 80 ? 'bg-red-500' : '' } }" />
      </div>
      <div class="border border-surface-200 dark:border-surface-800 p-4">
        <div class="flex justify-between text-sm mb-1">
          <span>{{ t('projects.usedAmount') }}</span>
          <span><AppMoneyDisplay :amount="project.used_amount" /> / <AppMoneyDisplay :amount="project.budget_amount" /></span>
        </div>
        <ProgressBar :value="project.budget_amount_percent ?? 0" :show-value="false" :pt="{ value: { class: (project.budget_amount_percent ?? 0) >= 80 ? 'bg-red-500' : '' } }" />
      </div>
    </div>

    <Tabs value="attachments" class="mt-6">
      <TabList><Tab value="attachments">{{ t('customers.attachments') }}</Tab></TabList>
      <TabPanels>
        <TabPanel value="attachments"><AttachmentList model="project" :object-id="id" /></TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>
