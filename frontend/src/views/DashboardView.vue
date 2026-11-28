<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Chart from 'primevue/chart'
import ProgressBar from 'primevue/progressbar'
import AppPageHeader from '../components/ui/AppPageHeader.vue'
import AppMoneyDisplay from '../components/ui/AppMoneyDisplay.vue'
import AppEmptyState from '../components/ui/AppEmptyState.vue'
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
  contracts: {
    id: number
    name: string
    period_start: string
    period_end: string
    used_hours: number
    included_hours: number
    overage_hours: number
  }[]
  budget_warnings: {
    id: number
    name: string
    customer: string
    budget_hours_percent: number | null
    budget_amount_percent: number | null
  }[]
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

// Charts only with data; otherwise the cards show an empty state instead of bare axes.
const revenueChart = computed(
  () =>
    stats.value?.revenue_by_month.some((r) => Number(r.total) > 0) && {
      labels: stats.value.revenue_by_month.map((r) =>
        new Date(r.month).toLocaleDateString(locale.value, { month: 'short', year: 'numeric' }),
      ),
      datasets: [
        {
          label: t('dashboard.revenue'),
          data: stats.value.revenue_by_month.map((r) => r.total),
          backgroundColor: brandColors.blue,
        },
      ],
    },
)
const hoursChart = computed(
  () =>
    stats.value?.hours_by_customer.length && {
      labels: stats.value.hours_by_customer.map(
        (r) => r.customer__name ?? t('dashboard.noCustomer'),
      ),
      datasets: [
        { data: stats.value.hours_by_customer.map((r) => r.hours), backgroundColor: chartPalette },
      ],
    },
)

// Each key figure opens the list it summarizes.
const monday = () => {
  const d = new Date()
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7))
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
const kpis = computed(() => {
  const s = stats.value
  if (!s) return []
  return [
    { label: t('dashboard.weekHours'), minutes: s.week_hours * 60, to: `/time?from=${monday()}` },
    { label: t('dashboard.uninvoiced'), minutes: s.uninvoiced_hours * 60, to: '/time?status=open' },
    {
      label: t('dashboard.openInvoices'),
      money: s.open_invoices.total ?? 0,
      count: s.open_invoices.count,
      to: '/invoices?receivable=open',
    },
    {
      label: t('dashboard.overdue'),
      money: s.overdue.total ?? 0,
      count: s.overdue.count,
      alert: s.overdue.count > 0,
      to: '/invoices?receivable=overdue',
    },
  ] as {
    label: string
    to: string
    minutes?: number
    money?: number
    count?: number
    alert?: boolean
  }[]
})

// Chart.js gets the PrimeVue tokens as values; reading `isDark` re-evaluates them after a theme switch.
const cssVar = (name: string) => (
  isDark.value,
  getComputedStyle(document.documentElement).getPropertyValue(name).trim()
)
const textColor = computed(() => cssVar('--p-text-muted-color'))
const gridColor = computed(() => cssVar('--p-content-border-color'))
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
      <router-link
        v-for="kpi in kpis"
        :key="kpi.label"
        :to="kpi.to"
        class="app-card p-4 hover:border-primary transition-colors"
      >
        <p class="text-sm text-surface-500">{{ kpi.label }}</p>
        <p class="text-2xl font-semibold mt-1" :class="{ 'text-danger': kpi.alert }">
          <AppMoneyDisplay v-if="kpi.money !== undefined" :amount="kpi.money" />
          <AppDurationDisplay v-else :minutes="kpi.minutes ?? 0" />
        </p>
        <p v-if="kpi.count !== undefined" class="text-sm text-surface-500 mt-0.5">
          {{ t('dashboard.invoiceCount', { n: kpi.count }, kpi.count) }}
        </p>
      </router-link>

      <div class="app-card sm:col-span-2 p-4">
        <p class="text-sm text-surface-500 mb-2">{{ t('dashboard.revenue') }}</p>
        <div class="h-56">
          <Chart
            v-if="revenueChart"
            type="bar"
            :data="revenueChart as any"
            :options="chartOpts"
            class="h-full"
          />
          <AppEmptyState
            v-else
            :message="t('dashboard.noRevenue')"
            icon="iconify lucide--chart-column"
            class="h-full"
          />
        </div>
      </div>
      <div class="app-card sm:col-span-2 p-4">
        <p class="text-sm text-surface-500 mb-2">{{ t('dashboard.hoursPerCustomer') }}</p>
        <div class="h-56">
          <Chart
            v-if="hoursChart"
            type="doughnut"
            :data="hoursChart as any"
            :options="pieOpts"
            class="h-full"
          />
          <AppEmptyState
            v-else
            :message="t('dashboard.noHours')"
            icon="iconify lucide--clock"
            class="h-full"
          />
        </div>
      </div>

      <div v-if="stats.budget_warnings.length" class="app-card sm:col-span-2 p-4">
        <p class="text-sm text-surface-500 mb-3">{{ t('dashboard.budgetWarnings') }}</p>
        <div v-for="w in stats.budget_warnings" :key="w.id" class="mb-3">
          <div class="flex justify-between text-sm">
            <router-link :to="`/projects/${w.id}`" class="text-primary">{{ w.name }}</router-link>
            <span class="text-surface-500">{{ w.customer }}</span>
          </div>
          <ProgressBar
            :value="Math.min(100, w.budget_hours_percent ?? w.budget_amount_percent ?? 0)"
            :show-value="false"
            class="mt-1"
          />
        </div>
      </div>

      <div v-if="stats.contracts.length" class="app-card sm:col-span-2 p-4">
        <p class="text-sm text-surface-500 mb-3">{{ t('dashboard.contractUsage') }}</p>
        <div v-for="c in stats.contracts" :key="c.id" class="mb-4">
          <router-link :to="`/contracts/${c.id}`" class="text-sm text-primary">{{
            c.name
          }}</router-link>
          <ContractUsageBar :usage="c" class="mt-1" />
        </div>
      </div>
    </div>
  </div>
</template>
