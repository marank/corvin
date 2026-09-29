<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import Checkbox from 'primevue/checkbox'
import AppPageHeader from '../components/ui/AppPageHeader.vue'
import AppDataTable from '../components/ui/AppDataTable.vue'
import AppIconButton from '../components/ui/AppIconButton.vue'
import AppStatusTag from '../components/ui/AppStatusTag.vue'
import AppModal from '../components/ui/AppModal.vue'
import AppFormField from '../components/ui/AppFormField.vue'
import AppDateInput from '../components/ui/AppDateInput.vue'
import AppDateTimeDisplay from '../components/ui/AppDateTimeDisplay.vue'
import CustomerSelect from '../components/CustomerSelect.vue'
import ProjectSelect from '../components/ProjectSelect.vue'
import { tasksApi, type Task } from '../api'
import { useNotify } from '../composables/useNotify'
import { useConfirmDelete } from '../composables/useConfirmDelete'

const { t } = useI18n()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const rows = ref<Task[]>([])
const loading = ref(true)
const modal = ref<InstanceType<typeof AppModal>>()
const editing = ref<Task | null>(null)
const form = ref<Partial<Task>>({ priority: 'medium', status: 'open' })
const statusFilter = ref<string | null>(null)

const priorities = ['low', 'medium', 'high']
const statuses = ['open', 'in_progress', 'done']

async function load() {
  loading.value = true
  const p = statusFilter.value ? `status=${statusFilter.value}&` : ''
  rows.value = (await tasksApi.list(`${p}page_size=500`)).results
  loading.value = false
}
onMounted(load)

function openEdit(task?: Task) {
  editing.value = task ?? null
  form.value = task
    ? { ...task }
    : { priority: 'medium', status: 'open' }
  modal.value?.open()
}

async function save() {
  try {
    if (editing.value) await tasksApi.update(editing.value.id, form.value)
    else await tasksApi.create(form.value)
    modal.value?.close()
    load()
  } catch (e) {
    notify.error(e)
  }
}

async function toggleDone(task: Task) {
  await tasksApi.update(task.id, { status: task.status === 'done' ? 'open' : 'done' })
  load()
}
</script>

<template>
  <div>
    <AppPageHeader :title="t('tasks.title')">
      <template #actions>
        <Select v-model="statusFilter" :options="statuses" :placeholder="t('common.status')" show-clear class="w-40" @update:model-value="load">
          <template #option="{ option }">{{ t(`tasks.status.${option}`) }}</template>
          <template #value="{ value }">{{ value ? t(`tasks.status.${value}`) : '' }}</template>
        </Select>
        <Button :label="t('tasks.new')" icon="pi pi-plus" @click="openEdit()" />
      </template>
    </AppPageHeader>

    <AppDataTable :rows="rows" :loading="loading" @row-click="openEdit">
      <Column :header="''" class="w-8">
        <template #body="{ data }"><Checkbox :model-value="data.status === 'done'" binary @click.stop @change="toggleDone(data)" /></template>
      </Column>
      <Column field="number" header="#" />
      <Column field="title" :header="t('common.name')" />
      <Column field="customer_name" :header="t('projects.customer')" />
      <Column field="project_name" :header="t('nav.projects')" />
      <Column :header="t('tasks.dueDate')"><template #body="{ data }"><AppDateTimeDisplay :value="data.due_date" /></template></Column>
      <Column :header="t('tasks.priority')">
        <template #body="{ data }"><AppStatusTag :status="data.priority" :label="t(`tasks.priorities.${data.priority}`)" /></template>
      </Column>
      <Column :header="t('common.status')">
        <template #body="{ data }"><AppStatusTag :status="data.status" :label="t(`tasks.status.${data.status}`)" /></template>
      </Column>
      <Column :header="t('common.actions')">
        <template #body="{ data }"><AppIconButton icon="pi pi-trash" severity="danger" @click.stop="confirmDelete(async () => { await tasksApi.remove(data.id); load() })" /></template>
      </Column>
      <template #card="{ row }">
        <div class="flex items-center gap-2">
          <Checkbox :model-value="row.status === 'done'" binary @click.stop @change="toggleDone(row)" />
          <span class="font-medium flex-1" :class="row.status === 'done' ? 'line-through' : ''">{{ row.title }}</span>
          <AppStatusTag :status="row.priority" :label="t(`tasks.priorities.${row.priority}`)" />
        </div>
      </template>
    </AppDataTable>

    <AppModal ref="modal" :title="t('tasks.new')" @confirm="save">
      <div class="flex flex-col gap-4">
        <AppFormField v-if="editing" :label="t('common.number')"><InputText v-model="form.number" class="w-full" readonly /></AppFormField>
        <AppFormField :label="t('common.name')" required><InputText v-model="form.title" class="w-full" /></AppFormField>
        <AppFormField :label="t('projects.customer')"><CustomerSelect v-model="form.customer" /></AppFormField>
        <AppFormField :label="t('nav.projects')"><ProjectSelect v-model="form.project" :customer-id="form.customer" /></AppFormField>
        <AppFormField :label="t('time.description')"><Textarea v-model="form.description" rows="2" class="w-full" /></AppFormField>
        <div class="grid grid-cols-3 gap-3">
          <AppFormField :label="t('tasks.dueDate')"><AppDateInput v-model="(form.due_date as any)" /></AppFormField>
          <AppFormField :label="t('tasks.priority')">
            <Select v-model="form.priority" :options="priorities" class="w-full">
              <template #option="{ option }">{{ t(`tasks.priorities.${option}`) }}</template>
              <template #value="{ value }">{{ value ? t(`tasks.priorities.${value}`) : '' }}</template>
            </Select>
          </AppFormField>
          <AppFormField :label="t('common.status')">
            <Select v-model="form.status" :options="statuses" class="w-full">
              <template #option="{ option }">{{ t(`tasks.status.${option}`) }}</template>
              <template #value="{ value }">{{ value ? t(`tasks.status.${value}`) : '' }}</template>
            </Select>
          </AppFormField>
        </div>
      </div>
    </AppModal>
  </div>
</template>
