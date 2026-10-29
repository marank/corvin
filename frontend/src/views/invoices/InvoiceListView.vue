<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Select from 'primevue/select'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppStatusTag from '../../components/ui/AppStatusTag.vue'
import AppMoneyDisplay from '../../components/ui/AppMoneyDisplay.vue'
import AppDateTimeDisplay from '../../components/ui/AppDateTimeDisplay.vue'
import AppIconButton from '../../components/ui/AppIconButton.vue'
import { invoicesApi, type Invoice } from '../../api'
import { useConfirmDelete } from '../../composables/useConfirmDelete'
import { usePagination } from '../../composables/usePagination'
import { tableStateKeys } from '../../tableStateKeys'

const { t } = useI18n()
const router = useRouter()
const confirmDelete = useConfirmDelete()
const rows = ref<Invoice[]>([])
const statusFilter = ref<string | null>(null)
const statuses = ['draft', 'issued', 'paid', 'cancelled']
const pagination = usePagination(load, '-issue_date')
const sortOptions = [
  { label: t('invoices.number'), value: 'number' },
  { label: t('projects.customer'), value: 'customer__name' },
  { label: t('invoices.issueDate'), value: 'issue_date' },
  { label: t('invoices.dueDate'), value: 'due_date' },
  { label: t('common.total'), value: 'total' },
  { label: t('common.status'), value: 'status' },
]

onMounted(pagination.start)

async function load() {
  const params = new URLSearchParams()
  if (statusFilter.value) params.set('status', statusFilter.value)
  const results = await pagination.fetchPage(invoicesApi.list, params)
  if (results) rows.value = results
}
</script>

<template>
  <div>
    <AppPageHeader :title="t('invoices.title')">
      <template #actions>
        <Select v-model="statusFilter" :options="statuses" :placeholder="t('common.status')" show-clear class="w-40" @update:model-value="pagination.refresh">
          <template #option="{ option }">{{ t(`invoices.status.${option}`) }}</template>
          <template #value="{ value }">{{ value ? t(`invoices.status.${value}`) : '' }}</template>
        </Select>
        <Button :label="t('invoices.new')" icon="pi pi-plus" @click="router.push('/invoices/new')" />
      </template>
    </AppPageHeader>

    <AppDataTable
      :rows="rows" :loading="pagination.loading.value" lazy selectable
      :total-records="pagination.totalRecords.value" :first="pagination.first.value"
      :page-size="pagination.pageSize.value" :sort-field="pagination.sortField.value"
      :sort-order="pagination.sortOrder.value" :sort-options="sortOptions"
      :state-key="tableStateKeys.invoices" @state-restore="pagination.onRestore" @page="pagination.onPage" @sort="pagination.onSort"
      @row-click="(r: Invoice) => router.push(`/invoices/${r.id}`)"
    >
      <Column field="number" :header="t('invoices.number')" sortable />
      <Column field="customer_name" sort-field="customer__name" :header="t('projects.customer')" sortable />
      <Column field="issue_date" :header="t('invoices.issueDate')" sortable><template #body="{ data }"><AppDateTimeDisplay :value="data.issue_date" /></template></Column>
      <Column field="due_date" :header="t('invoices.dueDate')" sortable><template #body="{ data }"><AppDateTimeDisplay :value="data.due_date" /></template></Column>
      <Column field="total" :header="t('common.total')" sortable>
        <template #body="{ data }"><AppMoneyDisplay :amount="data.total" :currency="data.currency" /></template>
      </Column>
      <Column :header="t('invoices.remaining')">
        <template #body="{ data }">
          <AppMoneyDisplay v-if="Number(data.remaining) > 0 && data.status !== 'draft'" :amount="data.remaining" :currency="data.currency" />
          <span v-else>—</span>
        </template>
      </Column>
      <Column field="status" :header="t('common.status')" sortable>
        <template #body="{ data }">
          <AppStatusTag :status="data.partially_paid ? 'partially_paid' : data.status" :label="data.partially_paid ? t('invoices.paid') + ' (teilw.)' : t(`invoices.status.${data.status}`)" />
        </template>
      </Column>
      <Column :header="t('common.actions')" :reorderable-column="false">
        <template #body="{ data }">
          <AppIconButton v-if="data.status === 'draft'" icon="pi pi-trash" severity="danger" @click.stop="confirmDelete(async () => { await invoicesApi.remove(data.id); load() })" />
        </template>
      </Column>
      <template #card="{ row }">
        <div class="flex justify-between items-center">
          <div>
            <div class="font-medium">{{ row.number }}</div>
            <div class="text-sm text-surface-500">{{ row.customer_name }} · <AppDateTimeDisplay :value="row.issue_date" /></div>
          </div>
          <div class="text-end">
            <AppMoneyDisplay :amount="row.total" :currency="row.currency" />
            <div><AppStatusTag :status="row.status" :label="t(`invoices.status.${row.status}`)" /></div>
          </div>
        </div>
      </template>
    </AppDataTable>
  </div>
</template>
