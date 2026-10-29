<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppStatusTag from '../../components/ui/AppStatusTag.vue'
import AppMoneyDisplay from '../../components/ui/AppMoneyDisplay.vue'
import AppDateTimeDisplay from '../../components/ui/AppDateTimeDisplay.vue'
import AppNumberDisplay from '../../components/ui/AppNumberDisplay.vue'
import AppModal from '../../components/ui/AppModal.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppCheckboxField from '../../components/ui/AppCheckboxField.vue'
import AppIconButton from '../../components/ui/AppIconButton.vue'
import AppDateInput from '../../components/ui/AppDateInput.vue'
import CustomerSelect from '../../components/CustomerSelect.vue'
import ProjectSelect from '../../components/ProjectSelect.vue'
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
const periods = ['monthly', 'quarterly', 'yearly']
const form = ref<Partial<SupportContract>>({
  period: 'monthly', included_hours: 10, fixed_price: 0,
  bill_overage: false, active: true, start_date: new Date().toISOString().slice(0, 10),
  next_billing_date: new Date().toISOString().slice(0, 10),
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

async function load() {
  const results = await pagination.fetchPage(contractsApi.list)
  if (results) rows.value = results
}

async function save() {
  saving.value = true
  try {
    await contractsApi.create(form.value)
    modal.value?.close()
    form.value = {
      period: 'monthly', included_hours: 10, fixed_price: 0,
      bill_overage: false, active: true, start_date: new Date().toISOString().slice(0, 10),
      next_billing_date: new Date().toISOString().slice(0, 10),
    }
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
        <Button :label="t('contracts.new')" icon="pi pi-plus" @click="modal?.open()" />
      </template>
    </AppPageHeader>

    <AppDataTable
      :rows="rows" :loading="pagination.loading.value" lazy selectable
      :total-records="pagination.totalRecords.value" :first="pagination.first.value"
      :page-size="pagination.pageSize.value" :sort-field="pagination.sortField.value"
      :sort-order="pagination.sortOrder.value" :sort-options="sortOptions"
      :state-key="tableStateKeys.contracts" @state-restore="pagination.onRestore" @page="pagination.onPage" @sort="pagination.onSort"
      @row-click="(r: SupportContract) => router.push(`/contracts/${r.id}`)"
    >
      <Column field="number" header="#" sortable />
      <Column field="name" :header="t('common.name')" sortable />
      <Column field="customer_name" sort-field="customer__name" :header="t('projects.customer')" sortable />
      <Column field="period" :header="t('contracts.period')" sortable>
        <template #body="{ data }">{{ t(`contracts.periods.${data.period}`) }}</template>
      </Column>
      <Column :header="t('contracts.includedHours')">
        <template #body="{ data }"><AppNumberDisplay :value="data.included_hours" />h</template>
      </Column>
      <Column field="fixed_price" :header="t('contracts.fixedPrice')" sortable>
        <template #body="{ data }"><AppMoneyDisplay :amount="data.fixed_price" /></template>
      </Column>
      <Column :header="t('contracts.nextBilling')"><template #body="{ data }"><AppDateTimeDisplay :value="data.next_billing_date" /></template></Column>
      <Column :header="t('common.status')">
        <template #body="{ data }"><AppStatusTag :status="data.active ? 'active' : 'cancelled'" :label="data.active ? t('customers.active') : '—'" /></template>
      </Column>
      <Column :header="t('common.actions')" :reorderable-column="false">
        <template #body="{ data }"><AppIconButton icon="pi pi-trash" severity="danger" @click.stop="confirmDelete(async () => { await contractsApi.remove(data.id); load() })" /></template>
      </Column>
      <template #card="{ row }">
        <div class="font-medium">{{ row.name }}</div>
        <div class="text-sm text-surface-500">{{ row.customer_name }} · <AppNumberDisplay :value="row.included_hours" />h / <AppMoneyDisplay :amount="row.fixed_price" /></div>
      </template>
    </AppDataTable>

    <AppModal ref="modal" :title="t('contracts.new')" size="lg" :loading="saving" @confirm="save">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <AppFormField :label="t('common.name')" required><InputText v-model="form.name" class="w-full" /></AppFormField>
        <AppFormField :label="t('projects.customer')" required><CustomerSelect v-model="form.customer" /></AppFormField>
        <AppFormField :label="t('nav.projects')"><ProjectSelect v-model="form.project" :customer-id="form.customer" /></AppFormField>
        <AppFormField :label="t('contracts.period')">
          <Select v-model="form.period" :options="periods" class="w-full">
            <template #option="{ option }">{{ t(`contracts.periods.${option}`) }}</template>
            <template #value="{ value }">{{ value ? t(`contracts.periods.${value}`) : '' }}</template>
          </Select>
        </AppFormField>
        <AppFormField :label="t('contracts.includedHours')"><InputNumber v-model="form.included_hours" :min-fraction-digits="2" class="w-full" /></AppFormField>
        <AppFormField :label="t('contracts.fixedPrice')"><InputNumber v-model="form.fixed_price" mode="currency" currency="EUR" class="w-full" /></AppFormField>
        <AppFormField :label="t('common.date')"><AppDateInput v-model="(form.start_date as any)" /></AppFormField>
        <AppFormField :label="t('contracts.nextBilling')"><AppDateInput v-model="(form.next_billing_date as any)" /></AppFormField>
        <AppFormField :label="t('time.end')"><AppDateInput v-model="(form.end_date as any)" /></AppFormField>
        <AppCheckboxField v-model="form.bill_overage" :label="t('contracts.billOverage')" />
        <AppFormField v-if="form.bill_overage" :label="t('contracts.overageRate')"><InputNumber v-model="form.overage_rate" mode="currency" currency="EUR" class="w-full" /></AppFormField>
        <AppCheckboxField v-model="form.active" :label="t('customers.active')" />
      </div>
    </AppModal>
  </div>
</template>
