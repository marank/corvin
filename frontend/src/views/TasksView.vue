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
import { usePagination } from '../composables/usePagination'
import { tableStateKeys } from '../tableStateKeys'

const { t } = useI18n()
const today = new Date().toLocaleDateString('sv') // YYYY-MM-DD in local time
const isOverdue = (task: { due_date: string | null; status: string }) =>
  !!task.due_date && task.due_date < today && task.status !== 'done'
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const rows = ref<Task[]>([])
const modal = ref<InstanceType<typeof AppModal>>()
const editing = ref<Task | null>(null)
const form = ref<Partial<Task>>({ priority: 'medium', status: 'open' })
const statusFilter = ref<string | null>(null)

const priorities = ['low', 'medium', 'high']
const statuses = ['open', 'in_progress', 'done']
const pagination = usePagination(load, 'position')
const sortOptions = [
  { label: '#', value: 'number' },
  { label: t('common.name'), value: 'title' },
  { label: t('projects.customer'), value: 'customer__name' },
  { label: t('projects.project'), value: 'project__name' },
  { label: t('tasks.dueDate'), value: 'due_date' },
  { label: t('tasks.priority'), value: 'priority' },
  { label: t('common.status'), value: 'status' },
]

onMounted(pagination.start)

async function load() {
  const params = new URLSearchParams()
  if (statusFilter.value) params.set('status', statusFilter.value)
  const results = await pagination.fetchPage(tasksApi.list, params)
  if (results) rows.value = results
}

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
  // Update locally first so the checkbox follows the bound status, and revert on failure.
  const previous = task.status
  task.status = previous === 'done' ? 'open' : 'done'
  try {
    await tasksApi.patch(task.id, { status: task.status })
  } catch (e) {
    task.status = previous
    notify.error(e)
  }
}
</script>

<template>
  <div>
    <AppPageHeader :title="t('tasks.title')">
      <template #actions>
        <Select v-model="statusFilter" :options="statuses" :placeholder="t('common.status')" show-clear class="w-40" @update:model-value="pagination.refresh">
          <template #option="{ option }">{{ t(`tasks.status.${option}`) }}</template>
          <template #value="{ value, placeholder }">
            <span v-if="value">{{ t(`tasks.status.${value}`) }}</span>
            <span v-else class="text-surface-500">{{ placeholder }}</span>
          </template>
        </Select>
        <Button :label="t('tasks.new')" icon="pi pi-plus" @click="openEdit()" />
      </template>
    </AppPageHeader>

    <AppDataTable
      :rows="rows" :loading="pagination.loading.value" lazy selectable
      :total-records="pagination.totalRecords.value" :first="pagination.first.value"
      :page-size="pagination.pageSize.value" :sort-field="pagination.sortField.value"
      :sort-order="pagination.sortOrder.value" :sort-options="sortOptions"
      :state-key="tableStateKeys.tasks" @state-restore="pagination.onRestore" @page="pagination.onPage" @sort="pagination.onSort" @row-click="openEdit"
    >
      <Column :header="''" class="w-8" :reorderable-column="false">
        <template #body="{ data }"><Checkbox :model-value="data.status === 'done'" binary @click.stop @change="toggleDone(data)" /></template>
      </Column>
      <Column field="number" header="#" sortable />
      <Column field="title" :header="t('common.name')" sortable style="min-width: 14rem" />
      <Column field="customer_name" sort-field="customer__name" :header="t('projects.customer')" sortable />
      <Column field="project_name" sort-field="project__name" :header="t('projects.project')" sortable />
      <Column field="due_date" :header="t('tasks.dueDate')" sortable>
        <template #body="{ data }"><AppDateTimeDisplay :value="data.due_date" :class="{ 'text-red-500 font-medium': isOverdue(data) }" /></template>
      </Column>
      <Column field="priority" :header="t('tasks.priority')" sortable>
        <template #body="{ data }"><AppStatusTag :status="data.priority" :label="t(`tasks.priorities.${data.priority}`)" /></template>
      </Column>
      <Column field="status" :header="t('common.status')" sortable>
        <template #body="{ data }"><AppStatusTag :status="data.status" :label="t(`tasks.status.${data.status}`)" /></template>
      </Column>
      <Column :header="t('common.actions')" :reorderable-column="false">
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

    <AppModal ref="modal" :title="editing ? t('common.edit') : t('tasks.new')" @confirm="save">
      <div class="flex flex-col gap-4">
        <AppFormField field="number" v-if="editing" :label="t('common.number')"><InputText v-model="form.number" class="w-full" readonly /></AppFormField>
        <AppFormField field="title" :label="t('common.name')" required><InputText v-model="form.title" class="w-full" /></AppFormField>
        <AppFormField field="customer" :label="t('projects.customer')"><CustomerSelect v-model="form.customer" /></AppFormField>
        <AppFormField field="project" :label="t('projects.project')"><ProjectSelect v-model="form.project" :customer-id="form.customer" /></AppFormField>
        <AppFormField field="description" :label="t('time.description')"><Textarea v-model="form.description" rows="2" class="w-full" /></AppFormField>
        <div class="grid grid-cols-3 gap-3">
          <AppFormField field="due_date" :label="t('tasks.dueDate')"><AppDateInput v-model="(form.due_date as any)" /></AppFormField>
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
