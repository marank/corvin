<script setup lang="ts">
import { isoDate } from '../../dateTimeInput'
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Column from 'primevue/column'
import Button from 'primevue/button'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppFilterBar, { type ActiveFilter } from '../../components/ui/AppFilterBar.vue'
import AppSearchInput from '../../components/ui/AppSearchInput.vue'
import { useQueryFilters } from '../../composables/useQueryFilters'
import AppEnumSelect from '../../components/ui/AppEnumSelect.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import Select from 'primevue/select'
import CustomerSelect from '../../components/CustomerSelect.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppStatusTag from '../../components/ui/AppStatusTag.vue'
import AppMoneyDisplay from '../../components/ui/AppMoneyDisplay.vue'
import AppDateTimeDisplay from '../../components/ui/AppDateTimeDisplay.vue'
import AppModal from '../../components/ui/AppModal.vue'
import AppIconButton from '../../components/ui/AppIconButton.vue'
import ContractFormFields from '../../components/ContractFormFields.vue'
import AppDurationDisplay from '../../components/ui/AppDurationDisplay.vue'
import { contractsApi, type SupportContract } from '../../api'
import { useNotify } from '../../composables/useNotify'
import { useConfirmDelete } from '../../composables/useConfirmDelete'
import { usePagination } from '../../composables/usePagination'
import { tableStateKeys } from '../../tableStateKeys'
import { contractPeriodValues as periods } from '../../utils/enums'

const { t } = useI18n()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const rows = ref<SupportContract[]>([])
const modal = ref<InstanceType<typeof AppModal>>()
const saving = ref(false)
const emptyForm = (): Partial<SupportContract> => ({
  period: 'monthly',
  included_hours: 10,
  fixed_price: 0,
  bill_overage: false,
  active: true,
  start_date: isoDate(),
  next_billing_date: isoDate(),
})
const form = ref(emptyForm())

function openNew() {
  form.value = emptyForm()
  modal.value?.open()
}
const preset = useQueryFilters()
const names = preset.names
const search = ref('')
const filters = ref({
  customer: preset.customer,
  period: null as string | null,
  active: null as string | null,
})
const activeOptions = [
  { label: t('common.active'), value: 'true' },
  { label: t('common.inactive'), value: 'false' },
]
const activeFilters = computed<ActiveFilter[]>(() => {
  const f = filters.value
  const active: ActiveFilter[] = []
  if (f.customer)
    active.push({ key: 'customer', label: t('projects.customer'), value: names.value.customer })
  if (f.period)
    active.push({
      key: 'period',
      label: t('contracts.period'),
      value: t(`contracts.periods.${f.period}`),
    })
  if (f.active)
    active.push({
      key: 'active',
      label: t('common.status'),
      value: activeOptions.find((o) => o.value === f.active)!.label,
    })
  return active
})
const pagination = usePagination(load, 'number')
const sortOptions = [
  { label: '#', value: 'number' },
  { label: t('common.name'), value: 'name' },
  { label: t('projects.customer'), value: 'customer__name' },
  { label: t('contracts.period'), value: 'period' },
  { label: t('contracts.fixedPrice'), value: 'fixed_price' },
]

onMounted(pagination.start)
watch([search, filters], () => pagination.refresh(), { deep: true })

async function load() {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters.value)) if (value) params.set(key, value)
  if (search.value) params.set('search', search.value)
  const results = await pagination.fetchPage(contractsApi.list, params)
  if (results) rows.value = results
}

async function save() {
  saving.value = true
  try {
    await contractsApi.create(form.value)
    modal.value?.close()
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
    <AppPageHeader :title="t('contracts.title')">
      <template #actions>
        <Button :label="t('contracts.new')" icon="pi pi-plus" @click="openNew" />
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
      :state-key="tableStateKeys.contracts"
      @state-restore="pagination.onRestore"
      @page="pagination.onPage"
      @sort="pagination.onSort"
      @row-click="(r: SupportContract) => router.push(`/contracts/${r.id}`)"
    >
      <template #toolbar>
        <AppFilterBar
          :active="activeFilters"
          @remove="(key) => (filters[key as 'customer' | 'period' | 'active'] = null)"
          @clear="filters = { customer: null, period: null, active: null }"
        >
          <AppFormField :label="t('projects.customer')">
            <CustomerSelect
              v-model="filters.customer"
              :placeholder="t('common.allCustomers')"
              @select="(c) => (names.customer = c?.name ?? '')"
            />
          </AppFormField>
          <AppFormField :label="t('contracts.period')">
            <AppEnumSelect
              v-model="filters.period"
              :options="periods"
              label-prefix="contracts.periods"
              :placeholder="t('common.all')"
              show-clear
              class="w-full"
            />
          </AppFormField>
          <AppFormField :label="t('common.status')">
            <Select
              v-model="filters.active"
              :options="activeOptions"
              option-label="label"
              option-value="value"
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
      <Column
        class="app-text"
        field="project_name"
        sort-field="project__name"
        :header="t('projects.project')"
        sortable
        hidden
      />
      <Column field="period" :header="t('contracts.period')" sortable>
        <template #body="{ data }">{{ t(`contracts.periods.${data.period}`) }}</template>
      </Column>
      <Column class="app-num" field="included_hours" :header="t('contracts.includedHours')">
        <template #body="{ data }"
          ><AppDurationDisplay :minutes="data.included_hours * 60"
        /></template>
      </Column>
      <Column class="app-num" field="fixed_price" :header="t('contracts.fixedPrice')" sortable>
        <template #body="{ data }"><AppMoneyDisplay :amount="data.fixed_price" /></template>
      </Column>
      <Column field="start_date" :header="t('contracts.startDate')" hidden
        ><template #body="{ data }"><AppDateTimeDisplay :value="data.start_date" /></template
      ></Column>
      <Column field="end_date" :header="t('contracts.endDate')" hidden
        ><template #body="{ data }"
          ><AppDateTimeDisplay v-if="data.end_date" :value="data.end_date" /></template
      ></Column>
      <Column field="next_billing_date" :header="t('contracts.nextBilling')"
        ><template #body="{ data }"><AppDateTimeDisplay :value="data.next_billing_date" /></template
      ></Column>
      <Column column-key="status" :header="t('common.status')">
        <template #body="{ data }"
          ><AppStatusTag
            :status="data.active ? 'active' : 'inactive'"
            :label="data.active ? t('common.active') : t('common.inactive')"
        /></template>
      </Column>
      <Column :reorderable-column="false">
        <template #body="{ data }"
          ><AppIconButton
            icon="pi pi-trash"
            severity="danger"
            @click.stop="
              confirmDelete(async () => {
                await contractsApi.remove(data.id)
                load()
              })
            "
        /></template>
      </Column>
      <template #card="{ row }">
        <div class="font-medium">{{ row.name }}</div>
        <div class="text-sm text-surface-500">
          {{ row.customer_name }} · <AppDurationDisplay :minutes="row.included_hours * 60" /> /
          <AppMoneyDisplay :amount="row.fixed_price" />
        </div>
      </template>
    </AppDataTable>

    <AppModal
      ref="modal"
      :form="form"
      :title="t('contracts.new')"
      size="lg"
      :loading="saving"
      @confirm="save"
    >
      <ContractFormFields v-model="form" />
    </AppModal>
  </div>
</template>
