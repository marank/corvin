<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
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
import AppIconButton from '../../components/ui/AppIconButton.vue'
import AppNumberDisplay from '../../components/ui/AppNumberDisplay.vue'
import AppDurationDisplay from '../../components/ui/AppDurationDisplay.vue'
import CustomerSelect from '../../components/CustomerSelect.vue'
import AppFilterBar, { type ActiveFilter } from '../../components/ui/AppFilterBar.vue'
import { useQueryFilters } from '../../composables/useQueryFilters'
import { projectsApi, type Project } from '../../api'
import { useNotify } from '../../composables/useNotify'
import { useConfirmDelete } from '../../composables/useConfirmDelete'
import { usePagination } from '../../composables/usePagination'
import { tableStateKeys } from '../../tableStateKeys'

const { t } = useI18n()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const rows = ref<Project[]>([])
const modal = ref<InstanceType<typeof AppModal>>()
const saving = ref(false)
const form = ref<Partial<Project>>({ status: 'active' })

const statuses = ['active', 'on_hold', 'done']
const pagination = usePagination(load, 'name')
const sortOptions = [
  { label: '#', value: 'number' },
  { label: t('common.name'), value: 'name' },
  { label: t('projects.customer'), value: 'customer__name' },
  { label: t('common.status'), value: 'status' },
]

const preset = useQueryFilters()
const filters = ref({ customer: preset.customer, status: null as string | null })
const names = preset.names
const activeFilters = computed<ActiveFilter[]>(() => {
  const f = filters.value
  const active: ActiveFilter[] = []
  if (f.customer) active.push({ key: 'customer', label: t('projects.customer'), value: names.value.customer })
  if (f.status) active.push({ key: 'status', label: t('common.status'), value: t(`projects.status.${f.status}`) })
  return active
})

onMounted(pagination.start)
watch(filters, () => pagination.refresh(), { deep: true })

async function load() {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters.value)) if (value) params.set(key, value)
  const results = await pagination.fetchPage(projectsApi.list, params)
  if (results) rows.value = results
}

async function save() {
  saving.value = true
  try {
    await projectsApi.create(form.value)
    modal.value?.close()
    form.value = { status: 'active' }
    notify.ok(t('common.created'))
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

    <AppDataTable
      :rows="rows" :loading="pagination.loading.value" lazy selectable :delete-row="(row) => projectsApi.remove(row.id)" @bulk-deleted="load"
      :total-records="pagination.totalRecords.value" :first="pagination.first.value"
      :page-size="pagination.pageSize.value" :sort-field="pagination.sortField.value"
      :sort-order="pagination.sortOrder.value" :sort-options="sortOptions"
      :state-key="tableStateKeys.projects" @state-restore="pagination.onRestore" @page="pagination.onPage" @sort="pagination.onSort"
      @row-click="(r: Project) => router.push(`/projects/${r.id}`)"
    >
      <template #toolbar>
        <AppFilterBar :active="activeFilters" @remove="(key) => filters[key as 'customer' | 'status'] = null" @clear="filters = { customer: null, status: null }">
          <AppFormField :label="t('projects.customer')">
            <CustomerSelect v-model="filters.customer" :placeholder="t('common.allCustomers')" @select="(c) => names.customer = c?.name ?? ''" />
          </AppFormField>
          <AppFormField :label="t('common.status')">
            <Select v-model="filters.status" :options="statuses" :placeholder="t('common.all')" show-clear class="w-full">
              <template #option="{ option }">{{ t(`projects.status.${option}`) }}</template>
              <template #value="{ value, placeholder }">
                <span v-if="value">{{ t(`projects.status.${value}`) }}</span>
                <span v-else class="text-surface-500">{{ placeholder }}</span>
              </template>
            </Select>
          </AppFormField>
        </AppFilterBar>
      </template>
      <Column field="number" :header="t('common.numberShort')" sortable />
      <Column class="app-text" field="name" :header="t('common.name')" sortable />
      <Column class="app-text" field="customer_name" sort-field="customer__name" :header="t('projects.customer')" sortable />
      <Column field="status" :header="t('common.status')" sortable>
        <template #body="{ data }"><AppStatusTag :status="data.status" :label="t(`projects.status.${data.status}`)" /></template>
      </Column>
      <Column class="app-num" :header="t('projects.usedHours')">
        <template #body="{ data }"><AppDurationDisplay :minutes="data.used_hours * 60" /></template>
      </Column>
      <Column class="app-num" :header="t('projects.budgetHours')">
        <template #body="{ data }"><AppNumberDisplay :value="data.budget_hours" /></template>
      </Column>
      <Column :header="t('common.actions')" :reorderable-column="false">
        <template #body="{ data }"><AppIconButton icon="pi pi-trash" severity="danger" @click.stop="confirmDelete(async () => { await projectsApi.remove(data.id); load() })" /></template>
      </Column>
      <template #card="{ row }">
        <div class="flex justify-between">
          <span class="font-medium">{{ row.name }}</span>
          <AppStatusTag :status="row.status" :label="t(`projects.status.${row.status}`)" />
        </div>
        <div class="text-sm text-surface-500">{{ row.customer_name }}</div>
      </template>
    </AppDataTable>

    <AppModal ref="modal" :form="form" :title="t('projects.new')" :loading="saving" @confirm="save">
      <div class="flex flex-col gap-4">
        <AppFormField field="customer" :label="t('projects.customer')" required><CustomerSelect v-model="form.customer" /></AppFormField>
        <AppFormField field="name" :label="t('common.name')" required><InputText v-model="form.name" class="w-full" /></AppFormField>
        <AppFormField field="description" :label="t('time.description')"><Textarea v-model="form.description" rows="2" class="w-full" /></AppFormField>
        <div class="grid grid-cols-2 gap-3">
          <AppFormField field="budget_hours" :label="t('projects.budgetHours')"><InputNumber v-model="form.budget_hours" class="w-full" /></AppFormField>
          <AppFormField field="budget_amount" :label="t('projects.budgetAmount')"><InputNumber v-model="form.budget_amount" mode="currency" currency="EUR" class="w-full" /></AppFormField>
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
