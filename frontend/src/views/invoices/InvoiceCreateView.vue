<script setup lang="ts">
import AppEnumSelect from '../../components/ui/AppEnumSelect.vue'
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import Button from 'primevue/button'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
import MultiSelect from 'primevue/multiselect'
import Column from 'primevue/column'
import Textarea from 'primevue/textarea'
import InputNumber from 'primevue/inputnumber'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppIconButton from '../../components/ui/AppIconButton.vue'
import AppDateInput from '../../components/ui/AppDateInput.vue'
import AppSegmented from '../../components/ui/AppSegmented.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppDurationDisplay from '../../components/ui/AppDurationDisplay.vue'
import AppMoneyDisplay from '../../components/ui/AppMoneyDisplay.vue'
import AppDateTimeDisplay from '../../components/ui/AppDateTimeDisplay.vue'
import AppNumberDisplay from '../../components/ui/AppNumberDisplay.vue'
import AppModal from '../../components/ui/AppModal.vue'
import CustomerSelect from '../../components/CustomerSelect.vue'
import NumberField from '../../components/NumberField.vue'
import ProjectSelect from '../../components/ProjectSelect.vue'
import {
  bankAccountsApi,
  contactsApi,
  customersApi,
  settingsApi,
  invoicesApi,
  templatesApi,
  timeTrackingApi,
  type BankAccount,
  type ConsolidatePreview,
  type ConsolidateRequest,
  type Contact,
  type DocumentTemplate,
  type TimeEntry,
} from '../../api'
import { ApiError } from '../../api/client'
import { errorText } from '../../composables/formErrors'
import { isoDate } from '../../dateTimeInput'
import { useNotify } from '../../composables/useNotify'
import { useUnsavedChanges } from '../../composables/useUnsavedChanges'
import { tableStateKeys } from '../../tableStateKeys'
import { useInvoiceTrips } from './useInvoiceTrips'
import { lineItemUnitValues as units, eInvoiceFormatValues as formats } from '../../utils/enums'

const { t } = useI18n()
const router = useRouter()
const notify = useNotify()
const confirm = useConfirm()

// Two sections: "Allgemein" with the invoice's fields, then its lines. "Positionen holen"
// only picks which time entries the invoice bills; the grouping above the table decides
// how they become lines (per entry, day or project). Hours and prices come from the
// entries and rates (computed by the server); the text of each line is the user's.
// The same page edits a draft (/invoices/:id/edit): it loads the draft's entries, grouping,
// texts and fields, and saving replaces them (entries no longer on a line are open again).
const route = useRoute()
const query = route.query
const invoiceId = typeof route.params.id === 'string' ? route.params.id : null
const invoiceNumber = ref('')
// The draft's number, correctable by hand until it is finalized.
const numberInput = ref<string | undefined>(undefined)
const backTo = invoiceId ? `/invoices/${invoiceId}` : '/invoices'
// While the draft is loading, the watchers below must not react to its values.
let loadingDraft = invoiceId !== null
// Prefilled from customer/project overviews ("Rechnung erstellen").
const customerId = ref<string | null>(
  !invoiceId && typeof query.customer === 'string' ? query.customer : null,
)
const projectId = ref<string | null>(
  !invoiceId && typeof query.project === 'string' ? query.project : null,
)
const eInvoiceFormat = ref('none')
const availableContacts = ref<Contact[]>([])
const contactIds = ref<string[]>([])
const bankAccounts = ref<BankAccount[]>([])
const bankAccountId = ref<string | null>(null)
// The account the invoice gets without a choice: the customer's, else the company default.
// It is preselected; only a different choice is sent (as the invoice's own account).
const companyBankAccountId = ref<string | null>(null)
const defaultBankAccountId = ref<string | null>(null)
const defaultEInvoiceFormat = ref('none')
const issueDate = ref<string | null>(isoDate())
// Due: issue date + the customer's (else the company's) payment terms, following the issue
// date until the user picks a date of their own.
const companyPaymentTerms = ref(14)
const customerPaymentTerms = ref<number | null>(null)
const ownDueDate = ref<string | null>(null)
const suggestedDueDate = computed(() => {
  if (!issueDate.value) return null
  const date = new Date(`${issueDate.value}T12:00:00`)
  date.setDate(date.getDate() + (customerPaymentTerms.value ?? companyPaymentTerms.value))
  return isoDate(date)
})
const dueDate = computed({
  get: () => ownDueDate.value ?? suggestedDueDate.value,
  set: (value) => {
    ownDueDate.value = value && value !== suggestedDueDate.value ? value : null
  },
})
const defaultVatRate = ref(0)
const vatRate = ref(0)
const templates = ref<DocumentTemplate[]>([])
// Empty: the template assigned to invoices in the settings.
const templateId = ref<string | null>(null)
const notes = ref('')
// Rarely needed fields sit behind "Mehr anzeigen"; a loaded draft opens it when one of them
// differs from its default, so nothing set is hidden at first.
const showMore = ref(false)
const moreDeviates = computed(
  () =>
    bankAccountId.value !== defaultBankAccountId.value ||
    eInvoiceFormat.value !== defaultEInvoiceFormat.value ||
    vatRate.value !== defaultVatRate.value ||
    !!templateId.value ||
    !!notes.value.trim(),
)
const creating = ref(false)
const created = ref(false)

// The entries the invoice bills, the grouping, and the user's texts by line key.
const billed = ref<TimeEntry[]>([])
const billedIds = computed(() => billed.value.map((entry) => entry.id))
const trips = useInvoiceTrips()
const groupBy = ref('day')
const groupByOptions = computed(() =>
  ['entry', 'day', 'project'].map((value) => ({ value, label: t(`invoices.groupBys.${value}`) })),
)
const texts = ref<Record<string, string>>({})
// The segmented control keeps its own selection; remounting it shows groupBy again after a cancel.
const groupByKey = ref(0)

interface OwnLine {
  id: string
  description: string
  quantity: number
  unit: string
  unit_price: number
}
const ownLines = ref<OwnLine[]>([])

function addOwnLine() {
  ownLines.value.push({
    id: crypto.randomUUID(),
    description: '',
    quantity: 1,
    unit: 'flat',
    unit_price: 0,
  })
}

const companyLoaded = (async () => {
  const [accounts, company, templatePage] = await Promise.all([
    bankAccountsApi.list(),
    settingsApi.get(),
    templatesApi.list('page_size=500&ordering=name'),
  ])
  bankAccounts.value = accounts.results.filter((account) => account.is_active)
  templates.value = templatePage.results
  companyBankAccountId.value = (company.default_bank_account as string | null) ?? null
  companyPaymentTerms.value = (company.payment_terms_days as number | undefined) ?? 14
  defaultVatRate.value = company.vat_enabled === false ? 0 : Number(company.default_vat_rate ?? 19)
  vatRate.value = defaultVatRate.value
})()

watch(customerId, async (value) => {
  if (loadingDraft) return
  // Lines bill the previous customer's entries.
  billed.value = []
  trips.billed.value = []
  texts.value = {}
  await loadCustomer(value)
})

// The customer's defaults (bank account, e-invoice, payment terms) and invoice contacts.
async function loadCustomer(value: string | null) {
  if (!value) {
    availableContacts.value = []
    contactIds.value = []
    customerPaymentTerms.value = null
    return
  }
  const [customer] = await Promise.all([customersApi.get(value), companyLoaded])
  defaultBankAccountId.value = customer.bank_account ?? companyBankAccountId.value
  bankAccountId.value = defaultBankAccountId.value
  defaultEInvoiceFormat.value = customer.e_invoice_format
  eInvoiceFormat.value = customer.e_invoice_format
  customerPaymentTerms.value = customer.payment_terms_days
  availableContacts.value = (await contactsApi.list(value)).results
  contactIds.value = availableContacts.value
    .filter((contact) => contact.is_invoice_contact)
    .map((contact) => contact.id)
}

// Entries the draft billed when loaded; removed from it, they are offered again.
const draftEntries = ref<TimeEntry[]>([])

async function loadDraft(id: string) {
  const [invoice, state] = await Promise.all([invoicesApi.get(id), invoicesApi.draft(id)])
  if (invoice.status !== 'draft') {
    void router.replace(`/invoices/${id}`)
    return
  }
  invoiceNumber.value = invoice.number
  numberInput.value = invoice.number
  customerId.value = invoice.customer
  projectId.value = invoice.project
  await loadCustomer(invoice.customer)
  contactIds.value = invoice.contacts.map((contact) => contact.id)
  bankAccountId.value = invoice.bank_account_override ?? defaultBankAccountId.value
  eInvoiceFormat.value = invoice.e_invoice_format
  issueDate.value = invoice.issue_date
  dueDate.value = invoice.due_date
  vatRate.value = Number(invoice.vat_rate)
  templateId.value = invoice.template
  notes.value = invoice.notes
  // Collapsed as on a new invoice, unless something in it differs from the defaults.
  showMore.value = moreDeviates.value
  groupBy.value = state.group_by
  groupByKey.value++
  billed.value = state.entries
  draftEntries.value = state.entries
  trips.billed.value = state.trips
  texts.value = { ...state.texts, ...state.trip_texts }
  ownLines.value = state.own_lines.map((line) => ({
    id: crypto.randomUUID(),
    description: line.description,
    quantity: Number(line.quantity),
    unit: line.unit,
    unit_price: Number(line.unit_price),
  }))
  await nextTick()
  loadingDraft = false
  markSaved()
}

// The invoice's project is a fixed filter for its lines: entries of other projects go when
// it is set (after asking), and "Positionen holen" only offers its entries. Left empty, the
// invoice takes the project of its lines if they all share one (done by the server).
watch(projectId, (value, previous) => {
  if (loadingDraft) return
  const others = billed.value.filter((entry) => value && entry.project !== value)
  if (!others.length) return
  // Cancelling (or closing the dialog) keeps the lines and the previous project. The cancel
  // button doesn't run onHide, closing doesn't run reject: both revert.
  let decided = false
  const revert = () => {
    if (decided) return
    decided = true
    projectId.value = previous
  }
  confirm.require({
    header: t('invoices.otherProjectsTitle'),
    message: t('invoices.otherProjectsMessage', others.length),
    icon: 'iconify lucide--triangle-alert',
    rejectLabel: t('common.cancel'),
    rejectProps: { text: true },
    acceptLabel: t('invoices.removeOtherProjects'),
    accept: () => {
      decided = true
      billed.value = billed.value.filter((entry) => entry.project === value)
    },
    reject: revert,
    onHide: revert,
  })
})

// Regrouping builds the lines anew; texts the user changed would be lost, so ask first.
function changeGroupBy(value: string) {
  if (value === groupBy.value) return
  if (!Object.keys(texts.value).length) {
    groupBy.value = value
    return
  }
  confirm.require({
    header: t('invoices.regroupTitle'),
    message: t('invoices.regroupMessage'),
    icon: 'iconify lucide--triangle-alert',
    rejectLabel: t('common.cancel'),
    rejectProps: { text: true },
    acceptLabel: t('invoices.regroup'),
    accept: () => {
      texts.value = {}
      groupBy.value = value
    },
    reject: () => groupByKey.value++,
    onHide: () => groupByKey.value++,
  })
}

// --- "Positionen holen": pick which open entries the invoice bills. ---
const fetchModal = ref<InstanceType<typeof AppModal>>()
const fetchProjectId = ref<string | null>(null)
const dateFrom = ref<string | null>(null)
const dateTo = ref<string | null>(null)
const openEntries = ref<TimeEntry[]>([])
const picked = ref(new Set<string>())
// Entries already on the invoice are not offered again; ones removed from the draft are.
function matchesFilter(entry: TimeEntry) {
  const day = isoDate(new Date(entry.start_datetime))
  return (
    (!fetchProjectId.value || entry.project === fetchProjectId.value) &&
    (!dateFrom.value || day >= dateFrom.value) &&
    (!dateTo.value || day <= dateTo.value)
  )
}
const offeredEntries = computed(() =>
  [...openEntries.value, ...draftEntries.value.filter(matchesFilter)]
    .filter((entry) => !billedIds.value.includes(entry.id))
    .sort((a, b) => a.start_datetime.localeCompare(b.start_datetime)),
)
const pickedMinutes = computed(() =>
  offeredEntries.value
    .filter((entry) => picked.value.has(entry.id))
    .reduce((sum, entry) => sum + entry.duration_minutes, 0),
)
const allPicked = computed(
  () =>
    offeredEntries.value.length > 0 &&
    offeredEntries.value.every((entry) => picked.value.has(entry.id)),
)
// The checkbox toggles the entry itself; its click must not reach the row as well.
const stopRowClick = { root: { onClick: (event: Event) => event.stopPropagation() } }

function togglePick(entry: TimeEntry) {
  const next = new Set(picked.value)
  if (!next.delete(entry.id)) next.add(entry.id)
  picked.value = next
}

function togglePickAll() {
  picked.value = allPicked.value
    ? new Set()
    : new Set(offeredEntries.value.map((entry) => entry.id))
}

let entriesRequest = 0
async function loadOpenEntries() {
  const request = ++entriesRequest
  if (!customerId.value) return
  const params = new URLSearchParams({
    customer: customerId.value,
    billable: 'true',
    invoice__isnull: 'true',
    contract__isnull: 'true',
    end_datetime__isnull: 'false',
    ordering: 'start_datetime',
  })
  if (fetchProjectId.value) params.set('project', fetchProjectId.value)
  if (dateFrom.value) params.set('start_datetime__date__gte', dateFrom.value)
  if (dateTo.value) params.set('start_datetime__date__lte', dateTo.value)
  const page = await timeTrackingApi.list(`${params.toString()}&page_size=500`)
  if (request !== entriesRequest) return
  openEntries.value = page.results
  // Newly offered entries start ticked.
  picked.value = new Set(offeredEntries.value.map((entry) => entry.id))
}

function loadOpenTrips() {
  if (!customerId.value) return
  void trips.load({
    customer: customerId.value,
    project: fetchProjectId.value,
    dateFrom: dateFrom.value,
    dateTo: dateTo.value,
    invoice: invoiceId,
  })
}

watch([fetchProjectId, dateFrom, dateTo], () => {
  void loadOpenEntries()
  loadOpenTrips()
})

function openFetch() {
  fetchProjectId.value = projectId.value
  void loadOpenEntries()
  loadOpenTrips()
  fetchModal.value?.open()
}

function takeOver() {
  billed.value = [
    ...billed.value,
    ...offeredEntries.value.filter((entry) => picked.value.has(entry.id)),
  ]
  trips.takeOver()
  fetchModal.value?.close()
}

// --- The lines: grouped by the server from the billed entries, plus own lines. ---
const previewRequestBody = computed<ConsolidateRequest | null>(() => {
  if (!customerId.value) return null
  return {
    customer_id: customerId.value,
    // Always a list: omitted would mean every open entry.
    entry_ids: billedIds.value,
    travel: trips.specs(texts.value),
    group_by: groupBy.value,
    vat_rate: vatRate.value,
    extra_lines: ownLines.value
      .filter((line) => line.description.trim())
      .map(({ description, quantity, unit, unit_price }) => ({
        description,
        quantity,
        unit,
        unit_price,
      })),
  }
})

// Server-side dry run: the grouped lines (with their entries and keys) and the totals; e.g.
// a missing hourly rate shows up before anything is created.
const preview = ref<ConsolidatePreview | null>(null)
const previewError = ref('')
let previewTimer: ReturnType<typeof setTimeout> | undefined
let previewRequest = 0
watch(
  previewRequestBody,
  (value) => {
    clearTimeout(previewTimer)
    if (
      !value ||
      (!value.entry_ids?.length && !value.extra_lines?.length && !value.travel?.length)
    ) {
      preview.value = null
      previewError.value = ''
      return
    }
    previewTimer = setTimeout(() => void loadPreview(value), 200)
  },
  { deep: true },
)

onBeforeUnmount(() => clearTimeout(previewTimer))

async function loadPreview(value: ConsolidateRequest) {
  const request = ++previewRequest
  try {
    const result = invoiceId
      ? await invoicesApi.draftPreview(invoiceId, value)
      : await invoicesApi.consolidatePreview(value)
    if (request !== previewRequest) return
    preview.value = result
    previewError.value = ''
  } catch (e) {
    if (request !== previewRequest) return
    preview.value = null
    previewError.value = e instanceof ApiError && e.data ? errorText(e.data) : t('common.error')
  }
}

// Lines from entries and trips: generated, their text editable.
const entryLines = computed(() =>
  (preview.value?.lines ?? []).filter(
    (line) => line.key && (line.entry_ids.length || line.visit_id),
  ),
)

function lineText(key: string, generated: string) {
  return texts.value[key] ?? generated
}

function setLineText(key: string, value: string | undefined, generated: string) {
  const next = { ...texts.value }
  if (value === undefined || value === generated) delete next[key]
  else next[key] = value
  texts.value = next
}

function removeEntryLine(key: string, entryIds: string[], visitId?: string) {
  billed.value = billed.value.filter((entry) => !entryIds.includes(entry.id))
  if (visitId) trips.remove(visitId)
  setLineText(key, undefined, '')
}

// Both kinds of lines in one table: generated ones first, then the user's own.
type PositionRow =
  | { id: string; entry: (typeof entryLines.value)[number]; own?: undefined }
  | { id: string; entry?: undefined; own: OwnLine }
const positionRows = computed<PositionRow[]>(() => [
  ...entryLines.value.map((entry) => ({ id: entry.key!, entry })),
  ...ownLines.value.map((own) => ({ id: own.id, own })),
])

function removeLine(row: PositionRow) {
  if (row.entry) removeEntryLine(row.entry.key!, row.entry.entry_ids, row.entry.visit_id)
  else ownLines.value = ownLines.value.filter((line) => line.id !== row.own.id)
}

function ownTotal(line: OwnLine) {
  return Math.round(line.quantity * line.unit_price * 100) / 100
}

const { markSaved } = useUnsavedChanges(
  computed(() => ({
    number: numberInput.value,
    customer: customerId.value,
    project: projectId.value,
    contacts: contactIds.value,
    issueDate: issueDate.value,
    dueDate: ownDueDate.value,
    bankAccount: bankAccountId.value,
    eInvoice: eInvoiceFormat.value,
    vatRate: vatRate.value,
    template: templateId.value,
    notes: notes.value,
    groupBy: groupBy.value,
    billed: billedIds.value,
    trips: trips.billedIds.value,
    texts: texts.value,
    own: ownLines.value,
  })),
  () => !created.value && !loadingDraft,
)

if (invoiceId) void loadDraft(invoiceId)
// The defaults filled in after loading (VAT rate, bank account, contacts) are no changes.
else void Promise.all([companyLoaded, loadCustomer(customerId.value)]).then(markSaved)

// Created as shown: these entries under these texts, and the own lines.
const createBody = computed<ConsolidateRequest | null>(() => {
  const body = previewRequestBody.value
  if (!body) return null
  return {
    ...body,
    project_id: projectId.value,
    contact_ids: contactIds.value,
    bank_account_id:
      bankAccountId.value !== defaultBankAccountId.value ? bankAccountId.value : null,
    e_invoice_format: eInvoiceFormat.value,
    ...(issueDate.value ? { issue_date: issueDate.value } : {}),
    ...(dueDate.value ? { due_date: dueDate.value } : {}),
    template_id: templateId.value,
    notes: notes.value,
    ...(invoiceId && numberInput.value !== undefined ? { number: numberInput.value } : {}),
    entry_lines: entryLines.value
      .filter((line) => line.entry_ids.length)
      .map((line) => ({
        entry_ids: line.entry_ids,
        description: lineText(line.key!, line.description),
      })),
  }
})
const canCreate = computed(
  () =>
    !!createBody.value &&
    !!preview.value &&
    !previewError.value &&
    (!!createBody.value.entry_lines?.length ||
      !!createBody.value.travel?.length ||
      !!createBody.value.extra_lines?.length),
)

async function create() {
  if (!createBody.value || !canCreate.value) return
  creating.value = true
  try {
    const inv = invoiceId
      ? await invoicesApi.saveDraft(invoiceId, createBody.value)
      : await invoicesApi.consolidate(createBody.value)
    created.value = true
    void router.push(`/invoices/${inv.id}`)
  } catch (e) {
    notify.error(e)
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div>
    <AppPageHeader
      :back-to="backTo"
      :back-label="invoiceId ? invoiceNumber : t('nav.invoices')"
      :title="invoiceId ? t('invoices.editTitle', { number: invoiceNumber }) : t('invoices.new')"
    >
      <template #actions>
        <Button :label="t('common.cancel')" text @click="router.push(backTo)" />
        <Button
          :label="invoiceId ? t('common.save') : t('invoices.createDraft')"
          icon="iconify lucide--check"
          :loading="creating"
          :disabled="!canCreate"
          @click="create"
        />
      </template>
    </AppPageHeader>

    <div class="flex flex-col gap-6">
      <section class="app-card p-4">
        <h2 class="font-semibold mb-4">{{ t('invoices.general') }}</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <AppFormField :label="t('projects.customer')" required
            ><CustomerSelect v-model="customerId" :disabled="!!invoiceId"
          /></AppFormField>
          <AppFormField :label="t('projects.project')"
            ><ProjectSelect v-model="projectId" :customer-id="customerId" customer-only
          /></AppFormField>
          <AppFormField :label="t('invoices.contacts')">
            <MultiSelect
              v-model="contactIds"
              :show-toggle-all="false"
              :options="availableContacts"
              option-label="name"
              option-value="id"
              display="chip"
              class="w-full"
            />
          </AppFormField>
          <NumberField v-if="invoiceId" v-model="numberInput" />
          <AppFormField :label="t('invoices.issueDate')" required
            ><AppDateInput v-model="issueDate"
          /></AppFormField>
          <AppFormField :label="t('invoices.dueDate')" required
            ><AppDateInput v-model="dueDate"
          /></AppFormField>
        </div>
        <button
          type="button"
          class="mt-3 text-sm text-surface-500 hover:text-primary inline-flex items-center gap-1"
          :aria-expanded="showMore"
          @click="showMore = !showMore"
        >
          <i
            :class="showMore ? 'iconify lucide--chevron-up' : 'iconify lucide--chevron-down'"
            class="text-xs"
          />
          {{ showMore ? t('invoices.showLess') : t('invoices.showMore') }}
        </button>
        <div v-if="showMore" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mt-4">
          <AppFormField :label="t('settings.bankAccount')">
            <Select
              v-model="bankAccountId"
              :options="bankAccounts"
              option-label="name"
              option-value="id"
              show-clear
              :placeholder="t('invoices.inheritedBankAccount')"
              class="w-full"
            />
          </AppFormField>
          <AppFormField :label="t('invoices.eInvoice')">
            <AppEnumSelect
              v-model="eInvoiceFormat"
              :options="formats"
              label-prefix="invoices.eInvoiceFormats"
              class="w-full"
            />
          </AppFormField>
          <AppFormField :label="t('invoices.vatRate')">
            <InputNumber
              v-model="vatRate"
              :min="0"
              :max="100"
              :max-fraction-digits="2"
              suffix=" %"
              fluid
              :pt="{ pcInputText: { root: { 'aria-label': t('invoices.vatRate') } } }"
            />
          </AppFormField>
          <AppFormField :label="t('invoices.template')">
            <Select
              v-model="templateId"
              :options="templates"
              option-label="name"
              option-value="id"
              show-clear
              :placeholder="t('invoices.assignedTemplate')"
              class="w-full"
            />
          </AppFormField>
          <AppFormField :label="t('common.notes')" class="col-span-full">
            <Textarea v-model="notes" rows="2" auto-resize fluid />
          </AppFormField>
        </div>
        <Message
          v-if="!bankAccounts.some((account) => account.iban)"
          severity="warn"
          size="small"
          class="mt-4"
        >
          {{ t('invoices.noIbanHint') }}
          <router-link to="/settings?tab=bankAccounts" class="underline font-medium">{{
            t('invoices.noIbanLink')
          }}</router-link>
        </Message>
      </section>

      <section class="app-card">
        <div class="flex flex-wrap items-center gap-3 p-4 pb-3">
          <h2 class="font-semibold">{{ t('invoices.positions') }}</h2>
          <div class="flex items-center gap-2 text-sm">
            <span class="text-surface-500">{{ t('invoices.groupBy') }}</span>
            <AppSegmented
              :key="groupByKey"
              :model-value="groupBy"
              :options="groupByOptions"
              size="small"
              @update:model-value="changeGroupBy"
            />
          </div>
          <div class="flex gap-2 ms-auto">
            <Button
              :label="t('invoices.fetchPositions')"
              icon="iconify lucide--download"
              size="small"
              :disabled="!customerId"
              @click="openFetch"
            />
            <Button
              :label="t('invoices.addLine')"
              icon="iconify lucide--plus"
              size="small"
              outlined
              :disabled="!customerId"
              @click="addOwnLine"
            />
          </div>
        </div>
        <Message v-if="previewError" severity="warn" class="mx-4 mb-3">{{ previewError }}</Message>

        <AppDataTable
          :rows="positionRows"
          :state-key="tableStateKeys.invoiceLines"
          :page-size="1000"
          :empty-message="customerId ? t('invoices.noLinesYet') : t('invoices.pickCustomer')"
          class="px-4"
        >
          <Column
            column-key="position"
            :header="t('invoices.position')"
            :reorderable-column="false"
            header-style="width: 3.5rem"
            ><template #body="{ index }"
              ><span class="text-surface-500 tabular-nums">{{ index + 1 }}</span></template
            ></Column
          >
          <Column
            column-key="description"
            :header="t('time.description')"
            class="app-text"
            header-style="min-width: 11rem"
          >
            <template #body="{ data }">
              <template v-if="data.entry">
                <Textarea
                  :model-value="lineText(data.entry.key, data.entry.description)"
                  rows="1"
                  auto-resize
                  fluid
                  :aria-label="t('time.description')"
                  @update:model-value="
                    (value: string | undefined) =>
                      setLineText(
                        data.entry.key,
                        value,
                        data.entry.default_description ?? data.entry.description,
                      )
                  "
                />
                <div class="flex gap-2 text-xs text-surface-500 mt-0.5">
                  <span v-if="data.entry.entry_ids.length">{{
                    t('invoices.entriesOnLine', data.entry.entry_ids.length)
                  }}</span>
                  <button
                    v-if="texts[data.entry.key] !== undefined"
                    type="button"
                    class="underline hover:text-primary"
                    @click="setLineText(data.entry.key, undefined, '')"
                  >
                    {{ t('invoices.resetText') }}
                  </button>
                </div>
              </template>
              <Textarea
                v-else
                v-model="data.own.description"
                rows="1"
                auto-resize
                fluid
                :placeholder="t('invoices.ownLinePlaceholder')"
                :aria-label="t('time.description')"
              />
            </template>
          </Column>
          <Column
            column-key="project"
            :header="t('projects.project')"
            class="app-optional"
            header-style="width: 10rem"
          >
            <template #body="{ data }">{{ data.entry?.project_name ?? '—' }}</template>
          </Column>
          <Column
            column-key="servicePeriod"
            :header="t('invoices.servicePeriod')"
            class="app-optional"
            header-style="width: 11rem"
          >
            <template #body="{ data }">
              <span v-if="data.entry?.date_from" class="tabular-nums whitespace-nowrap"
                ><AppDateTimeDisplay :value="data.entry.date_from" /><template
                  v-if="data.entry.date_to && data.entry.date_to !== data.entry.date_from"
                  >–<AppDateTimeDisplay :value="data.entry.date_to" /></template
              ></span>
              <template v-else>—</template>
            </template>
          </Column>
          <Column
            column-key="quantity"
            :header="t('invoices.quantity')"
            class="app-num"
            header-style="width: 5rem"
          >
            <template #body="{ data }">
              <AppNumberDisplay v-if="data.entry" :value="data.entry.quantity" />
              <InputNumber
                v-else
                v-model="data.own.quantity"
                :min="0"
                :max-fraction-digits="2"
                fluid
                input-class="text-right"
                :pt="{ pcInputText: { root: { 'aria-label': t('invoices.quantity') } } }"
              />
            </template>
          </Column>
          <Column column-key="unit" :header="t('invoices.unit')" header-style="width: 6.5rem">
            <template #body="{ data }">
              <template v-if="data.entry">{{ t(`invoices.units.${data.entry.unit}`) }}</template>
              <AppEnumSelect
                v-else
                v-model="data.own.unit"
                :options="units"
                label-prefix="invoices.units"
                class="w-full"
              />
            </template>
          </Column>
          <Column
            column-key="unitPrice"
            :header="t('invoices.unitPrice')"
            class="app-num"
            header-style="width: 7rem"
          >
            <template #body="{ data }">
              <AppMoneyDisplay v-if="data.entry" :amount="data.entry.unit_price" />
              <InputNumber
                v-else
                v-model="data.own.unit_price"
                mode="currency"
                currency="EUR"
                fluid
                input-class="text-right"
                :pt="{ pcInputText: { root: { 'aria-label': t('invoices.unitPrice') } } }"
              />
            </template>
          </Column>
          <Column
            column-key="total"
            :header="t('common.total')"
            class="app-num"
            header-style="width: 7rem"
          >
            <template #body="{ data }">
              <AppMoneyDisplay
                :amount="data.entry ? data.entry.total : ownTotal(data.own)"
                class="font-medium"
              />
            </template>
          </Column>
          <Column column-key="actions" :reorderable-column="false">
            <template #body="{ data }">
              <AppIconButton
                icon="iconify lucide--trash-2"
                severity="danger"
                :label="t('common.delete')"
                @click="removeLine(data)"
              />
            </template>
          </Column>
        </AppDataTable>

        <div class="flex justify-end p-4">
          <div class="w-72 flex flex-col gap-1 text-sm tabular-nums">
            <div class="flex justify-between">
              <span class="text-surface-500">{{ t('invoices.subtotal') }}</span>
              <AppMoneyDisplay :amount="preview?.subtotal ?? 0" />
            </div>
            <div class="flex justify-between text-surface-500">
              <span
                >{{ t('invoices.vat') }} (<AppNumberDisplay
                  :value="preview?.vat_rate ?? 0"
                  :maximum-fraction-digits="2"
                />
                %)</span
              ><AppMoneyDisplay :amount="preview?.vat_amount ?? 0" />
            </div>
            <div
              class="flex justify-between font-semibold text-base pt-1 border-t border-surface-200 dark:border-surface-800"
            >
              <span>{{ t('common.total') }}</span><AppMoneyDisplay :amount="preview?.total ?? 0" />
            </div>
          </div>
        </div>
      </section>
    </div>

    <AppModal
      ref="fetchModal"
      :title="t('invoices.fetchPositions')"
      size="xl"
      :confirm-label="t('invoices.takeOver')"
      @confirm="takeOver"
    >
      <div class="flex flex-col gap-4">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <AppFormField :label="t('projects.project')"
            ><ProjectSelect
              v-model="fetchProjectId"
              :customer-id="customerId"
              customer-only
              :disabled="!!projectId"
          /></AppFormField>
          <AppFormField :label="t('invoices.dateFrom')"
            ><AppDateInput v-model="dateFrom"
          /></AppFormField>
          <AppFormField :label="t('invoices.dateTo')"
            ><AppDateInput v-model="dateTo"
          /></AppFormField>
        </div>
        <span class="text-sm text-surface-500">
          {{
            t('invoices.selectedEntries', {
              selected: picked.size,
              total: offeredEntries.length,
            })
          }}
          · <AppDurationDisplay :minutes="pickedMinutes" />
        </span>
        <p v-if="!offeredEntries.length" class="text-sm text-surface-500">
          {{ t('invoices.noOpenEntries') }}
        </p>
        <AppDataTable
          v-else
          :rows="offeredEntries"
          :state-key="tableStateKeys.invoiceSourceEntries"
          @row-click="togglePick"
        >
          <Column header-style="width: 3rem" :reorderable-column="false">
            <template #header
              ><Checkbox
                :model-value="allPicked"
                :indeterminate="picked.size > 0 && !allPicked"
                binary
                :aria-label="t('table.selectPage')"
                @update:model-value="togglePickAll"
            /></template>
            <template #body="{ data }"
              ><Checkbox
                :model-value="picked.has(data.id)"
                binary
                :pt="stopRowClick"
                @update:model-value="togglePick(data)"
            /></template>
          </Column>
          <Column field="start_datetime" :header="t('common.date')"
            ><template #body="{ data }"
              ><AppDateTimeDisplay :value="data.start_datetime" type="datetime" /></template
          ></Column>
          <Column class="app-text" field="project_name" :header="t('projects.project')" />
          <Column class="app-text" field="description" :header="t('time.description')" />
          <Column class="app-num" field="duration_minutes" :header="t('time.duration')">
            <template #body="{ data }"
              ><AppDurationDisplay :minutes="data.duration_minutes"
            /></template>
          </Column>
        </AppDataTable>
        <template v-if="trips.offered.value.length">
          <h3 class="font-semibold mt-2">{{ t('travel.trips') }}</h3>
          <AppDataTable
            :rows="trips.offered.value"
            :state-key="tableStateKeys.invoiceSourceTrips"
            @row-click="trips.toggle"
          >
            <Column header-style="width: 3rem" :reorderable-column="false">
              <template #body="{ data }"
                ><Checkbox
                  :model-value="trips.picked.value.has(data.id)"
                  binary
                  :pt="stopRowClick"
                  @update:model-value="trips.toggle(data)"
              /></template>
            </Column>
            <Column field="date" :header="t('common.date')"
              ><template #body="{ data }"><AppDateTimeDisplay :value="data.date" /></template
            ></Column>
            <Column field="number" :header="t('common.numberShort')" />
            <Column class="app-text" field="project_name" :header="t('projects.project')" />
            <Column class="app-text" field="location" :header="t('visits.location')" />
          </AppDataTable>
        </template>
      </div>
    </AppModal>
  </div>
</template>
