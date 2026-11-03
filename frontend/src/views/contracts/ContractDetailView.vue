<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppDurationDisplay from '../../components/ui/AppDurationDisplay.vue'
import AppMoneyDisplay from '../../components/ui/AppMoneyDisplay.vue'
import AppDateTimeDisplay from '../../components/ui/AppDateTimeDisplay.vue'
import AppNumberDisplay from '../../components/ui/AppNumberDisplay.vue'
import ContractUsageBar from '../../components/ContractUsageBar.vue'
import {
  contractsApi, invoicesApi, timeTrackingApi,
  type ContractUsage, type Invoice, type SupportContract, type TimeEntry,
} from '../../api'
import { useNotify } from '../../composables/useNotify'
import { useConfirmDelete } from '../../composables/useConfirmDelete'
import { tableStateKeys } from '../../tableStateKeys'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const id = route.params.id as string

const contract = ref<SupportContract | null>(null)
const usage = ref<ContractUsage | null>(null)
const entries = ref<TimeEntry[]>([])
const invoices = ref<Invoice[]>([])
const running = ref(false)

async function load() {
  contract.value = await contractsApi.get(id)
  usage.value = await contractsApi.usage(id)
  entries.value = (await timeTrackingApi.list(`contract=${id}&page_size=500`)).results
  invoices.value = (await invoicesApi.list(`contract=${id}&page_size=500`)).results
}
onMounted(load)

async function runNow() {
  running.value = true
  try {
    const inv = await contractsApi.runNow(id)
    notify.ok(t('contracts.generatedInvoice'))
    load()
    if (inv?.id) router.push(`/invoices/${inv.id}`)
  } catch (e) {
    notify.error(e)
  } finally {
    running.value = false
  }
}
</script>

<template>
  <div v-if="contract">
    <AppPageHeader :title="contract.name" :subtitle="`${contract.number} · ${contract.customer_name}`">
      <template #actions>
        <Button :label="t('common.delete')" text severity="danger" @click="confirmDelete(async () => { await contractsApi.remove(id); router.push('/contracts') })" />
        <Button :label="t('contracts.runNow')" icon="pi pi-play" :loading="running" @click="runNow" />
      </template>
    </AppPageHeader>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="border border-surface-200 dark:border-surface-800 p-4">
        <p class="text-sm text-surface-500 mb-2">{{ t('contracts.usage') }} (<AppDateTimeDisplay :value="usage?.period_start" /> – <AppDateTimeDisplay :value="usage?.period_end" />)</p>
        <ContractUsageBar v-if="usage" :usage="usage" />
      </div>
      <div class="border border-surface-200 dark:border-surface-800 p-4">
        <p class="text-sm text-surface-500">{{ t('contracts.fixedPrice') }}</p>
        <p class="text-xl font-semibold mt-1"><AppMoneyDisplay :amount="contract.fixed_price" /></p>
        <p class="text-sm text-surface-500 mt-1">{{ t(`contracts.periods.${contract.period}`) }} · <AppNumberDisplay :value="contract.included_hours" />h</p>
      </div>
      <div class="border border-surface-200 dark:border-surface-800 p-4">
        <p class="text-sm text-surface-500">{{ t('contracts.nextBilling') }}</p>
        <p class="text-xl font-semibold mt-1"><AppDateTimeDisplay :value="contract.next_billing_date" /></p>
        <p class="text-sm text-surface-500 mt-1"><AppDateTimeDisplay :value="contract.start_date" /> – <AppDateTimeDisplay v-if="contract.end_date" :value="contract.end_date" /><span v-else>∞</span></p>
      </div>
    </div>

    <h2 class="font-semibold mt-6 mb-2">{{ t('time.title') }}</h2>
    <AppDataTable :rows="entries" :state-key="tableStateKeys.contractTimeEntries">
      <Column field="start_datetime" :header="t('common.date')" sortable><template #body="{ data }"><AppDateTimeDisplay :value="data.start_datetime" type="datetime" /></template></Column>
      <Column class="app-text" field="description" :header="t('time.description')" sortable />
      <Column class="app-num" field="duration_minutes" :header="t('time.duration')" sortable>
        <template #body="{ data }"><AppDurationDisplay :minutes="data.duration_minutes" /></template>
      </Column>
    </AppDataTable>

    <h2 class="font-semibold mt-6 mb-2">{{ t('invoices.title') }}</h2>
    <AppDataTable :rows="invoices" :state-key="tableStateKeys.contractInvoices" @row-click="(r: Invoice) => router.push(`/invoices/${r.id}`)">
      <Column field="number" :header="t('invoices.number')" sortable />
      <Column field="issue_date" :header="t('invoices.issueDate')" sortable><template #body="{ data }"><AppDateTimeDisplay :value="data.issue_date" /></template></Column>
      <Column class="app-num" field="total" :header="t('common.total')" sortable>
        <template #body="{ data }"><AppMoneyDisplay :amount="data.total" /></template>
      </Column>
    </AppDataTable>
  </div>
</template>
