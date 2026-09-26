<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Chart from 'primevue/chart'
import ProgressBar from 'primevue/progressbar'
import AppPageHeader from '../components/ui/AppPageHeader.vue'
import AppMoneyDisplay from '../components/ui/AppMoneyDisplay.vue'
import AppNumberDisplay from '../components/ui/AppNumberDisplay.vue'
import ContractUsageBar from '../components/ContractUsageBar.vue'
import { statsApi } from '../api'

interface DashboardStats {
  revenue_by_month: { month: string; total: number }[]
  hours_by_customer: { project__customer__name: string; hours: number }[]
  uninvoiced_hours: number
  week_hours: number
  open_invoices: { total: number | null; count: number }
  overdue: { total: number | null; count: number }
  contracts: { id: number; name: string; period_start: string; period_end: string; used_hours: number; included_hours: number; overage_hours: number }[]
  budget_warnings: { id: number; name: string; customer: string; budget_hours_percent: number | null; budget_amount_percent: number | null }[]
  timer_running: string | null
}

const { t } = useI18n()
const stats = ref<DashboardStats | null>(null)
const revenueChart = ref<unknown>(null)
const hoursChart = ref<unknown>(null)

onMounted(async () => {
  stats.value = (await statsApi.dashboard()) as unknown as DashboardStats
  revenueChart.value = {
    labels: stats.value.revenue_by_month.map((r) => r.month.slice(0, 7)),
    datasets: [{ label: t('dashboard.revenue'), data: stats.value.revenue_by_month.map((r) => r.total), backgroundColor: '#2563eb' }],
  }
  hoursChart.value = {
    labels: stats.value.hours_by_customer.map((r) => r.project__customer__name),
    datasets: [{ data: stats.value.hours_by_customer.map((r) => r.hours), backgroundColor: ['#2563eb', '#16a34a', '#ea580c', '#9333ea', '#0d9488', '#dc2626', '#ca8a04', '#4f46e5'] }],
  }
})

const chartOpts = { maintainAspectRatio: false, plugins: { legend: { display: false } } }
const pieOpts = { maintainAspectRatio: false }
</script>

<template>
  <div>
    <AppPageHeader :title="t('dashboard.title')" />
    <div v-if="stats" class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      <div class="border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-4">
        <p class="text-sm text-surface-500">{{ t('dashboard.weekHours') }}</p>
        <p class="text-2xl font-semibold mt-1"><AppNumberDisplay :value="stats.week_hours" :minimum-fraction-digits="1" :maximum-fraction-digits="1" />h</p>
      </div>
      <div class="border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-4">
        <p class="text-sm text-surface-500">{{ t('dashboard.uninvoiced') }}</p>
        <p class="text-2xl font-semibold mt-1"><AppNumberDisplay :value="stats.uninvoiced_hours" :minimum-fraction-digits="1" :maximum-fraction-digits="1" />h</p>
      </div>
      <div class="border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-4">
        <p class="text-sm text-surface-500">{{ t('dashboard.openInvoices') }}</p>
        <p class="text-2xl font-semibold mt-1">
          <AppMoneyDisplay :amount="stats.open_invoices.total ?? 0" />
          <span class="text-sm font-normal text-surface-500"> (<AppNumberDisplay :value="stats.open_invoices.count" :maximum-fraction-digits="0" />)</span>
        </p>
      </div>
      <div class="border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-4">
        <p class="text-sm text-surface-500">{{ t('dashboard.overdue') }}</p>
        <p class="text-2xl font-semibold mt-1 text-red-500">
          <AppMoneyDisplay :amount="stats.overdue.total ?? 0" />
          <span class="text-sm font-normal"> (<AppNumberDisplay :value="stats.overdue.count" :maximum-fraction-digits="0" />)</span>
        </p>
      </div>

      <div class="sm:col-span-2 border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-4">
        <p class="text-sm text-surface-500 mb-2">{{ t('dashboard.revenue') }}</p>
        <div class="h-56"><Chart v-if="revenueChart" type="bar" :data="(revenueChart as any)" :options="chartOpts" class="h-full" /></div>
      </div>
      <div class="sm:col-span-2 border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-4">
        <p class="text-sm text-surface-500 mb-2">{{ t('dashboard.hoursPerCustomer') }}</p>
        <div class="h-56"><Chart v-if="hoursChart" type="doughnut" :data="(hoursChart as any)" :options="pieOpts" class="h-full" /></div>
      </div>

      <div v-if="stats.budget_warnings.length" class="sm:col-span-2 border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-4">
        <p class="text-sm text-surface-500 mb-3">{{ t('dashboard.budgetWarnings') }}</p>
        <div v-for="w in stats.budget_warnings" :key="w.id" class="mb-3">
          <div class="flex justify-between text-sm">
            <router-link :to="`/projects/${w.id}`" class="text-primary">{{ w.name }}</router-link>
            <span class="text-surface-500">{{ w.customer }}</span>
          </div>
          <ProgressBar :value="Math.min(100, w.budget_hours_percent ?? w.budget_amount_percent ?? 0)" :show-value="false" class="mt-1" />
        </div>
      </div>

      <div v-if="stats.contracts.length" class="sm:col-span-2 border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-4">
        <p class="text-sm text-surface-500 mb-3">{{ t('dashboard.contractUsage') }}</p>
        <div v-for="c in stats.contracts" :key="c.id" class="mb-4">
          <router-link :to="`/contracts/${c.id}`" class="text-sm text-primary">{{ c.name }}</router-link>
          <ContractUsageBar :usage="c" class="mt-1" />
        </div>
      </div>
    </div>
  </div>
</template>
