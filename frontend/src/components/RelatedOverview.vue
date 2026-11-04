<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import AppDurationDisplay from './ui/AppDurationDisplay.vue'
import AppMoneyDisplay from './ui/AppMoneyDisplay.vue'
import AppDateTimeDisplay from './ui/AppDateTimeDisplay.vue'
import AppStatusTag from './ui/AppStatusTag.vue'
import {
  invoicesApi, projectsApi, tasksApi, timeTrackingApi,
  type Invoice, type Project, type Task, type TimeEntry,
} from '../api'

// What belongs to a customer or project, at a glance: key figures plus the latest
// time entries, invoices, open tasks (and projects for a customer). Each list links
// to the full page with the same filter.
const props = defineProps<{ scope: 'customer' | 'project'; id: string }>()
const { t } = useI18n()

const uninvoicedMinutes = ref(0)
const totalMinutes = ref(0)
const entries = ref<TimeEntry[]>([])
const invoices = ref<Invoice[]>([])
const tasks = ref<Task[]>([])
const projects = ref<Project[]>([])
const loaded = ref(false)

const filter = computed(() => `${props.scope}=${props.id}`)
const openInvoices = computed(() => invoices.value.filter((invoice) => ['issued', 'sent'].includes(invoice.status)))
const openAmount = computed(() => openInvoices.value.reduce((sum, invoice) => sum + Number(invoice.remaining), 0))
const openTasks = computed(() => tasks.value.filter((task) => task.status !== 'done'))
const activeProjects = computed(() => projects.value.filter((project) => project.status === 'active'))
const invoiceStatus = (invoice: Invoice) => invoice.partially_paid ? 'partially_paid' : invoice.status

onMounted(async () => {
  const uninvoiced = `${filter.value}&billable=true&invoice__isnull=true&contract__isnull=true&end_datetime__isnull=false`
  const [open, all, entryPage, invoicePage, taskPage, projectPage] = await Promise.all([
    timeTrackingApi.summary(uninvoiced),
    timeTrackingApi.summary(filter.value),
    timeTrackingApi.list(`${filter.value}&page_size=5&ordering=-start_datetime`),
    invoicesApi.list(`${filter.value}&page_size=200&ordering=-issue_date`),
    tasksApi.list(`${filter.value}&page_size=200&ordering=due_date`),
    props.scope === 'customer' ? projectsApi.list(`customer=${props.id}&page_size=200&ordering=name`) : null,
  ])
  uninvoicedMinutes.value = open.total_minutes
  totalMinutes.value = all.total_minutes
  entries.value = entryPage.results
  invoices.value = invoicePage.results
  tasks.value = taskPage.results
  projects.value = projectPage?.results ?? []
  loaded.value = true
})

const card = 'border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900'
const row = 'flex items-center gap-3 px-4 py-2 border-t border-surface-100 dark:border-surface-800 text-sm hover:bg-surface-50 dark:hover:bg-surface-800'
</script>

<template>
  <div v-if="loaded" class="flex flex-col gap-4">
    <div class="grid grid-cols-2 xl:grid-cols-4 gap-3">
      <div :class="card" class="p-4">
        <p class="text-sm text-surface-500">{{ t('overview.uninvoiced') }}</p>
        <p class="text-xl font-semibold mt-1"><AppDurationDisplay :minutes="uninvoicedMinutes" /></p>
      </div>
      <div :class="card" class="p-4">
        <p class="text-sm text-surface-500">{{ t('overview.openInvoices') }}</p>
        <p class="text-xl font-semibold mt-1">
          <AppMoneyDisplay :amount="openAmount" />
          <span class="text-sm font-normal text-surface-500"> · {{ openInvoices.length }}</span>
        </p>
      </div>
      <div :class="card" class="p-4">
        <p class="text-sm text-surface-500">{{ t('overview.openTasks') }}</p>
        <p class="text-xl font-semibold mt-1">{{ openTasks.length }}</p>
      </div>
      <div :class="card" class="p-4">
        <template v-if="scope === 'customer'">
          <p class="text-sm text-surface-500">{{ t('overview.activeProjects') }}</p>
          <p class="text-xl font-semibold mt-1">{{ activeProjects.length }}</p>
        </template>
        <template v-else>
          <p class="text-sm text-surface-500">{{ t('overview.totalHours') }}</p>
          <p class="text-xl font-semibold mt-1"><AppDurationDisplay :minutes="totalMinutes" /></p>
        </template>
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-2 gap-4 items-start">
      <section v-if="scope === 'customer'" :class="card">
        <header class="flex items-center justify-between px-4 py-2">
          <h2 class="font-medium">{{ t('nav.projects') }}</h2>
          <router-link :to="`/projects?customer=${id}`" class="text-sm text-primary">{{ t('overview.showAll') }}</router-link>
        </header>
        <router-link v-for="project in projects.slice(0, 5)" :key="project.id" :to="`/projects/${project.id}`" :class="row">
          <span class="flex-1 min-w-0 truncate">{{ project.name }}</span>
          <span class="text-surface-500 tabular-nums"><AppDurationDisplay :minutes="project.used_hours * 60" /></span>
          <AppStatusTag :status="project.status" :label="t(`projects.status.${project.status}`)" />
        </router-link>
        <p v-if="!projects.length" class="px-4 py-3 border-t border-surface-100 dark:border-surface-800 text-sm text-surface-500">{{ t('common.empty') }}</p>
      </section>

      <section :class="card">
        <header class="flex items-center justify-between px-4 py-2">
          <h2 class="font-medium">{{ t('overview.recentTime') }}</h2>
          <router-link :to="`/time?${filter}`" class="text-sm text-primary">{{ t('overview.showAll') }}</router-link>
        </header>
        <router-link v-for="entry in entries" :key="entry.id" :to="`/time?${filter}`" :class="row">
          <AppDateTimeDisplay :value="entry.start_datetime" class="text-surface-500 tabular-nums" />
          <span class="flex-1 min-w-0 truncate">{{ entry.description || entry.project_name || '—' }}</span>
          <span class="tabular-nums"><AppDurationDisplay :minutes="entry.duration_minutes" /></span>
        </router-link>
        <p v-if="!entries.length" class="px-4 py-3 border-t border-surface-100 dark:border-surface-800 text-sm text-surface-500">{{ t('common.empty') }}</p>
      </section>

      <section :class="card">
        <header class="flex items-center justify-between px-4 py-2">
          <h2 class="font-medium">{{ t('invoices.title') }}</h2>
          <router-link :to="`/invoices?${filter}`" class="text-sm text-primary">{{ t('overview.showAll') }}</router-link>
        </header>
        <router-link v-for="invoice in invoices.slice(0, 5)" :key="invoice.id" :to="`/invoices/${invoice.id}`" :class="row">
          <span class="w-28 shrink-0 tabular-nums">{{ invoice.number }}</span>
          <AppDateTimeDisplay :value="invoice.issue_date" class="flex-1 text-surface-500 tabular-nums" />
          <AppMoneyDisplay :amount="invoice.total" :currency="invoice.currency" class="tabular-nums" />
          <AppStatusTag :status="invoiceStatus(invoice)" :label="t(`invoices.status.${invoiceStatus(invoice)}`)" />
        </router-link>
        <p v-if="!invoices.length" class="px-4 py-3 border-t border-surface-100 dark:border-surface-800 text-sm text-surface-500">{{ t('common.empty') }}</p>
      </section>

      <section :class="card">
        <header class="flex items-center justify-between px-4 py-2">
          <h2 class="font-medium">{{ t('overview.openTasks') }}</h2>
          <router-link :to="`/tasks?${filter}`" class="text-sm text-primary">{{ t('overview.showAll') }}</router-link>
        </header>
        <router-link v-for="task in openTasks.slice(0, 5)" :key="task.id" :to="`/tasks?${filter}`" :class="row">
          <span class="flex-1 min-w-0 truncate">{{ task.title }}</span>
          <AppDateTimeDisplay v-if="task.due_date" :value="task.due_date" class="text-surface-500 tabular-nums" />
          <AppStatusTag :status="task.priority" :label="t(`tasks.priorities.${task.priority}`)" />
        </router-link>
        <p v-if="!openTasks.length" class="px-4 py-3 border-t border-surface-100 dark:border-surface-800 text-sm text-surface-500">{{ t('common.empty') }}</p>
      </section>
    </div>
  </div>
</template>
