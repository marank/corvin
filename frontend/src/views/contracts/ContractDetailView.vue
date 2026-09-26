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
import ContractUsageBar from '../../components/ContractUsageBar.vue'
import {
  contractsApi, invoicesApi, timeEntriesApi,
  type ContractUsage, type Invoice, type SupportContract, type TimeEntry,
} from '../../api'
import { useNotify } from '../../composables/useNotify'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const notify = useNotify()
const id = Number(route.params.id)

const contract = ref<SupportContract | null>(null)
const usage = ref<ContractUsage | null>(null)
const entries = ref<TimeEntry[]>([])
const invoices = ref<Invoice[]>([])
const running = ref(false)

async function load() {
  contract.value = await contractsApi.get(id)
  usage.value = await contractsApi.usage(id)
  entries.value = (await timeEntriesApi.list(`contract=${id}&page_size=200`)).results
  invoices.value = (await invoicesApi.list(`contract=${id}&page_size=100`)).results
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
    <AppPageHeader :title="contract.name" :subtitle="contract.customer_name">
      <template #actions>
        <Button :label="t('contracts.runNow')" icon="pi pi-play" :loading="running" @click="runNow" />
      </template>
    </AppPageHeader>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="border border-surface-200 dark:border-surface-800 p-4">
        <p class="text-sm text-surface-500 mb-2">{{ t('contracts.usage') }} ({{ usage?.period_start }} – {{ usage?.period_end }})</p>
        <ContractUsageBar v-if="usage" :usage="usage" />
      </div>
      <div class="border border-surface-200 dark:border-surface-800 p-4">
        <p class="text-sm text-surface-500">{{ t('contracts.fixedPrice') }}</p>
        <p class="text-xl font-semibold mt-1"><AppMoneyDisplay :amount="contract.fixed_price" /></p>
        <p class="text-sm text-surface-500 mt-1">{{ t(`contracts.periods.${contract.period}`) }} · {{ contract.included_hours }}h</p>
      </div>
      <div class="border border-surface-200 dark:border-surface-800 p-4">
        <p class="text-sm text-surface-500">{{ t('contracts.nextBilling') }}</p>
        <p class="text-xl font-semibold mt-1">{{ contract.next_billing_date }}</p>
        <p class="text-sm text-surface-500 mt-1">{{ contract.start_date }} – {{ contract.end_date ?? '∞' }}</p>
      </div>
    </div>

    <h2 class="font-semibold mt-6 mb-2">{{ t('time.title') }}</h2>
    <AppDataTable :rows="entries">
      <Column field="date" :header="t('common.date')" />
      <Column field="description" :header="t('time.description')" />
      <Column :header="t('time.duration')">
        <template #body="{ data }"><AppDurationDisplay :minutes="data.duration_minutes" /></template>
      </Column>
    </AppDataTable>

    <h2 class="font-semibold mt-6 mb-2">{{ t('invoices.title') }}</h2>
    <AppDataTable :rows="invoices" @row-click="(r: Invoice) => router.push(`/invoices/${r.id}`)">
      <Column field="number" :header="t('invoices.number')" />
      <Column field="issue_date" :header="t('invoices.issueDate')" />
      <Column :header="t('common.total')">
        <template #body="{ data }"><AppMoneyDisplay :amount="data.total" /></template>
      </Column>
    </AppDataTable>
  </div>
</template>
