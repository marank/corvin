<script setup lang="ts">
import { useTabQuery } from '../../composables/useTabQuery'
import { ref } from 'vue'
import { useLoadFailed } from '../../composables/useLoadFailed'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import Button from 'primevue/button'
import Column from 'primevue/column'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import AppLoadState from '../../components/ui/AppLoadState.vue'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppDurationDisplay from '../../components/ui/AppDurationDisplay.vue'
import AppMoneyDisplay from '../../components/ui/AppMoneyDisplay.vue'
import AppDateTimeDisplay from '../../components/ui/AppDateTimeDisplay.vue'
import ContractUsageBar from '../../components/ContractUsageBar.vue'
import ContractFormFields from '../../components/ContractFormFields.vue'
import {
  contractsApi,
  invoicesApi,
  timeTrackingApi,
  type ContractUsage,
  type Invoice,
  type SupportContract,
  type TimeEntry,
} from '../../api'
import { useNotify } from '../../composables/useNotify'
import { useConfirmDelete } from '../../composables/useConfirmDelete'
import { useUnsavedChanges } from '../../composables/useUnsavedChanges'
import { tableStateKeys } from '../../tableStateKeys'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const notify = useNotify()
const confirm = useConfirm()
const confirmDelete = useConfirmDelete()
const id = route.params.id as string

const contract = ref<SupportContract | null>(null)
const form = ref<Partial<SupportContract>>({})
const { markSaved } = useUnsavedChanges(form)
const usage = ref<ContractUsage | null>(null)
const entries = ref<TimeEntry[]>([])
const invoices = ref<Invoice[]>([])
const running = ref(false)
const saving = ref(false)
const tab = useTabQuery('overview', ['overview', 'details'])

async function load() {
  contract.value = await contractsApi.get(id)
  form.value = { ...contract.value }
  markSaved()
  usage.value = await contractsApi.usage(id)
  entries.value = (await timeTrackingApi.list(`contract=${id}&page_size=500`)).results
  invoices.value = (await invoicesApi.list(`contract=${id}&page_size=500`)).results
}
const loadFailed = useLoadFailed(load)

async function save() {
  saving.value = true
  try {
    await contractsApi.update(id, form.value)
    notify.ok(t('common.saved'))
    await load()
  } catch (e) {
    notify.error(e)
  } finally {
    saving.value = false
  }
}

// Billing creates an invoice and advances the billing date, so it asks first.
function confirmRunNow() {
  confirm.require({
    header: t('contracts.runNow'),
    message: t('contracts.runNowConfirm'),
    icon: 'pi pi-file',
    rejectLabel: t('common.cancel'),
    rejectProps: { text: true },
    acceptLabel: t('contracts.runNow'),
    accept: () => void runNow(),
  })
}

async function runNow() {
  running.value = true
  try {
    const inv = await contractsApi.runNow(id)
    notify.ok(t('contracts.generatedInvoice'))
    if (inv.id) void router.push(`/invoices/${inv.id}`)
    else void load()
  } catch (e) {
    notify.error(e)
  } finally {
    running.value = false
  }
}
</script>

<template>
  <div v-if="contract">
    <AppPageHeader
      back-to="/contracts"
      :back-label="t('nav.contracts')"
      :title="contract.name"
      :subtitle="`${contract.number} · ${contract.customer_name}`"
    >
      <template #actions>
        <Button
          :label="t('common.delete')"
          text
          severity="danger"
          @click="
            confirmDelete(async () => {
              await contractsApi.remove(id)
              router.push('/contracts')
            })
          "
        />
        <Button
          v-if="tab === 'overview'"
          :label="t('contracts.runNow')"
          icon="pi pi-play"
          :loading="running"
          @click="confirmRunNow"
        />
        <Button
          v-if="tab === 'details'"
          :label="t('common.save')"
          :loading="saving"
          @click="save"
        />
      </template>
    </AppPageHeader>

    <Tabs v-model:value="tab">
      <TabList>
        <Tab value="overview">{{ t('overview.title') }}</Tab>
        <Tab value="details">{{ t('overview.masterData') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="overview">
          <div class="flex flex-col gap-4 pt-4">
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div class="app-card p-4">
                <p class="text-sm text-surface-500 mb-2">
                  {{ t('contracts.usage') }} (<AppDateTimeDisplay :value="usage?.period_start" /> –
                  <AppDateTimeDisplay :value="usage?.period_end" />)
                </p>
                <ContractUsageBar v-if="usage" :usage="usage" />
              </div>
              <div class="app-card p-4">
                <p class="text-sm text-surface-500">{{ t('contracts.fixedPrice') }}</p>
                <p class="text-xl font-semibold mt-1">
                  <AppMoneyDisplay :amount="contract.fixed_price" />
                </p>
                <p class="text-sm text-surface-500 mt-1">
                  {{ t(`contracts.periods.${contract.period}`) }} ·
                  <AppDurationDisplay :minutes="contract.included_hours * 60" />
                </p>
              </div>
              <div class="app-card p-4">
                <p class="text-sm text-surface-500">{{ t('contracts.nextBilling') }}</p>
                <p class="text-xl font-semibold mt-1">
                  <AppDateTimeDisplay :value="contract.next_billing_date" />
                </p>
                <p class="text-sm text-surface-500 mt-1">
                  <AppDateTimeDisplay :value="contract.start_date" /> –
                  <AppDateTimeDisplay v-if="contract.end_date" :value="contract.end_date" /><span
                    v-else
                    >∞</span
                  >
                </p>
              </div>
            </div>

            <div class="grid grid-cols-1 xl:grid-cols-2 gap-4 items-start">
              <section>
                <h2 class="font-semibold mb-2">{{ t('time.title') }}</h2>
                <AppDataTable :rows="entries" :state-key="tableStateKeys.contractTimeEntries">
                  <Column field="start_datetime" :header="t('common.date')" sortable
                    ><template #body="{ data }"
                      ><AppDateTimeDisplay :value="data.start_datetime" /></template
                  ></Column>
                  <Column
                    class="app-text"
                    field="description"
                    :header="t('time.description')"
                    sortable
                  />
                  <Column
                    class="app-num"
                    field="duration_minutes"
                    :header="t('time.duration')"
                    sortable
                  >
                    <template #body="{ data }"
                      ><AppDurationDisplay :minutes="data.duration_minutes"
                    /></template>
                  </Column>
                </AppDataTable>
              </section>
              <section>
                <h2 class="font-semibold mb-2">{{ t('invoices.title') }}</h2>
                <AppDataTable
                  :rows="invoices"
                  :state-key="tableStateKeys.contractInvoices"
                  @row-click="(r: Invoice) => router.push(`/invoices/${r.id}`)"
                >
                  <Column field="number" :header="t('common.numberShort')" sortable />
                  <Column field="issue_date" :header="t('invoices.issueDate')" sortable
                    ><template #body="{ data }"
                      ><AppDateTimeDisplay :value="data.issue_date" /></template
                  ></Column>
                  <Column class="app-num" field="total" :header="t('common.total')" sortable>
                    <template #body="{ data }"
                      ><AppMoneyDisplay :amount="data.total" :currency="data.currency"
                    /></template>
                  </Column>
                </AppDataTable>
              </section>
            </div>
          </div>
        </TabPanel>
        <TabPanel value="details">
          <div class="max-w-3xl pt-4"><ContractFormFields v-model="form" /></div>
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
  <AppLoadState v-else :failed="loadFailed" back-to="/contracts" :back-label="t('nav.contracts')" />
</template>
