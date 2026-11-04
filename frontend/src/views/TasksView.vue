<script setup lang="ts">
import AppEnumSelect from '../components/ui/AppEnumSelect.vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import AppPageHeader from '../components/ui/AppPageHeader.vue'
import AppDataTable from '../components/ui/AppDataTable.vue'
import AppIconButton from '../components/ui/AppIconButton.vue'
import AppStatusTag from '../components/ui/AppStatusTag.vue'
import AppPriority from '../components/ui/AppPriority.vue'
import AppModal from '../components/ui/AppModal.vue'
import AppFormField from '../components/ui/AppFormField.vue'
import AppFilterBar, { type ActiveFilter } from '../components/ui/AppFilterBar.vue'
import { useQueryFilters } from '../composables/useQueryFilters'
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
const preset = useQueryFilters()
const filters = ref({ customer: preset.customer, project: preset.project, status: null as string | null, priority: null as string | null })
const names = preset.names
const activeFilters = computed<ActiveFilter[]>(() => {
  const f = filters.value
  const active: ActiveFilter[] = []
  if (f.customer) active.push({ key: 'customer', label: t('projects.customer'), value: names.value.customer })
  if (f.project) active.push({ key: 'project', label: t('projects.project'), value: names.value.project })
  if (f.status) active.push({ key: 'status', label: t('common.status'), value: t(`tasks.status.${f.status}`) })
  if (f.priority) active.push({ key: 'priority', label: t('tasks.priority'), value: t(`tasks.priorities.${f.priority}`) })
  return active
})

const priorities = ['low', 'medium', 'high']
const statuses = ['open', 'in_progress', 'done']
const pagination = usePagination(load, 'position')
const sortOptions = [
  { label: '#', value: 'number' },
  { label: t('tasks.task'), value: 'title' },
  { label: t('projects.customer'), value: 'customer__name' },
  { label: t('projects.project'), value: 'project__name' },
  { label: t('tasks.dueDate'), value: 'due_date' },
  { label: t('tasks.priority'), value: 'priority' },
  { label: t('common.status'), value: 'status' },
]

onMounted(pagination.start)
watch(filters, () => pagination.refresh(), { deep: true })

async function load() {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters.value)) if (value) params.set(key, value)
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
    notify.ok(t('common.saved'))
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
        <Button :label="t('tasks.new')" icon="pi pi-plus" @click="openEdit()" />
      </template>
    </AppPageHeader>

    <AppDataTable
      :rows="rows" :loading="pagination.loading.value" lazy selectable :delete-row="(row) => tasksApi.remove(row.id)" @bulk-deleted="load"
      :total-records="pagination.totalRecords.value" :first="pagination.first.value"
      :page-size="pagination.pageSize.value" :sort-field="pagination.sortField.value"
      :sort-order="pagination.sortOrder.value" :sort-options="sortOptions"
      :state-key="tableStateKeys.tasks" @state-restore="pagination.onRestore" @page="pagination.onPage" @sort="pagination.onSort" @row-click="openEdit"
    >
      <template #toolbar>
        <AppFilterBar :active="activeFilters" @remove="(key) => filters[key as 'customer' | 'project' | 'status' | 'priority'] = null" @clear="filters = { customer: null, project: null, status: null, priority: null }">
          <AppFormField :label="t('projects.customer')">
            <CustomerSelect v-model="filters.customer" :placeholder="t('common.allCustomers')" @select="(c) => names.customer = c?.name ?? ''" />
          </AppFormField>
          <AppFormField :label="t('projects.project')">
            <ProjectSelect v-model="filters.project" :customer-id="filters.customer" :placeholder="t('common.allProjects')" @select="(p) => names.project = p?.name ?? ''" />
          </AppFormField>
          <AppFormField :label="t('common.status')">
            <AppEnumSelect v-model="filters.status" :options="statuses" label-prefix="tasks.status" :placeholder="t('common.all')" show-clear class="w-full" />
          </AppFormField>
          <AppFormField :label="t('tasks.priority')">
            <AppEnumSelect v-model="filters.priority" :options="priorities" label-prefix="tasks.priorities" :placeholder="t('common.all')" show-clear class="w-full" />
          </AppFormField>
        </AppFilterBar>
      </template>
      <Column :header="''" class="w-8" :reorderable-column="false">
        <template #body="{ data }"><AppIconButton :icon="data.status === 'done' ? 'pi pi-check-circle' : 'pi pi-circle'" :class="data.status === 'done' ? 'text-success! opacity-100!' : 'opacity-100!'" :aria-label="data.status === 'done' ? t('tasks.reopen') : t('tasks.markDone')" :title="data.status === 'done' ? t('tasks.reopen') : t('tasks.markDone')" @click.stop="toggleDone(data)" /></template>
      </Column>
      <Column field="number" :header="t('common.numberShort')" sortable />
      <Column class="app-text" field="title" :header="t('tasks.task')" sortable>
        <template #body="{ data }"><span :class="{ 'line-through text-surface-500': data.status === 'done' }">{{ data.title }}</span></template>
      </Column>
      <Column class="app-text" field="customer_name" sort-field="customer__name" :header="t('projects.customer')" sortable />
      <Column class="app-text" field="project_name" sort-field="project__name" :header="t('projects.project')" sortable />
      <Column field="due_date" :header="t('tasks.dueDate')" sortable>
        <template #body="{ data }"><AppDateTimeDisplay :value="data.due_date" :class="{ 'text-danger font-medium': isOverdue(data) }" /></template>
      </Column>
      <Column field="priority" :header="t('tasks.priority')" sortable>
        <template #body="{ data }"><AppPriority :priority="data.priority" /></template>
      </Column>
      <Column field="status" :header="t('common.status')" sortable>
        <template #body="{ data }"><AppStatusTag :status="data.status" :label="t(`tasks.status.${data.status}`)" /></template>
      </Column>
      <Column :header="t('common.actions')" :reorderable-column="false">
        <template #body="{ data }"><AppIconButton icon="pi pi-trash" severity="danger" @click.stop="confirmDelete(async () => { await tasksApi.remove(data.id); load() })" /></template>
      </Column>
      <template #card="{ row }">
        <div class="flex items-center gap-2">
          <AppIconButton :icon="row.status === 'done' ? 'pi pi-check-circle' : 'pi pi-circle'" :class="{ 'text-success!': row.status === 'done' }" :aria-label="row.status === 'done' ? t('tasks.reopen') : t('tasks.markDone')" @click.stop="toggleDone(row)" />
          <span class="font-medium flex-1" :class="{ 'line-through text-surface-500': row.status === 'done' }">{{ row.title }}</span>
          <AppPriority :priority="row.priority" />
        </div>
      </template>
    </AppDataTable>

    <AppModal ref="modal" :form="form" :title="editing ? `${t('tasks.edit')} · ${editing.number}` : t('tasks.new')" @confirm="save">
      <div class="flex flex-col gap-4">
        <AppFormField field="title" :label="t('tasks.task')" required><InputText v-model="form.title" class="w-full" /></AppFormField>
        <AppFormField field="customer" :label="t('projects.customer')"><CustomerSelect v-model="form.customer" /></AppFormField>
        <AppFormField field="project" :label="t('projects.project')"><ProjectSelect v-model="form.project" :customer-id="form.customer" /></AppFormField>
        <AppFormField field="description" :label="t('time.description')"><Textarea v-model="form.description" rows="2" class="w-full" /></AppFormField>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <AppFormField field="due_date" :label="t('tasks.dueDate')"><AppDateInput v-model="(form.due_date as any)" /></AppFormField>
          <AppFormField :label="t('tasks.priority')">
            <AppEnumSelect v-model="form.priority" :options="priorities" label-prefix="tasks.priorities" class="w-full" />
          </AppFormField>
          <AppFormField :label="t('common.status')">
            <AppEnumSelect v-model="form.status" :options="statuses" label-prefix="tasks.status" class="w-full" />
          </AppFormField>
        </div>
      </div>
    </AppModal>
  </div>
</template>
