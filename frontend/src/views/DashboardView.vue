<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Chart from 'primevue/chart'
import ProgressBar from 'primevue/progressbar'
import AppPageHeader from '../components/ui/AppPageHeader.vue'
import AppMoneyDisplay from '../components/ui/AppMoneyDisplay.vue'
import AppNumberDisplay from '../components/ui/AppNumberDisplay.vue'
import AppDurationDisplay from '../components/ui/AppDurationDisplay.vue'
import ContractUsageBar from '../components/ContractUsageBar.vue'
import { statsApi } from '../api'
import { useNotify } from '../composables/useNotify'
import { brandColors, chartPalette } from '../theme/brand'

interface DashboardStats {
  revenue_by_month: { month: string; total: number }[]
  hours_by_customer: { customer__name: string | null; hours: number }[]
  uninvoiced_hours: number
  week_hours: number
  open_invoices: { total: number | null; count: number }
  overdue: { total: number | null; count: number }
  contracts: { id: number; name: string; period_start: string; period_end: string; used_hours: number; included_hours: number; overage_hours: number }[]
  budget_warnings: { id: number; name: string; customer: string; budget_hours_percent: number | null; budget_amount_percent: number | null }[]
  timer_running: string | null
}

const { t, locale } = useI18n()
const notify = useNotify()
const stats = ref<DashboardStats | null>(null)
// Chart.js can't read CSS variables, so re-read the theme colors when dark mode toggles.
const isDark = ref(document.documentElement.classList.contains('dark'))
const themeObserver = new MutationObserver(() => {
  isDark.value = document.documentElement.classList.contains('dark')
})
onMounted(async () => {
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
  try {
    stats.value = (await statsApi.dashboard()) as unknown as DashboardStats
  } catch (e) {
    notify.error(e)
  }
})
onUnmounted(() => themeObserver.disconnect())

const revenueChart = computed(() => stats.value && {
  labels: stats.value.revenue_by_month.map((r) =>
    new Date(r.month).toLocaleDateString(locale.value, { month: 'short', year: 'numeric' })),
  datasets: [{ label: t('dashboard.revenue'), data: stats.value.revenue_by_month.map((r) => r.total), backgroundColor: brandColors.blue }],
})
const hoursChart = computed(() => stats.value && {
  labels: stats.value.hours_by_customer.map((r) => r.customer__name ?? t('dashboard.noCustomer')),
  datasets: [{ data: stats.value.hours_by_customer.map((r) => r.hours), backgroundColor: chartPalette }],
})

const textColor = computed(() => (isDark.value ? '#a1a1aa' : '#52525b'))
const gridColor = computed(() => (isDark.value ? '#3f3f46' : '#e4e4e7'))
const chartOpts = computed(() => ({
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { ticks: { color: textColor.value }, grid: { color: gridColor.value } },
    y: { ticks: { color: textColor.value }, grid: { color: gridColor.value } },
  },
}))
const pieOpts = computed(() => ({
  maintainAspectRatio: false,
  plugins: { legend: { labels: { color: textColor.value } } },
}))
</script>

<template>
  <div>
    <AppPageHeader :title="t('dashboard.title')" />
    <div v-if="stats" class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      <div class="border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-4">
        <p class="text-sm text-surface-500">{{ t('dashboard.weekHours') }}</p>
        <p class="text-2xl font-semibold mt-1"><AppDurationDisplay :minutes="stats.week_hours * 60" /></p>
      </div>
      <div class="border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-4">
        <p class="text-sm text-surface-500">{{ t('dashboard.uninvoiced') }}</p>
        <p class="text-2xl font-semibold mt-1"><AppDurationDisplay :minutes="stats.uninvoiced_hours * 60" /></p>
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
        <p class="text-2xl font-semibold mt-1" :class="{ 'text-red-500': stats.overdue.count > 0 }">
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
