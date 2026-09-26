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
import { invoicesApi, type Invoice } from '../../api'

const { t } = useI18n()
const router = useRouter()
const rows = ref<Invoice[]>([])
const loading = ref(true)
const statusFilter = ref<string | null>(null)
const statuses = ['draft', 'issued', 'paid', 'cancelled']

async function load() {
  loading.value = true
  const p = statusFilter.value ? `status=${statusFilter.value}&` : ''
  rows.value = (await invoicesApi.list(`${p}page_size=500`)).results
  loading.value = false
}
onMounted(load)
</script>

<template>
  <div>
    <AppPageHeader :title="t('invoices.title')">
      <template #actions>
        <Select v-model="statusFilter" :options="statuses" :placeholder="t('common.status')" show-clear class="w-40" @update:model-value="load">
          <template #option="{ option }">{{ t(`invoices.status.${option}`) }}</template>
          <template #value="{ value }">{{ value ? t(`invoices.status.${value}`) : '' }}</template>
        </Select>
        <Button :label="t('invoices.new')" icon="pi pi-plus" @click="router.push('/invoices/new')" />
      </template>
    </AppPageHeader>

    <AppDataTable :rows="rows" :loading="loading" @row-click="(r: Invoice) => router.push(`/invoices/${r.id}`)">
      <Column field="number" :header="t('invoices.number')" />
      <Column field="customer_name" :header="t('projects.customer')" />
      <Column field="issue_date" :header="t('invoices.issueDate')" />
      <Column field="due_date" :header="t('invoices.dueDate')" />
      <Column :header="t('common.total')">
        <template #body="{ data }"><AppMoneyDisplay :amount="data.total" :currency="data.currency" /></template>
      </Column>
      <Column :header="t('invoices.remaining')">
        <template #body="{ data }">
          <AppMoneyDisplay v-if="Number(data.remaining) > 0 && data.status !== 'draft'" :amount="data.remaining" :currency="data.currency" />
          <span v-else>—</span>
        </template>
      </Column>
      <Column :header="t('common.status')">
        <template #body="{ data }">
          <AppStatusTag :status="data.partially_paid ? 'partially_paid' : data.status" :label="data.partially_paid ? t('invoices.paid') + ' (teilw.)' : t(`invoices.status.${data.status}`)" />
        </template>
      </Column>
      <template #card="{ row }">
        <div class="flex justify-between items-center">
          <div>
            <div class="font-medium">{{ row.number }}</div>
            <div class="text-sm text-surface-500">{{ row.customer_name }} · {{ row.issue_date }}</div>
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
