<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppStatusTag from '../../components/ui/AppStatusTag.vue'
import AppModal from '../../components/ui/AppModal.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import CustomerSelect from '../../components/CustomerSelect.vue'
import { projectsApi, type Project } from '../../api'
import { useNotify } from '../../composables/useNotify'

const { t } = useI18n()
const router = useRouter()
const notify = useNotify()
const rows = ref<Project[]>([])
const loading = ref(true)
const modal = ref<InstanceType<typeof AppModal>>()
const saving = ref(false)
const form = ref<Partial<Project>>({ status: 'active' })

const statuses = ['active', 'on_hold', 'done']

async function load() {
  loading.value = true
  rows.value = (await projectsApi.list('page_size=500')).results
  loading.value = false
}
onMounted(load)

async function save() {
  saving.value = true
  try {
    await projectsApi.create(form.value)
    modal.value?.close()
    notify.ok(t('projects.new'))
    load()
  } catch (e) {
    notify.error(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <AppPageHeader :title="t('projects.title')">
      <template #actions>
        <Button :label="t('projects.new')" icon="pi pi-plus" @click="form = { status: 'active' }; modal?.open()" />
      </template>
    </AppPageHeader>

    <AppDataTable :rows="rows" :loading="loading" @row-click="(r: Project) => router.push(`/projects/${r.id}`)">
      <Column field="name" :header="t('common.name')" />
      <Column field="customer_name" :header="t('projects.customer')" />
      <Column :header="t('common.status')">
        <template #body="{ data }"><AppStatusTag :status="data.status" :label="t(`projects.status.${data.status}`)" /></template>
      </Column>
      <Column :header="t('projects.usedHours')">
        <template #body="{ data }">{{ data.used_hours.toFixed(1) }}h</template>
      </Column>
      <Column :header="t('projects.budgetHours')">
        <template #body="{ data }">{{ data.budget_hours ?? '—' }}</template>
      </Column>
      <template #card="{ row }">
        <div class="flex justify-between">
          <span class="font-medium">{{ row.name }}</span>
          <AppStatusTag :status="row.status" :label="t(`projects.status.${row.status}`)" />
        </div>
        <div class="text-sm text-surface-500">{{ row.customer_name }}</div>
      </template>
    </AppDataTable>

    <AppModal ref="modal" :title="t('projects.new')" :loading="saving" @confirm="save">
      <div class="flex flex-col gap-4">
        <AppFormField :label="t('projects.customer')" required><CustomerSelect v-model="form.customer" /></AppFormField>
        <AppFormField :label="t('common.name')" required><InputText v-model="form.name" class="w-full" /></AppFormField>
        <AppFormField :label="t('time.description')"><Textarea v-model="form.description" rows="2" class="w-full" /></AppFormField>
        <div class="grid grid-cols-2 gap-3">
          <AppFormField :label="t('projects.budgetHours')"><InputNumber v-model="form.budget_hours" class="w-full" /></AppFormField>
          <AppFormField :label="t('projects.budgetAmount')"><InputNumber v-model="form.budget_amount" mode="currency" currency="EUR" class="w-full" /></AppFormField>
        </div>
        <AppFormField :label="t('common.status')">
          <Select v-model="form.status" :options="statuses" class="w-full">
            <template #option="{ option }">{{ t(`projects.status.${option}`) }}</template>
            <template #value="{ value }">{{ value ? t(`projects.status.${value}`) : '' }}</template>
          </Select>
        </AppFormField>
      </div>
    </AppModal>
  </div>
</template>
