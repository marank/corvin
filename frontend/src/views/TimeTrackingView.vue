<script setup lang="ts">
import AppEnumSelect from '../components/ui/AppEnumSelect.vue'
import { computed, onMounted, ref, watch } from 'vue'
import dayjs from 'dayjs'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import AppPageHeader from '../components/ui/AppPageHeader.vue'
import AppDataTable from '../components/ui/AppDataTable.vue'
import AppIconButton from '../components/ui/AppIconButton.vue'
import AppDurationDisplay from '../components/ui/AppDurationDisplay.vue'
import AppDateTimeDisplay from '../components/ui/AppDateTimeDisplay.vue'
import AppDateInput from '../components/ui/AppDateInput.vue'
import AppFormField from '../components/ui/AppFormField.vue'
import AppFilterBar, { type ActiveFilter } from '../components/ui/AppFilterBar.vue'
import AppModal from '../components/ui/AppModal.vue'
import CustomerSelect from '../components/CustomerSelect.vue'
import ProjectSelect from '../components/ProjectSelect.vue'
import TimeEntryForm from '../components/TimeEntryForm.vue'
import { timeTrackingApi, type TimeEntry } from '../api'
import { useTimerStore } from '../stores/timer'
import { useFormattingStore } from '../stores/formatting'
import { useQueryFilters } from '../composables/useQueryFilters'
import { useNotify } from '../composables/useNotify'
import { useConfirmDelete } from '../composables/useConfirmDelete'
import { usePagination } from '../composables/usePagination'
import { tableStateKeys } from '../tableStateKeys'

const { t, locale } = useI18n()
const weekday = (day: string) =>
  new Date(`${day}T12:00:00`).toLocaleDateString(locale.value, { weekday: 'short' })
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const timer = useTimerStore()
type DayRow = TimeEntry & { day: string }
const rows = ref<DayRow[]>([])
// Day groups with totals, only while the list is sorted by date (otherwise days are scattered).
const groupByDay = computed(() => pagination.sortField.value === 'start_datetime')
const dayTotals = computed(() => {
  const totals: Record<string, number> = {}
  for (const row of rows.value) totals[row.day] = (totals[row.day] ?? 0) + row.duration_minutes
  return totals
})
const modal = ref<InstanceType<typeof AppModal>>()

function onEntrySaved() {
  modal.value?.close()
  void load()
}
const entryForm = ref<InstanceType<typeof TimeEntryForm>>()
const editing = ref<TimeEntry | null>(null)
const pagination = usePagination(load, '-start_datetime')
const sortOptions = [
  { label: t('common.date'), value: 'start_datetime' },
  { label: t('projects.project'), value: 'project__name' },
  { label: t('projects.customer'), value: 'customer__name' },
  { label: t('time.duration'), value: 'duration_minutes' },
]

const preset = useQueryFilters()
// The dashboard links here with ?status=open (uninvoiced) or ?from=<monday> (this week).
const query = useRoute().query
const queryString = (value: unknown) => (typeof value === 'string' && value ? value : null)
const filters = ref({
  customer: preset.customer,
  project: preset.project,
  from: queryString(query.from),
  to: null as string | null,
  status: ['open', 'invoiced'].includes(queryString(query.status) ?? '')
    ? queryString(query.status)
    : null,
})
const statuses = ['open', 'invoiced']
const summary = ref({ count: 0, total_minutes: 0 })
const formatting = useFormattingStore()
// Names for the filter chips: from the URL preset, then from the selects' select events.
const filterNames = preset.names

const activeFilters = computed<ActiveFilter[]>(() => {
  const f = filters.value
  const date = (value: string) => dayjs(value).format(formatting.dateFormat)
  const active: ActiveFilter[] = []
  if (f.customer)
    active.push({
      key: 'customer',
      label: t('projects.customer'),
      value: filterNames.value.customer,
    })
  if (f.project)
    active.push({ key: 'project', label: t('projects.project'), value: filterNames.value.project })
  if (f.from || f.to) {
    active.push({
      key: 'period',
      label: t('time.period'),
      value: `${f.from ? date(f.from) : '…'} – ${f.to ? date(f.to) : '…'}`,
    })
  }
  if (f.status)
    active.push({ key: 'status', label: t('common.status'), value: t(`time.statuses.${f.status}`) })
  return active
})

function removeFilter(key: string) {
  if (key === 'period') {
    filters.value.from = null
    filters.value.to = null
  } else {
    filters.value[key as 'customer' | 'project' | 'status'] = null
  }
}

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
  if (results)
    rows.value = results.map((entry) => ({
      ...entry,
      day: dayjs(entry.start_datetime).format('YYYY-MM-DD'),
    }))
  summary.value = totals
  void timer.refresh()
}

watch(filters, () => pagination.refresh(), { deep: true })
watch(
  () => timer.version,
  () => load(),
)

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
          <Button
            v-if="timer.running.is_paused"
            :label="t('time.resumeTimer')"
            icon="pi pi-play"
            severity="secondary"
            outlined
            @click="run(timer.resume)"
          />
          <Button
            v-else
            :label="t('time.pauseTimer')"
            icon="pi pi-pause"
            severity="secondary"
            outlined
            @click="run(timer.pause)"
          />
          <Button
            :label="t('time.stopTimer')"
            icon="pi pi-stop"
            severity="danger"
            @click="run(timer.stop)"
          />
        </template>
        <Button
          v-else
          :label="t('time.startTimer')"
          icon="pi pi-play"
          @click="timer.requestStart()"
        />
        <Button :label="t('time.new')" icon="pi pi-plus" @click="openEdit()" />
      </template>
    </AppPageHeader>

    <AppDataTable
      :rows="rows"
      :loading="pagination.loading.value"
      lazy
      selectable
      :delete-row="(row) => timeTrackingApi.remove(row.id)"
      @bulk-deleted="load"
      :total-records="pagination.totalRecords.value"
      :first="pagination.first.value"
      :page-size="pagination.pageSize.value"
      :sort-field="pagination.sortField.value"
      :sort-order="pagination.sortOrder.value"
      :sort-options="sortOptions"
      :state-key="tableStateKeys.timeTracking"
      @state-restore="pagination.onRestore"
      @page="pagination.onPage"
      @sort="pagination.onSort"
      @row-click="openEdit"
      :group-field="groupByDay ? 'day' : undefined"
    >
      <template #groupheader="{ data }">
        <div class="flex items-center gap-3 text-sm font-medium">
          <span>{{ weekday(data.day) }}, {{ dayjs(data.day).format(formatting.dateFormat) }}</span>
          <span class="text-surface-500 font-normal tabular-nums"
            ><AppDurationDisplay :minutes="dayTotals[data.day] ?? null"
          /></span>
        </div>
      </template>
      <template #toolbar>
        <AppFilterBar :active="activeFilters" @remove="removeFilter" @clear="resetFilters">
          <AppFormField :label="t('projects.customer')">
            <CustomerSelect
              v-model="filters.customer"
              :placeholder="t('common.allCustomers')"
              @select="(c) => (filterNames.customer = c?.name ?? '')"
            />
          </AppFormField>
          <AppFormField :label="t('projects.project')">
            <ProjectSelect
              v-model="filters.project"
              :customer-id="filters.customer"
              :placeholder="t('common.allProjects')"
              @select="(p) => (filterNames.project = p?.name ?? '')"
            />
          </AppFormField>
          <AppFormField :label="t('time.period')">
            <div class="grid grid-cols-2 gap-2">
              <AppDateInput v-model="filters.from" :placeholder="t('time.from')" />
              <AppDateInput v-model="filters.to" :placeholder="t('time.to')" />
            </div>
          </AppFormField>
          <AppFormField :label="t('common.status')">
            <AppEnumSelect
              v-model="filters.status"
              :options="statuses"
              label-prefix="time.statuses"
              :placeholder="t('common.all')"
              show-clear
              class="w-full"
            />
          </AppFormField>
          <template #end>
            <span class="text-sm text-surface-500 whitespace-nowrap"
              >{{ t('time.entries', summary.count) }} ·
              <AppDurationDisplay
                :minutes="summary.total_minutes"
                class="font-semibold text-surface-900 dark:text-surface-0"
            /></span>
          </template>
        </AppFilterBar>
      </template>
      <Column field="start_datetime" :header="t('common.date')" sortable
        ><template #body="{ data }"><AppDateTimeDisplay :value="data.start_datetime" /></template
      ></Column>
      <Column :header="t('time.time')">
        <template #body="{ data }">
          <AppDateTimeDisplay :value="data.start_datetime" type="time" />–<AppDateTimeDisplay
            v-if="data.end_datetime"
            :value="data.end_datetime"
            type="time"
          />
        </template>
      </Column>
      <Column
        class="app-text"
        field="project_name"
        sort-field="project__name"
        :header="t('projects.project')"
        sortable
      />
      <Column
        class="app-text"
        field="customer_name"
        sort-field="customer__name"
        :header="t('projects.customer')"
        sortable
      />
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
      <Column :header="t('time.invoiced')">
        <template #body="{ data }">
          <router-link
            v-if="data.invoice"
            :to="`/invoices/${data.invoice}`"
            class="text-primary"
            @click.stop
            >{{ data.invoice_number || t('time.invoiced') }}</router-link
          >
        </template>
      </Column>
      <Column class="app-text" field="contract_name" :header="t('invoices.contract')" />
      <Column :reorderable-column="false">
        <template #body="{ data }"
          ><AppIconButton
            v-if="!data.invoice"
            icon="pi pi-trash"
            severity="danger"
            @click.stop="
              confirmDelete(async () => {
                await timeTrackingApi.remove(data.id)
                load()
              })
            "
        /></template>
      </Column>
      <template #card="{ row }">
        <div class="flex justify-between items-center">
          <div>
            <div class="font-medium">{{ row.description || row.project_name || '—' }}</div>
            <div class="text-surface-500">
              <AppDateTimeDisplay :value="row.start_datetime" type="datetime" /> ·
              {{ row.customer_name }}
            </div>
          </div>
          <AppDurationDisplay :minutes="row.duration_minutes" />
        </div>
      </template>
    </AppDataTable>

    <AppModal
      ref="modal"
      :form="entryForm?.state"
      :loading="entryForm?.saving"
      :title="editing ? t('time.editEntry') : t('time.new')"
      size="lg"
      @confirm="entryForm?.save()"
    >
      <TimeEntryForm ref="entryForm" :entry="editing" @saved="onEntrySaved" />
    </AppModal>
  </div>
</template>
