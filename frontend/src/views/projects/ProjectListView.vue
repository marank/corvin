<script setup lang="ts">
import AppEnumSelect from '../../components/ui/AppEnumSelect.vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppStatusTag from '../../components/ui/AppStatusTag.vue'
import AppMoneyDisplay from '../../components/ui/AppMoneyDisplay.vue'
import AppDateTimeDisplay from '../../components/ui/AppDateTimeDisplay.vue'
import AppModal from '../../components/ui/AppModal.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppIconButton from '../../components/ui/AppIconButton.vue'
import AppDurationDisplay from '../../components/ui/AppDurationDisplay.vue'
import CustomerSelect from '../../components/CustomerSelect.vue'
import AppFilterBar, { type ActiveFilter } from '../../components/ui/AppFilterBar.vue'
import AppSearchInput from '../../components/ui/AppSearchInput.vue'
import { useQueryFilters } from '../../composables/useQueryFilters'
import { projectsApi, type Project } from '../../api'
import { useNotify } from '../../composables/useNotify'
import { useConfirmDelete } from '../../composables/useConfirmDelete'
import { usePagination } from '../../composables/usePagination'
import { tableStateKeys } from '../../tableStateKeys'
import { projectStatusValues as statuses } from '../../utils/enums'

const { t } = useI18n()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const rows = ref<Project[]>([])
const modal = ref<InstanceType<typeof AppModal>>()
const saving = ref(false)
const form = ref<Partial<Project>>({ status: 'active' })

function openNew() {
  form.value = { status: 'active' }
  modal.value?.open()
}

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
const search = ref('')
const activeFilters = computed<ActiveFilter[]>(() => {
  const f = filters.value
  const active: ActiveFilter[] = []
  if (f.customer)
    active.push({ key: 'customer', label: t('projects.customer'), value: names.value.customer })
  if (f.status)
    active.push({
      key: 'status',
      label: t('common.status'),
      value: t(`projects.status.${f.status}`),
    })
  return active
})

onMounted(pagination.start)
watch([search, filters], () => pagination.refresh(), { deep: true })

async function load() {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters.value)) if (value) params.set(key, value)
  if (search.value) params.set('search', search.value)
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
    void load()
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
        <Button :label="t('projects.new')" icon="pi pi-plus" @click="openNew" />
      </template>
    </AppPageHeader>

    <AppDataTable
      :rows="rows"
      :loading="pagination.loading.value"
      lazy
      :total-records="pagination.totalRecords.value"
      :first="pagination.first.value"
      :page-size="pagination.pageSize.value"
      :sort-field="pagination.sortField.value"
      :sort-order="pagination.sortOrder.value"
      :sort-options="sortOptions"
      :state-key="tableStateKeys.projects"
      @state-restore="pagination.onRestore"
      @page="pagination.onPage"
      @sort="pagination.onSort"
      @row-click="(r: Project) => router.push(`/projects/${r.id}`)"
    >
      <template #toolbar>
        <AppFilterBar
          :active="activeFilters"
          @remove="(key) => (filters[key as 'customer' | 'status'] = null)"
          @clear="filters = { customer: null, status: null }"
        >
          <AppFormField :label="t('projects.customer')">
            <CustomerSelect
              v-model="filters.customer"
              :placeholder="t('common.allCustomers')"
              @select="(c) => (names.customer = c?.name ?? '')"
            />
          </AppFormField>
          <AppFormField :label="t('common.status')">
            <AppEnumSelect
              v-model="filters.status"
              :options="statuses"
              label-prefix="projects.status"
              :placeholder="t('common.all')"
              show-clear
              class="w-full"
            />
          </AppFormField>
          <template #end><AppSearchInput v-model="search" /></template>
        </AppFilterBar>
      </template>
      <Column
        field="number"
        :header="t('common.numberShort')"
        header-style="width: 6.5rem"
        sortable
      />
      <Column class="app-text" field="name" :header="t('common.name')" sortable />
      <Column
        class="app-text"
        field="customer_name"
        sort-field="customer__name"
        :header="t('projects.customer')"
        sortable
      />
      <Column class="app-text" field="description" :header="t('time.description')" hidden />
      <Column field="status" :header="t('common.status')" header-style="width: 8.5rem" sortable>
        <template #body="{ data }"
          ><AppStatusTag :status="data.status" :label="t(`projects.status.${data.status}`)"
        /></template>
      </Column>
      <Column
        class="app-num"
        column-key="used_hours"
        :header="t('projects.usedHours')"
        header-style="width: 11rem"
      >
        <template #body="{ data }">
          <span class="inline-flex items-center justify-end gap-2">
            <span
              v-if="data.budget_hours"
              class="inline-block w-12 h-1.5 bg-surface-200 dark:bg-surface-700 overflow-hidden"
              :title="`${Math.round(data.budget_hours_percent ?? 0)} %`"
            >
              <span
                class="block h-full"
                :class="(data.budget_hours_percent ?? 0) >= 80 ? 'bg-danger' : 'bg-primary'"
                :style="{ width: `${Math.min(100, data.budget_hours_percent ?? 0)}%` }"
              />
            </span>
            <span>
              <AppDurationDisplay :minutes="data.used_hours * 60" /><template
                v-if="data.budget_hours"
              >
                / <AppDurationDisplay :minutes="data.budget_hours * 60"
              /></template>
            </span>
          </span>
        </template>
      </Column>
      <Column class="app-num" column-key="used_amount" :header="t('projects.usedAmount')" hidden>
        <template #body="{ data }">
          <AppMoneyDisplay :amount="data.used_amount" /><template v-if="data.budget_amount">
            / <AppMoneyDisplay :amount="data.budget_amount"
          /></template>
        </template>
      </Column>
      <Column
        field="created_at"
        :header="t('common.createdAt')"
        header-style="width: 7rem"
        sortable
        hidden
      >
        <template #body="{ data }"><AppDateTimeDisplay :value="data.created_at" /></template>
      </Column>
      <Column :reorderable-column="false">
        <template #body="{ data }"
          ><AppIconButton
            icon="pi pi-trash"
            severity="danger"
            @click.stop="
              confirmDelete(async () => {
                await projectsApi.remove(data.id)
                load()
              })
            "
        /></template>
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
        <AppFormField field="customer" :label="t('projects.customer')" required
          ><CustomerSelect v-model="form.customer"
        /></AppFormField>
        <AppFormField field="name" :label="t('common.name')" required
          ><InputText v-model="form.name" class="w-full"
        /></AppFormField>
        <AppFormField field="description" :label="t('time.description')"
          ><Textarea v-model="form.description" rows="2" class="w-full"
        /></AppFormField>
        <div class="grid grid-cols-2 gap-3">
          <AppFormField field="budget_hours" :label="t('projects.budgetHours')"
            ><InputNumber v-model="form.budget_hours" class="w-full"
          /></AppFormField>
          <AppFormField field="budget_amount" :label="t('projects.budgetAmount')"
            ><InputNumber
              v-model="form.budget_amount"
              mode="currency"
              currency="EUR"
              class="w-full"
          /></AppFormField>
        </div>
        <AppFormField :label="t('common.status')">
          <AppEnumSelect
            v-model="form.status"
            :options="statuses"
            label-prefix="projects.status"
            class="w-full"
          />
        </AppFormField>
      </div>
    </AppModal>
  </div>
</template>
