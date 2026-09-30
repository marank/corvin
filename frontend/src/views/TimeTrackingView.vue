<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import AppPageHeader from '../components/ui/AppPageHeader.vue'
import AppDataTable from '../components/ui/AppDataTable.vue'
import AppIconButton from '../components/ui/AppIconButton.vue'
import AppDurationDisplay from '../components/ui/AppDurationDisplay.vue'
import AppDateTimeDisplay from '../components/ui/AppDateTimeDisplay.vue'
import AppModal from '../components/ui/AppModal.vue'
import TimeEntryForm from '../components/TimeEntryForm.vue'
import { timeTrackingApi, type TimeEntry } from '../api'
import { useTimerStore } from '../stores/timer'
import { useNotify } from '../composables/useNotify'
import { useConfirmDelete } from '../composables/useConfirmDelete'

const { t } = useI18n()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const timer = useTimerStore()
const rows = ref<TimeEntry[]>([])
const loading = ref(true)
const modal = ref<InstanceType<typeof AppModal>>()
const editing = ref<TimeEntry | null>(null)

const runningEntry = computed(() => rows.value.find((r) => r.is_running) ?? null)
const runningStart = computed(() => {
  if (!runningEntry.value) return null
  return new Date(runningEntry.value.start_datetime)
})

async function load() {
  loading.value = true
  rows.value = (await timeTrackingApi.list('page_size=500&ordering=-start_datetime')).results
  timer.refresh()
  loading.value = false
}
onMounted(load)

watch(() => timer.version, () => {
  load()
})

function openEdit(entry?: TimeEntry) {
  editing.value = entry ?? null
  modal.value?.open()
}

async function startTimer() {
  try {
    await timer.start()
    load()
  } catch (e) {
    notify.error(e)
  }
}

async function stopTimer() {
  if (!runningEntry.value) return
  try {
    await timer.stop()
    load()
  } catch (e) {
    notify.error(e)
  }
}

const elapsedText = computed(() => {
  const ms = timer.elapsed
  const s = Math.floor(ms / 1000)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
})

const startTimeText = computed(() => {
  if (!runningStart.value) return ''
  return runningStart.value.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
})
</script>

<template>
  <div>
    <AppPageHeader :title="t('time.title')">
      <template #actions>
        <template v-if="runningEntry">
          <Button
            :label="`${elapsedText} (${startTimeText})`"
            icon="pi pi-clock"
            severity="secondary"
            text
            disabled
          />
          <Button :label="t('time.stopTimer')" icon="pi pi-stop" severity="danger" @click="stopTimer" />
        </template>
        <Button v-else :label="t('time.startTimer')" icon="pi pi-play" @click="startTimer" />
        <Button :label="t('time.new')" icon="pi pi-plus" @click="openEdit()" />
      </template>
    </AppPageHeader>

    <AppDataTable :rows="rows" :loading="loading" @row-click="openEdit">
      <Column :header="t('time.start')"><template #body="{ data }"><AppDateTimeDisplay :value="data.start_datetime" type="datetime" /></template></Column>
      <Column :header="t('time.end')"><template #body="{ data }"><AppDateTimeDisplay v-if="data.end_datetime" :value="data.end_datetime" type="datetime" /><span v-else class="text-surface-500">—</span></template></Column>
      <Column field="project_name" :header="t('nav.projects')" />
      <Column field="customer_name" :header="t('projects.customer')" />
      <Column field="description" :header="t('time.description')" />
      <Column :header="t('time.duration')">
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
      <Column :header="t('common.actions')">
        <template #body="{ data }"><AppIconButton icon="pi pi-trash" severity="danger" @click.stop="confirmDelete(async () => { await timeTrackingApi.remove(data.id); load() })" /></template>
      </Column>
      <template #card="{ row }">
        <div class="flex justify-between items-center">
          <div>
            <div class="font-medium">{{ row.description || row.project_name }}</div>
            <div class="text-sm text-surface-500"><AppDateTimeDisplay :value="row.start_datetime" type="datetime" /> · {{ row.customer_name }}</div>
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
