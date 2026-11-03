<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import AppPageHeader from '../components/ui/AppPageHeader.vue'
import AppDataTable from '../components/ui/AppDataTable.vue'
import AppIconButton from '../components/ui/AppIconButton.vue'
import AppDurationDisplay from '../components/ui/AppDurationDisplay.vue'
import AppDateTimeDisplay from '../components/ui/AppDateTimeDisplay.vue'
import AppDateInput from '../components/ui/AppDateInput.vue'
import AppModal from '../components/ui/AppModal.vue'
import CustomerSelect from '../components/CustomerSelect.vue'
import ProjectSelect from '../components/ProjectSelect.vue'
import TimeEntryForm from '../components/TimeEntryForm.vue'
import { timeTrackingApi, type TimeEntry } from '../api'
import { useTimerStore } from '../stores/timer'
import { useNotify } from '../composables/useNotify'
import { useConfirmDelete } from '../composables/useConfirmDelete'
import { usePagination } from '../composables/usePagination'
import { tableStateKeys } from '../tableStateKeys'

const { t } = useI18n()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const timer = useTimerStore()
const rows = ref<TimeEntry[]>([])
const modal = ref<InstanceType<typeof AppModal>>()
const editing = ref<TimeEntry | null>(null)
const pagination = usePagination(load, '-start_datetime')
const sortOptions = [
  { label: t('common.date'), value: 'start_datetime' },
  { label: t('projects.project'), value: 'project__name' },
  { label: t('projects.customer'), value: 'customer__name' },
  { label: t('time.duration'), value: 'duration_minutes' },
]

const filters = ref({
  customer: null as string | null,
  project: null as string | null,
  from: null as string | null,
  to: null as string | null,
  status: null as string | null,
})
const statuses = ['open', 'invoiced']
const hasFilters = computed(() => Object.values(filters.value).some((value) => value))
const summary = ref({ count: 0, total_minutes: 0 })

function filterParams() {
  const params = new URLSearchParams()
  const f = filters.value
  if (f.customer) params.set('customer', f.customer)
  if (f.project) params.set('project', f.project)
  if (f.from) params.set('start_datetime__date__gte', f.from)
  if (f.to) params.set('start_datetime__date__lte', f.to)
  if (f.status) params.set('invoice__isnull', f.status === 'open' ? 'true' : 'false')
  return params
}

function resetFilters() {
  filters.value = { customer: null, project: null, from: null, to: null, status: null }
}

onMounted(pagination.start)

async function load() {
  const params = filterParams()
  const [results, totals] = await Promise.all([
    pagination.fetchPage(timeTrackingApi.list, params),
    timeTrackingApi.summary(params.toString()),
  ])
  if (results) rows.value = results
  summary.value = totals
  timer.refresh()
}

watch(filters, () => pagination.refresh(), { deep: true })
watch(() => timer.version, () => load())

function openEdit(entry?: TimeEntry) {
  editing.value = entry ?? null
  modal.value?.open()
}

async function run(action: () => Promise<unknown>) {
  try {
    await action()
  } catch (e) {
    notify.error(e)
  }
}
</script>

<template>
  <div>
    <AppPageHeader :title="t('time.title')">
      <template #actions>
        <template v-if="timer.running">
          <Button v-if="timer.running.is_paused" :label="t('time.resumeTimer')" icon="pi pi-play" severity="secondary" outlined @click="run(timer.resume)" />
          <Button v-else :label="t('time.pauseTimer')" icon="pi pi-pause" severity="secondary" outlined @click="run(timer.pause)" />
          <Button :label="t('time.stopTimer')" icon="pi pi-stop" severity="danger" @click="run(timer.stop)" />
        </template>
        <Button v-else :label="t('time.startTimer')" icon="pi pi-play" @click="timer.requestStart()" />
        <Button :label="t('time.new')" icon="pi pi-plus" @click="openEdit()" />
      </template>
    </AppPageHeader>

    <div class="flex flex-wrap items-center gap-2 mb-3">
      <CustomerSelect v-model="filters.customer" :placeholder="t('time.allCustomers')" class="w-full! sm:w-52!" />
      <ProjectSelect v-model="filters.project" :customer-id="filters.customer" :placeholder="t('time.allProjects')" class="w-full! sm:w-52!" />
      <div class="flex gap-2 w-full sm:w-auto">
        <AppDateInput v-model="filters.from" :placeholder="t('time.from')" class="flex-1 sm:w-40! sm:flex-none" />
        <AppDateInput v-model="filters.to" :placeholder="t('time.to')" class="flex-1 sm:w-40! sm:flex-none" />
      </div>
      <Select v-model="filters.status" :options="statuses" :placeholder="t('time.allStatuses')" show-clear class="w-full sm:w-56">
        <template #option="{ option }">{{ t(`time.statuses.${option}`) }}</template>
        <template #value="{ value, placeholder }">
          <span v-if="value">{{ t(`time.statuses.${value}`) }}</span>
          <span v-else class="text-surface-500">{{ placeholder }}</span>
        </template>
      </Select>
      <AppIconButton v-if="hasFilters" icon="pi pi-filter-slash" :aria-label="t('time.resetFilters')" :title="t('time.resetFilters')" @click="resetFilters" />
      <span class="ml-auto text-sm text-surface-500 whitespace-nowrap">{{ t('time.entries', summary.count) }} · <AppDurationDisplay :minutes="summary.total_minutes" class="font-semibold text-surface-900 dark:text-surface-0" /></span>
    </div>

    <AppDataTable
      :rows="rows" :loading="pagination.loading.value" lazy selectable
      :total-records="pagination.totalRecords.value" :first="pagination.first.value"
      :page-size="pagination.pageSize.value" :sort-field="pagination.sortField.value"
      :sort-order="pagination.sortOrder.value" :sort-options="sortOptions"
      :state-key="tableStateKeys.timeTracking" @state-restore="pagination.onRestore" @page="pagination.onPage" @sort="pagination.onSort" @row-click="openEdit"
    >
      <Column field="start_datetime" :header="t('common.date')" sortable><template #body="{ data }"><AppDateTimeDisplay :value="data.start_datetime" /></template></Column>
      <Column :header="t('time.time')">
        <template #body="{ data }">
          <AppDateTimeDisplay :value="data.start_datetime" type="time" />–<AppDateTimeDisplay v-if="data.end_datetime" :value="data.end_datetime" type="time" />
        </template>
      </Column>
      <Column class="app-text" field="project_name" sort-field="project__name" :header="t('projects.project')" sortable />
      <Column class="app-text" field="customer_name" sort-field="customer__name" :header="t('projects.customer')" sortable />
      <Column class="app-text" field="description" :header="t('time.description')" />
      <Column class="app-num" field="duration_minutes" :header="t('time.duration')" sortable>
        <template #body="{ data }">
          <Tag v-if="data.is_running" :value="t('time.timerRunning')" severity="warn" />
          <AppDurationDisplay v-else :minutes="data.duration_minutes" />
        </template>
      </Column>
      <Column :header="t('time.billable')">
        <template #body="{ data }">
          <i v-if="data.billable" class="pi pi-check" />
        </template>
      </Column>
      <Column :header="t('common.status')">
        <template #body="{ data }">
          <Tag v-if="data.invoice" :value="t('time.invoiced')" severity="info" />
          <Tag v-else-if="data.contract" :value="data.contract_name" severity="secondary" />
        </template>
      </Column>
      <Column :reorderable-column="false">
        <template #body="{ data }"><AppIconButton v-if="!data.invoice" icon="pi pi-trash" severity="danger" @click.stop="confirmDelete(async () => { await timeTrackingApi.remove(data.id); load() })" /></template>
      </Column>
      <template #card="{ row }">
        <div class="flex justify-between items-center">
          <div>
            <div class="font-medium">{{ row.description || row.project_name || '—' }}</div>
            <div class="text-surface-500"><AppDateTimeDisplay :value="row.start_datetime" type="datetime" /> · {{ row.customer_name }}</div>
          </div>
          <AppDurationDisplay :minutes="row.duration_minutes" />
        </div>
      </template>
    </AppDataTable>

    <AppModal ref="modal" :title="editing ? t('time.editEntry') : t('time.new')" size="lg" :show-footer="false">
      <TimeEntryForm :entry="editing" @saved="modal?.close(); load()" @cancel="modal?.close()" />
    </AppModal>
  </div>
</template>
