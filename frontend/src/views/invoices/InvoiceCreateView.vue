<script setup lang="ts">
import AppEnumSelect from '../../components/ui/AppEnumSelect.vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
import MultiSelect from 'primevue/multiselect'
import Steps from 'primevue/steps'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppIconButton from '../../components/ui/AppIconButton.vue'
import AppDateInput from '../../components/ui/AppDateInput.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppDurationDisplay from '../../components/ui/AppDurationDisplay.vue'
import AppMoneyDisplay from '../../components/ui/AppMoneyDisplay.vue'
import AppDateTimeDisplay from '../../components/ui/AppDateTimeDisplay.vue'
import AppNumberDisplay from '../../components/ui/AppNumberDisplay.vue'
import CustomerSelect from '../../components/CustomerSelect.vue'
import ProjectSelect from '../../components/ProjectSelect.vue'
import {
  bankAccountsApi, contactsApi, invoicesApi, timeTrackingApi,
  type BankAccount, type ConsolidatePreview, type ConsolidateRequest, type Contact, type TimeEntry,
} from '../../api'
import { ApiError } from '../../api/client'
import { errorText } from '../../composables/formErrors'
import { useNotify } from '../../composables/useNotify'
import { useUnsavedChanges } from '../../composables/useUnsavedChanges'
import { tableStateKeys } from '../../tableStateKeys'

const { t } = useI18n()
const router = useRouter()
const notify = useNotify()

const query = useRoute().query
const step = ref(0)
// Prefilled from customer/project overviews ("Rechnung erstellen").
const customerId = ref<string | null>(typeof query.customer === 'string' ? query.customer : null)
const projectId = ref<string | null>(typeof query.project === 'string' ? query.project : null)
const dateFrom = ref<string | null>(null)
const dateTo = ref<string | null>(null)
const groupBy = ref('entry')
const eInvoiceFormat = ref('none')
const entries = ref<TimeEntry[]>([])
const availableContacts = ref<Contact[]>([])
const contactIds = ref<string[]>([])
const bankAccounts = ref<BankAccount[]>([])
const bankAccountId = ref<string | null>(null)
const creating = ref(false)
const created = ref(false)

interface ManualLine {
  id: string
  description: string
  quantity: number
  unit: string
  unit_price: number
}
const manualLines = ref<ManualLine[]>([])
const lineForm = ref({ description: '', quantity: 1, unit: 'flat', unit_price: 0 })
const units = ['hours', 'flat', 'piece']

function addLine() {
  if (!lineForm.value.description.trim()) return
  manualLines.value.push({ id: crypto.randomUUID(), ...lineForm.value })
  lineForm.value = { description: '', quantity: 1, unit: 'flat', unit_price: 0 }
}

const groupBys = ['entry', 'day', 'project']
const formats = ['none', 'zugferd', 'xrechnung']
const steps = computed(() => [
  { label: t('projects.customer') },
  { label: t('invoices.invoiceLines') },
  { label: t('invoices.reviewStep') },
])

onMounted(async () => {
  bankAccounts.value = (await bankAccountsApi.list()).results.filter((account) => account.is_active)
})

watch(customerId, async (value) => {
  if (!value) {
    availableContacts.value = []
    contactIds.value = []
    return
  }
  availableContacts.value = (await contactsApi.list(value)).results
  contactIds.value = availableContacts.value
    .filter((contact) => contact.is_invoice_contact)
    .map((contact) => contact.id)
}, { immediate: true })

// Entries the user unticked in step 2; everything else gets billed.
const excluded = ref(new Set<string>())
const selectedEntries = computed(() => entries.value.filter((entry) => !excluded.value.has(entry.id)))
const selectedMinutes = computed(() => selectedEntries.value.reduce((sum, entry) => sum + entry.duration_minutes, 0))
const allSelected = computed(() => entries.value.length > 0 && excluded.value.size === 0)

function toggleEntry(entry: TimeEntry) {
  const next = new Set(excluded.value)
  if (!next.delete(entry.id)) next.add(entry.id)
  excluded.value = next
}

function toggleAll() {
  excluded.value = allSelected.value ? new Set(entries.value.map((entry) => entry.id)) : new Set()
}

let entriesRequest = 0
watch([customerId, projectId, dateFrom, dateTo], async () => {
  const request = ++entriesRequest
  excluded.value = new Set()
  if (!customerId.value) {
    entries.value = []
    return
  }
  const params = new URLSearchParams({
    customer: String(customerId.value),
    billable: 'true',
    invoice__isnull: 'true',
    contract__isnull: 'true',
    end_datetime__isnull: 'false',
    ordering: 'start_datetime',
  })
  if (projectId.value) params.set('project', String(projectId.value))
  if (dateFrom.value) params.set('start_datetime__date__gte', dateFrom.value)
  if (dateTo.value) params.set('start_datetime__date__lte', dateTo.value)
  const page = await timeTrackingApi.list(`${params.toString()}&page_size=500`)
  if (request !== entriesRequest) return
  entries.value = page.results
}, { immediate: true })

const payload = computed<ConsolidateRequest | null>(() => customerId.value
  ? {
      customer_id: customerId.value,
      project_id: projectId.value,
      contact_ids: contactIds.value,
      bank_account_id: bankAccountId.value,
      date_from: dateFrom.value,
      date_to: dateTo.value,
      entry_ids: selectedEntries.value.map((entry) => entry.id),
      group_by: groupBy.value,
      e_invoice_format: eInvoiceFormat.value,
      extra_lines: manualLines.value,
    }
  : null)

// Server-side dry run of the invoice, so amounts (and e.g. a missing hourly
// rate) show up before anything is created.
const preview = ref<ConsolidatePreview | null>(null)
const previewError = ref('')
let previewTimer: ReturnType<typeof setTimeout> | undefined
let previewRequest = 0
watch(payload, (value) => {
  clearTimeout(previewTimer)
  if (!value || (!value.entry_ids?.length && !manualLines.value.length)) {
    preview.value = null
    previewError.value = ''
    return
  }
  previewTimer = setTimeout(async () => {
    const request = ++previewRequest
    try {
      const result = await invoicesApi.consolidatePreview(value)
      if (request !== previewRequest) return
      preview.value = result
      previewError.value = ''
    } catch (e) {
      if (request !== previewRequest) return
      preview.value = null
      previewError.value = e instanceof ApiError && e.data ? errorText(e.data) : t('common.error')
    }
  }, 300)
}, { deep: true })
// Leaving after step 1 or with own lines would lose the selection.
useUnsavedChanges(
  computed(() => ({ started: step.value > 0, lines: manualLines.value.length })),
  () => !created.value,
)
const canCreate = computed(() => !!payload.value && !previewError.value
  && (selectedEntries.value.length > 0 || manualLines.value.length > 0))


async function create() {
  if (!payload.value || !canCreate.value) return
  creating.value = true
  try {
    const inv = await invoicesApi.consolidate(payload.value)
    created.value = true
    router.push(`/invoices/${inv.id}`)
  } catch (e) {
    notify.error(e)
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div>
    <AppPageHeader back-to="/invoices" :back-label="t('nav.invoices')" :title="t('invoices.new')" />
    <Steps :model="steps" :active-step="step" class="mb-6" :readonly="!customerId" @update:active-step="(s: number) => step = s" />

    <div v-if="step === 0" class="flex flex-col gap-4 max-w-lg">
      <AppFormField :label="t('projects.customer')" required><CustomerSelect v-model="customerId" /></AppFormField>
      <AppFormField :label="t('projects.project')"><ProjectSelect v-model="projectId" :customer-id="customerId" /></AppFormField>
      <AppFormField :label="t('invoices.contacts')">
        <MultiSelect v-model="contactIds" :show-toggle-all="false" :options="availableContacts" option-label="name" option-value="id" display="chip" class="w-full" />
      </AppFormField>
      <div class="grid grid-cols-2 gap-3">
        <AppFormField :label="t('invoices.dateFrom')"><AppDateInput v-model="dateFrom" /></AppFormField>
        <AppFormField :label="t('invoices.dateTo')"><AppDateInput v-model="dateTo" /></AppFormField>
      </div>
      <div class="flex justify-end gap-2">
        <Button :label="t('common.cancel')" text @click="router.push('/invoices')" />
        <Button :label="t('common.next')" icon="pi pi-arrow-right" icon-pos="right" :disabled="!customerId" @click="step = 1" />
      </div>
    </div>

    <div v-else-if="step === 1">
      <div class="flex flex-wrap items-baseline justify-between gap-2 mb-3 text-sm">
        <span class="text-surface-500">
          {{ t('invoices.selectedEntries', { selected: selectedEntries.length, total: entries.length }) }} · <AppDurationDisplay :minutes="selectedMinutes" />
        </span>
        <span v-if="preview">{{ t('invoices.subtotal') }}: <AppMoneyDisplay :amount="preview.subtotal" class="font-semibold" /></span>
      </div>
      <Message v-if="previewError" severity="warn" class="mb-3">{{ previewError }}</Message>
      <AppDataTable :rows="entries" :state-key="tableStateKeys.invoiceSourceEntries" @row-click="toggleEntry">
        <Column class="w-10" :reorderable-column="false">
          <template #header><Checkbox :model-value="allSelected" :indeterminate="excluded.size > 0 && excluded.size < entries.length" binary :aria-label="t('table.selectPage')" @update:model-value="toggleAll" /></template>
          <template #body="{ data }"><Checkbox :model-value="!excluded.has(data.id)" binary @click.stop @update:model-value="toggleEntry(data)" /></template>
        </Column>
        <Column field="start_datetime" :header="t('common.date')" sortable><template #body="{ data }"><AppDateTimeDisplay :value="data.start_datetime" type="datetime" /></template></Column>
        <Column class="app-text" field="project_name" :header="t('projects.project')" sortable />
        <Column class="app-text" field="description" :header="t('time.description')" sortable />
        <Column class="app-num" field="duration_minutes" :header="t('time.duration')" sortable>
          <template #body="{ data }"><AppDurationDisplay :minutes="data.duration_minutes" /></template>
        </Column>
      </AppDataTable>

      <h2 class="font-semibold mt-6 mb-2">{{ t('invoices.manualLines') }}</h2>
      <AppDataTable v-if="manualLines.length" :rows="manualLines" :state-key="tableStateKeys.invoiceManualLines" class="mb-3">
        <Column class="app-text" field="description" :header="t('time.description')" sortable />
        <Column class="app-num" field="quantity" :header="t('invoices.quantity')" sortable />
        <Column class="app-num" :header="t('invoices.unitPrice')">
          <template #body="{ data }"><AppMoneyDisplay :amount="data.unit_price" /></template>
        </Column>
        <Column class="app-num" :header="t('common.total')">
          <template #body="{ data }"><AppMoneyDisplay :amount="data.quantity * data.unit_price" /></template>
        </Column>
        <Column :header="t('common.actions')" :reorderable-column="false">
          <template #body="{ index }"><AppIconButton icon="pi pi-trash" severity="danger" @click.stop="manualLines.splice(index, 1)" /></template>
        </Column>
      </AppDataTable>
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-[minmax(240px,1fr)_120px_140px_140px] gap-2 items-end">
        <AppFormField field="description" :label="t('time.description')" class="min-w-0"><InputText v-model="lineForm.description" class="w-full min-w-0" /></AppFormField>
        <AppFormField field="quantity" :label="t('invoices.quantity')" class="min-w-0"><InputNumber v-model="lineForm.quantity" :min="0" :min-fraction-digits="0" :max-fraction-digits="2" class="w-full min-w-0" fluid /></AppFormField>
        <AppFormField :label="t('invoices.unit')" class="min-w-0">
          <AppEnumSelect v-model="lineForm.unit" :options="units" label-prefix="invoices.units" class="w-full min-w-0" />
        </AppFormField>
        <AppFormField field="unit_price" :label="t('invoices.unitPrice')" class="min-w-0"><InputNumber v-model="lineForm.unit_price" mode="currency" currency="EUR" class="w-full min-w-0" fluid /></AppFormField>
      </div>
      <Button :label="t('invoices.addLine')" icon="pi pi-plus" size="small" text class="mt-2" :disabled="!lineForm.description.trim()" @click="addLine" />

      <div class="flex justify-end gap-2 mt-6">
        <Button :label="t('common.back')" text @click="step = 0" />
        <Button :label="t('common.next')" icon="pi pi-arrow-right" icon-pos="right" :disabled="!canCreate" @click="step = 2" />
      </div>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-[minmax(0,28rem)_minmax(0,1fr)] gap-6 items-start">
      <div class="flex flex-col gap-4">
        <AppFormField :label="t('invoices.groupBy')">
          <AppEnumSelect v-model="groupBy" :options="groupBys" label-prefix="invoices.groupBys" class="w-full" />
        </AppFormField>
        <Message v-if="!bankAccounts.some((account) => account.iban)" severity="warn">
          {{ t('invoices.noIbanHint') }}
          <router-link to="/settings?tab=bankAccounts" class="underline font-medium">{{ t('invoices.noIbanLink') }}</router-link>
        </Message>
        <AppFormField :label="t('settings.bankAccount')">
          <Select v-model="bankAccountId" :options="bankAccounts" option-label="name" option-value="id" show-clear :placeholder="t('invoices.inheritedBankAccount')" class="w-full" />
        </AppFormField>
        <AppFormField :label="t('invoices.eInvoice')">
          <AppEnumSelect v-model="eInvoiceFormat" :options="formats" label-prefix="invoices.eInvoiceFormats" class="w-full" />
        </AppFormField>
      </div>

      <div class="app-card text-sm">
        <div class="px-4 py-2 border-b border-surface-200 dark:border-surface-800 font-medium">{{ t('invoices.summary') }}</div>
        <Message v-if="previewError" severity="warn" class="m-4">{{ previewError }}</Message>
        <template v-else-if="preview">
          <div class="max-h-80 overflow-y-auto">
            <div v-for="(line, index) in preview.lines" :key="index" class="flex gap-3 px-4 py-1.5 border-b border-surface-100 dark:border-surface-800">
              <span class="flex-1 min-w-0 truncate" :title="line.description">{{ line.description }}</span>
              <span class="text-surface-500 whitespace-nowrap tabular-nums"><AppNumberDisplay :value="line.quantity" /> × <AppMoneyDisplay :amount="line.unit_price" /></span>
              <AppMoneyDisplay :amount="line.total" class="w-24 text-right tabular-nums" />
            </div>
          </div>
          <div class="px-4 py-3 flex flex-col gap-1 tabular-nums">
            <div class="flex justify-between"><span>{{ t('invoices.subtotal') }}</span><AppMoneyDisplay :amount="preview.subtotal" /></div>
            <div class="flex justify-between text-surface-500"><span>{{ t('invoices.vat') }} (<AppNumberDisplay :value="preview.vat_rate" :maximum-fraction-digits="2" /> %)</span><AppMoneyDisplay :amount="preview.vat_amount" /></div>
            <div class="flex justify-between font-semibold text-base"><span>{{ t('common.total') }}</span><AppMoneyDisplay :amount="preview.total" /></div>
          </div>
        </template>
      </div>

      <div class="lg:col-span-2 flex justify-end gap-2">
        <Button :label="t('common.back')" text @click="step = 1" />
        <Button :label="t('common.create')" icon="pi pi-check" :loading="creating" :disabled="!canCreate" @click="create" />
      </div>
    </div>
  </div>
</template>
