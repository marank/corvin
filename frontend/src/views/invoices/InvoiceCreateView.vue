<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Select from 'primevue/select'
import Steps from 'primevue/steps'
import Column from 'primevue/column'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppDateInput from '../../components/ui/AppDateInput.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppDurationDisplay from '../../components/ui/AppDurationDisplay.vue'
import CustomerSelect from '../../components/CustomerSelect.vue'
import ProjectSelect from '../../components/ProjectSelect.vue'
import { invoicesApi, timeEntriesApi, type TimeEntry } from '../../api'
import { useNotify } from '../../composables/useNotify'

const { t } = useI18n()
const router = useRouter()
const notify = useNotify()

const step = ref(0)
const customerId = ref<number | null>(null)
const projectId = ref<number | null>(null)
const dateFrom = ref<string | null>(null)
const dateTo = ref<string | null>(null)
const groupBy = ref('entry')
const eInvoiceFormat = ref('none')
const entries = ref<TimeEntry[]>([])
const creating = ref(false)

const groupBys = ['entry', 'day', 'project']
const formats = ['none', 'zugferd', 'xrechnung']
const steps = computed(() => [
  { label: t('projects.customer') },
  { label: t('time.title') },
  { label: t('invoices.title') },
])

watch([customerId, projectId, dateFrom, dateTo], async () => {
  if (!customerId.value) {
    entries.value = []
    return
  }
  const params = new URLSearchParams({
    project__customer: String(customerId.value),
    billable: 'true',
    invoice__isnull: 'true',
    contract__isnull: 'true',
    page_size: '500',
  })
  if (projectId.value) params.set('project', String(projectId.value))
  if (dateFrom.value) params.set('date__gte', dateFrom.value)
  if (dateTo.value) params.set('date__lte', dateTo.value)
  entries.value = (await timeEntriesApi.list(params.toString())).results
})

const totalHours = computed(() => entries.value.reduce((s, e) => s + e.duration_minutes, 0) / 60)

async function create() {
  if (!customerId.value) return
  creating.value = true
  try {
    const inv = await invoicesApi.consolidate({
      customer_id: customerId.value,
      project_id: projectId.value,
      date_from: dateFrom.value,
      date_to: dateTo.value,
      group_by: groupBy.value,
      e_invoice_format: eInvoiceFormat.value,
    })
    router.push(`/invoices/${inv.id}`)
  } catch (e) {
    notify.error(e)
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div>
    <AppPageHeader :title="t('invoices.new')" />
    <Steps :model="steps" :active-step="step" class="mb-6" :readonly="false" @update:active-step="(s: number) => step = s" />

    <div v-if="step === 0" class="flex flex-col gap-4 max-w-lg">
      <AppFormField :label="t('projects.customer')" required><CustomerSelect v-model="customerId" /></AppFormField>
      <AppFormField :label="t('nav.projects')"><ProjectSelect v-model="projectId" :customer-id="customerId" /></AppFormField>
      <div class="grid grid-cols-2 gap-3">
        <AppFormField :label="t('common.date') + ' ≥'"><AppDateInput v-model="dateFrom" /></AppFormField>
        <AppFormField :label="t('common.date') + ' ≤'"><AppDateInput v-model="dateTo" /></AppFormField>
      </div>
      <Button :label="t('common.confirm')" class="self-start" :disabled="!customerId" @click="step = 1" />
    </div>

    <div v-else-if="step === 1">
      <p class="text-sm text-surface-500 mb-3">{{ entries.length }} · {{ totalHours.toFixed(2) }}h</p>
      <AppDataTable :rows="entries">
        <Column field="date" :header="t('common.date')" />
        <Column field="project_name" :header="t('nav.projects')" />
        <Column field="description" :header="t('time.description')" />
        <Column :header="t('time.duration')">
          <template #body="{ data }"><AppDurationDisplay :minutes="data.duration_minutes" /></template>
        </Column>
      </AppDataTable>
      <div class="flex gap-2 mt-4">
        <Button :label="t('common.back')" text @click="step = 0" />
        <Button :label="t('common.confirm')" @click="step = 2" />
      </div>
    </div>

    <div v-else class="flex flex-col gap-4 max-w-lg">
      <AppFormField :label="t('invoices.groupBy')">
        <Select v-model="groupBy" :options="groupBys" class="w-full">
          <template #option="{ option }">{{ t(`invoices.groupBys.${option}`) }}</template>
          <template #value="{ value }">{{ t(`invoices.groupBys.${value}`) }}</template>
        </Select>
      </AppFormField>
      <AppFormField :label="t('invoices.eInvoice')">
        <Select v-model="eInvoiceFormat" :options="formats" class="w-full">
          <template #option="{ option }">{{ t(`invoices.eInvoiceFormats.${option}`) }}</template>
          <template #value="{ value }">{{ t(`invoices.eInvoiceFormats.${value}`) }}</template>
        </Select>
      </AppFormField>
      <div class="flex gap-2">
        <Button :label="t('common.back')" text @click="step = 1" />
        <Button :label="t('common.create')" icon="pi pi-check" :loading="creating" :disabled="!entries.length" @click="create" />
      </div>
    </div>
  </div>
</template>
