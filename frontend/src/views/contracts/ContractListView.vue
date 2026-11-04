<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Column from 'primevue/column'
import Button from 'primevue/button'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
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

const { t } = useI18n()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const rows = ref<SupportContract[]>([])
const modal = ref<InstanceType<typeof AppModal>>()
const saving = ref(false)
const emptyForm = (): Partial<SupportContract> => ({
  period: 'monthly', included_hours: 10, fixed_price: 0,
  bill_overage: false, active: true, start_date: new Date().toISOString().slice(0, 10),
  next_billing_date: new Date().toISOString().slice(0, 10),
})
const form = ref(emptyForm())
const pagination = usePagination(load, 'number')
const sortOptions = [
  { label: '#', value: 'number' },
  { label: t('common.name'), value: 'name' },
  { label: t('projects.customer'), value: 'customer__name' },
  { label: t('contracts.period'), value: 'period' },
  { label: t('contracts.fixedPrice'), value: 'fixed_price' },
]

onMounted(pagination.start)

async function load() {
  const results = await pagination.fetchPage(contractsApi.list)
  if (results) rows.value = results
}

async function save() {
  saving.value = true
  try {
    await contractsApi.create(form.value)
    modal.value?.close()
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
    <AppPageHeader :title="t('contracts.title')">
      <template #actions>
        <Button :label="t('contracts.new')" icon="pi pi-plus" @click="form = emptyForm(); modal?.open()" />
      </template>
    </AppPageHeader>

    <AppDataTable
      :rows="rows" :loading="pagination.loading.value" lazy selectable :delete-row="(row) => contractsApi.remove(row.id)" @bulk-deleted="load"
      :total-records="pagination.totalRecords.value" :first="pagination.first.value"
      :page-size="pagination.pageSize.value" :sort-field="pagination.sortField.value"
      :sort-order="pagination.sortOrder.value" :sort-options="sortOptions"
      :state-key="tableStateKeys.contracts" @state-restore="pagination.onRestore" @page="pagination.onPage" @sort="pagination.onSort"
      @row-click="(r: SupportContract) => router.push(`/contracts/${r.id}`)"
    >
      <Column field="number" :header="t('common.numberShort')" sortable />
      <Column class="app-text" field="name" :header="t('common.name')" sortable />
      <Column class="app-text" field="customer_name" sort-field="customer__name" :header="t('projects.customer')" sortable />
      <Column field="period" :header="t('contracts.period')" sortable>
        <template #body="{ data }">{{ t(`contracts.periods.${data.period}`) }}</template>
      </Column>
      <Column class="app-num" :header="t('contracts.includedHours')">
        <template #body="{ data }"><AppDurationDisplay :minutes="data.included_hours * 60" /></template>
      </Column>
      <Column class="app-num" field="fixed_price" :header="t('contracts.fixedPrice')" sortable>
        <template #body="{ data }"><AppMoneyDisplay :amount="data.fixed_price" /></template>
      </Column>
      <Column :header="t('contracts.nextBilling')"><template #body="{ data }"><AppDateTimeDisplay :value="data.next_billing_date" /></template></Column>
      <Column :header="t('common.status')">
        <template #body="{ data }"><AppStatusTag :status="data.active ? 'active' : 'inactive'" :label="data.active ? t('common.active') : t('common.inactive')" /></template>
      </Column>
      <Column :header="t('common.actions')" :reorderable-column="false">
        <template #body="{ data }"><AppIconButton icon="pi pi-trash" severity="danger" @click.stop="confirmDelete(async () => { await contractsApi.remove(data.id); load() })" /></template>
      </Column>
      <template #card="{ row }">
        <div class="font-medium">{{ row.name }}</div>
        <div class="text-sm text-surface-500">{{ row.customer_name }} · <AppDurationDisplay :minutes="row.included_hours * 60" /> / <AppMoneyDisplay :amount="row.fixed_price" /></div>
      </template>
    </AppDataTable>

    <AppModal ref="modal" :form="form" :title="t('contracts.new')" size="lg" :loading="saving" @confirm="save">
      <ContractFormFields v-model="form" />
    </AppModal>
  </div>
</template>
