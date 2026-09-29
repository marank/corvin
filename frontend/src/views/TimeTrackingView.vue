<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import InputText from 'primevue/inputtext'
import AppPageHeader from '../components/ui/AppPageHeader.vue'
import AppDataTable from '../components/ui/AppDataTable.vue'
import AppIconButton from '../components/ui/AppIconButton.vue'
import AppDurationDisplay from '../components/ui/AppDurationDisplay.vue'
import AppDateTimeDisplay from '../components/ui/AppDateTimeDisplay.vue'
import AppModal from '../components/ui/AppModal.vue'
import TimeEntryForm from '../components/TimeEntryForm.vue'
import CustomerSelect from '../components/CustomerSelect.vue'
import ProjectSelect from '../components/ProjectSelect.vue'
import { timeEntriesApi, type TimeEntry } from '../api'
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
const timerCustomer = ref<string | null>(null)
const timerProject = ref<string | null>(null)
const timerDesc = ref('')

async function load() {
  loading.value = true
  rows.value = (await timeEntriesApi.list('page_size=500&ordering=-date,-start_time')).results
  loading.value = false
}
onMounted(load)

function openEdit(entry?: TimeEntry) {
  editing.value = entry ?? null
  modal.value?.open()
}

async function startTimer() {
  if (!timerCustomer.value) return
  try {
    await timer.start(timerCustomer.value, timerProject.value, timerDesc.value)
    load()
  } catch (e) {
    notify.error(e)
  }
}
</script>

<template>
  <div>
    <AppPageHeader :title="t('time.title')">
      <template #actions>
        <Button :label="t('time.new')" icon="pi pi-plus" @click="openEdit()" />
      </template>
    </AppPageHeader>

    <div class="border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-3 mb-4 flex flex-wrap items-center gap-3">
      <CustomerSelect v-model="timerCustomer" class="w-56" />
      <ProjectSelect v-model="timerProject" :customer-id="timerCustomer" class="w-56" />
      <InputText v-model="timerDesc" :placeholder="t('time.description')" class="flex-1 min-w-40" />
      <Button v-if="!timer.running" :label="t('time.startTimer')" icon="pi pi-play" :disabled="!timerCustomer" @click="startTimer" />
      <Button v-else :label="t('time.stopTimer')" icon="pi pi-stop" severity="danger" @click="timer.stop().then(load)" />
    </div>

    <AppDataTable :rows="rows" :loading="loading" @row-click="openEdit">
      <Column :header="t('common.date')"><template #body="{ data }"><AppDateTimeDisplay :value="data.date" /></template></Column>
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
        <template #body="{ data }"><AppIconButton icon="pi pi-trash" severity="danger" @click.stop="confirmDelete(async () => { await timeEntriesApi.remove(data.id); load() })" /></template>
      </Column>
      <template #card="{ row }">
        <div class="flex justify-between items-center">
          <div>
            <div class="font-medium">{{ row.description || row.project_name }}</div>
            <div class="text-sm text-surface-500"><AppDateTimeDisplay :value="row.date" /> · {{ row.customer_name }}</div>
          </div>
          <AppDurationDisplay :minutes="row.duration_minutes" />
        </div>
      </template>
    </AppDataTable>

    <AppModal ref="modal" :title="t('time.new')" size="lg" :show-footer="false">
      <TimeEntryForm :entry="editing" @saved="modal?.close(); load()" @cancel="modal?.close()" />
    </AppModal>
  </div>
</template>
