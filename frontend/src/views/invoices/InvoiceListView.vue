<script setup lang="ts">
import AppEnumSelect from '../../components/ui/AppEnumSelect.vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppStatusTag from '../../components/ui/AppStatusTag.vue'
import AppMoneyDisplay from '../../components/ui/AppMoneyDisplay.vue'
import AppDateTimeDisplay from '../../components/ui/AppDateTimeDisplay.vue'
import AppIconButton from '../../components/ui/AppIconButton.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppFilterBar, { type ActiveFilter } from '../../components/ui/AppFilterBar.vue'
import CustomerSelect from '../../components/CustomerSelect.vue'
import ProjectSelect from '../../components/ProjectSelect.vue'
import { useQueryFilters } from '../../composables/useQueryFilters'
import { invoicesApi, type Invoice } from '../../api'
import { useConfirmDelete } from '../../composables/useConfirmDelete'
import { usePagination } from '../../composables/usePagination'
import { tableStateKeys } from '../../tableStateKeys'
import { invoiceStatusValues as statuses } from '../../utils/enums'

const { t } = useI18n()
const router = useRouter()
const confirmDelete = useConfirmDelete()
const rows = ref<Invoice[]>([])
// Rarely needed actions behind the ⋮ button.
const moreMenu = ref<InstanceType<typeof Menu>>()
const moreActions = computed(() => [
  {
    label: t('invoices.importExternal'),
    icon: 'iconify lucide--upload',
    command: () => void router.push('/invoices/import'),
  },
])
const preset = useQueryFilters()
const receivableQuery = useRoute().query.receivable
const receivables = ['open', 'overdue']
const filters = ref({
  customer: preset.customer,
  project: preset.project,
  status: null as string | null,
  receivable:
    typeof receivableQuery === 'string' && receivables.includes(receivableQuery)
      ? receivableQuery
      : null,
})
const names = preset.names
const activeFilters = computed<ActiveFilter[]>(() => {
  const f = filters.value
  const active: ActiveFilter[] = []
  if (f.customer)
    active.push({ key: 'customer', label: t('projects.customer'), value: names.value.customer })
  if (f.project)
    active.push({ key: 'project', label: t('projects.project'), value: names.value.project })
  if (f.status)
    active.push({
      key: 'status',
      label: t('common.status'),
      value: t(`invoices.status.${f.status}`),
    })
  if (f.receivable)
    active.push({
      key: 'receivable',
      label: t('invoices.receivable'),
      value: t(`invoices.receivables.${f.receivable}`),
    })
  return active
})
const statusKey = (invoice: Invoice) => (invoice.partially_paid ? 'partially_paid' : invoice.status)
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
watch(filters, () => pagination.refresh(), { deep: true })

async function load() {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters.value)) if (value) params.set(key, value)
  const results = await pagination.fetchPage(invoicesApi.list, params)
  if (results) rows.value = results
}
</script>

<template>
  <div>
    <AppPageHeader :title="t('invoices.title')">
      <template #actions>
        <Button
          :label="t('invoices.new')"
          icon="iconify lucide--plus"
          @click="router.push('/invoices/new')"
        />
        <Button
          icon="iconify lucide--ellipsis-vertical"
          text
          severity="secondary"
          :aria-label="t('common.moreActions')"
          aria-haspopup="menu"
          @click="moreMenu?.toggle($event)"
        />
        <Menu ref="moreMenu" :model="moreActions" popup />
      </template>
    </AppPageHeader>

    <AppDataTable
      :rows="rows"
      :loading="pagination.loading.value"
      lazy
      :total-records="pagination.totalRecords.value"
      :first="pagination.first.value"
      :page-size="pagination.pageSize.value"
      :sort-field="pagination.sortField.value"
      :sort-order="pagination.sortOrder.value"
      :sort-options="sortOptions"
      :state-key="tableStateKeys.invoices"
      @state-restore="pagination.onRestore"
      @page="pagination.onPage"
      @sort="pagination.onSort"
      @row-click="(r: Invoice) => router.push(`/invoices/${r.id}`)"
    >
      <template #toolbar>
        <AppFilterBar
          :active="activeFilters"
          @remove="
            (key) => (filters[key as 'customer' | 'project' | 'status' | 'receivable'] = null)
          "
          @clear="filters = { customer: null, project: null, status: null, receivable: null }"
        >
          <AppFormField :label="t('projects.customer')">
            <CustomerSelect
              v-model="filters.customer"
              :placeholder="t('common.allCustomers')"
              @select="(c) => (names.customer = c?.name ?? '')"
            />
          </AppFormField>
          <AppFormField :label="t('projects.project')">
            <ProjectSelect
              v-model="filters.project"
              :customer-id="filters.customer"
              :placeholder="t('common.allProjects')"
              @select="(p) => (names.project = p?.name ?? '')"
            />
          </AppFormField>
          <AppFormField :label="t('common.status')">
            <AppEnumSelect
              v-model="filters.status"
              :options="statuses"
              label-prefix="invoices.status"
              :placeholder="t('common.all')"
              show-clear
              class="w-full"
            />
          </AppFormField>
          <AppFormField :label="t('invoices.receivable')">
            <AppEnumSelect
              v-model="filters.receivable"
              :options="receivables"
              label-prefix="invoices.receivables"
              :placeholder="t('common.all')"
              show-clear
              class="w-full"
            />
          </AppFormField>
        </AppFilterBar>
      </template>
      <Column
        field="number"
        :header="t('common.numberShort')"
        header-style="width: 6.5rem"
        sortable
      />
      <Column
        class="app-text"
        field="customer_name"
        sort-field="customer__name"
        :header="t('projects.customer')"
        sortable
      />
      <Column class="app-text" field="project_name" :header="t('projects.project')" hidden />
      <Column class="app-text" field="contract_name" :header="t('invoices.contract')" hidden />
      <Column
        field="issue_date"
        :header="t('invoices.issueDate')"
        header-style="width: 7rem"
        sortable
        ><template #body="{ data }"><AppDateTimeDisplay :value="data.issue_date" /></template
      ></Column>
      <Column field="due_date" :header="t('invoices.dueDate')" header-style="width: 7rem" sortable
        ><template #body="{ data }"><AppDateTimeDisplay :value="data.due_date" /></template
      ></Column>
      <Column class="app-num" field="subtotal" :header="t('invoices.subtotal')" hidden>
        <template #body="{ data }"
          ><AppMoneyDisplay :amount="data.subtotal" :currency="data.currency"
        /></template>
      </Column>
      <Column class="app-num" field="vat_amount" :header="t('invoices.vat')" hidden>
        <template #body="{ data }"
          ><AppMoneyDisplay :amount="data.vat_amount" :currency="data.currency"
        /></template>
      </Column>
      <Column class="app-num" field="total" :header="t('common.total')" sortable>
        <template #body="{ data }"
          ><AppMoneyDisplay :amount="data.total" :currency="data.currency"
        /></template>
      </Column>
      <Column class="app-num" field="amount_paid" :header="t('invoices.paid')" hidden>
        <template #body="{ data }"
          ><AppMoneyDisplay :amount="data.amount_paid" :currency="data.currency"
        /></template>
      </Column>
      <Column class="app-num" field="remaining" :header="t('invoices.remaining')">
        <template #body="{ data }">
          <AppMoneyDisplay
            v-if="Number(data.remaining) > 0 && data.status !== 'draft'"
            :amount="data.remaining"
            :currency="data.currency"
          />
          <span v-else>—</span>
        </template>
      </Column>
      <Column field="sent_at" :header="t('invoices.sentAt')" hidden>
        <template #body="{ data }"
          ><AppDateTimeDisplay v-if="data.sent_at" :value="data.sent_at"
        /></template>
      </Column>
      <Column field="status" :header="t('common.status')" header-style="width: 9rem" sortable>
        <template #body="{ data }">
          <AppStatusTag
            :status="statusKey(data)"
            :label="t(`invoices.status.${statusKey(data)}`)"
          />
        </template>
      </Column>
      <Column :reorderable-column="false">
        <template #body="{ data }">
          <AppIconButton
            v-if="data.status === 'draft'"
            icon="iconify lucide--trash-2"
            severity="danger"
            @click.stop="
              confirmDelete(async () => {
                await invoicesApi.remove(data.id)
                load()
              })
            "
          />
        </template>
      </Column>
      <template #card="{ row }">
        <div class="flex justify-between items-center">
          <div>
            <div class="font-medium">{{ row.number }}</div>
            <div class="text-sm text-surface-500">
              {{ row.customer_name }} · <AppDateTimeDisplay :value="row.issue_date" />
            </div>
          </div>
          <div class="text-end">
            <AppMoneyDisplay :amount="row.total" :currency="row.currency" />
            <div>
              <AppStatusTag
                :status="statusKey(row)"
                :label="t(`invoices.status.${statusKey(row)}`)"
              />
            </div>
          </div>
        </div>
      </template>
    </AppDataTable>
  </div>
</template>
