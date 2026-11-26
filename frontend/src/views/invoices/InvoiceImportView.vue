<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppDateInput from '../../components/ui/AppDateInput.vue'
import AppDateTimeDisplay from '../../components/ui/AppDateTimeDisplay.vue'
import AppDurationDisplay from '../../components/ui/AppDurationDisplay.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppMoneyDisplay from '../../components/ui/AppMoneyDisplay.vue'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import CustomerSelect from '../../components/CustomerSelect.vue'
import ProjectSelect from '../../components/ProjectSelect.vue'
import { invoicesApi, settingsApi, timeTrackingApi, type TimeEntry } from '../../api'
import { isoDate } from '../../dateTimeInput'
import { useNotify } from '../../composables/useNotify'
import { useUnsavedChanges } from '../../composables/useUnsavedChanges'
import { tableStateKeys } from '../../tableStateKeys'

// An invoice written elsewhere: its number, dates and amount as on the original, the PDF
// (and XML) it went out as, and the open time entries it billed. Recorded as issued.
const { t } = useI18n()
const router = useRouter()
const notify = useNotify()

const form = ref({
  customer: null as string | null,
  project: null as string | null,
  number: '',
  issue_date: isoDate(),
  due_date: null as string | null,
  net: 0,
  vat_rate: 19,
})
const pdf = ref<File | null>(null)
const xml = ref<File | null>(null)
const pdfInput = ref<HTMLInputElement>()
const xmlInput = ref<HTMLInputElement>()
const saving = ref(false)
const saved = ref(false)

// With VAT the net amount and rate, without (small business) just the amount.
const vatEnabled = ref(true)
void settingsApi.get().then((company) => {
  vatEnabled.value = company.vat_enabled !== false
  form.value.vat_rate = Number(company.default_vat_rate ?? 19)
})
const total = computed(() =>
  vatEnabled.value
    ? Math.round(form.value.net * (100 + form.value.vat_rate)) / 100
    : form.value.net,
)

const entries = ref<TimeEntry[]>([])
const picked = ref(new Set<string>())
const pickedMinutes = computed(() =>
  entries.value
    .filter((entry) => picked.value.has(entry.id))
    .reduce((sum, entry) => sum + entry.duration_minutes, 0),
)
// The checkbox toggles the entry itself; its click must not reach the row as well.
const stopRowClick = { root: { onClick: (event: Event) => event.stopPropagation() } }

function togglePick(entry: TimeEntry) {
  const next = new Set(picked.value)
  if (!next.delete(entry.id)) next.add(entry.id)
  picked.value = next
}

// The customer's (or project's) open entries; none is ticked until chosen.
watch(
  () => [form.value.customer, form.value.project],
  async ([customer, project]) => {
    picked.value = new Set()
    if (!customer) {
      entries.value = []
      return
    }
    const params = new URLSearchParams({
      customer,
      billable: 'true',
      invoice__isnull: 'true',
      contract__isnull: 'true',
      end_datetime__isnull: 'false',
      ordering: 'start_datetime',
      page_size: '500',
    })
    if (project) params.set('project', project)
    entries.value = (await timeTrackingApi.list(params.toString())).results
  },
)

const fileOf = (event: Event) => (event.target as HTMLInputElement).files?.[0] ?? null

const canSave = computed(
  () =>
    !!form.value.customer && !!form.value.number.trim() && !!form.value.issue_date && !!pdf.value,
)

useUnsavedChanges(
  computed(() => ({ ...form.value, pdf: pdf.value?.name, picked: [...picked.value] })),
  () => !saved.value,
)

async function save() {
  if (!canSave.value || !pdf.value) return
  const data = new FormData()
  const f = form.value
  data.append('customer_id', f.customer!)
  if (f.project) data.append('project_id', f.project)
  data.append('number', f.number.trim())
  data.append('issue_date', f.issue_date)
  if (f.due_date) data.append('due_date', f.due_date)
  data.append('net', f.net.toFixed(2))
  if (vatEnabled.value) data.append('vat_rate', String(f.vat_rate))
  data.append('pdf', pdf.value)
  if (xml.value) data.append('xml', xml.value)
  for (const id of picked.value) data.append('entry_ids', id)
  saving.value = true
  try {
    const invoice = await invoicesApi.importExternal(data)
    saved.value = true
    void router.push(`/invoices/${invoice.id}`)
  } catch (e) {
    notify.error(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <AppPageHeader
      back-to="/invoices"
      :back-label="t('nav.invoices')"
      :title="t('invoices.importExternal')"
    >
      <template #actions>
        <Button :label="t('common.cancel')" text @click="router.push('/invoices')" />
        <Button
          :label="t('invoices.importSave')"
          icon="pi pi-check"
          :loading="saving"
          :disabled="!canSave"
          @click="save"
        />
      </template>
    </AppPageHeader>

    <div class="flex flex-col gap-6">
      <section class="app-card p-4">
        <p class="text-sm text-surface-500 mb-4">{{ t('invoices.importHint') }}</p>
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <AppFormField field="customer_id" :label="t('projects.customer')" required
            ><CustomerSelect v-model="form.customer"
          /></AppFormField>
          <AppFormField field="project_id" :label="t('projects.project')"
            ><ProjectSelect v-model="form.project" :customer-id="form.customer" customer-only
          /></AppFormField>
          <AppFormField field="number" :label="t('invoices.number')" required
            ><InputText v-model="form.number" class="w-full"
          /></AppFormField>
          <AppFormField field="issue_date" :label="t('invoices.issueDate')" required
            ><AppDateInput v-model="form.issue_date"
          /></AppFormField>
          <AppFormField field="due_date" :label="t('invoices.dueDate')"
            ><AppDateInput v-model="form.due_date" :placeholder="t('invoices.dueByTerms')"
          /></AppFormField>
          <template v-if="vatEnabled">
            <AppFormField field="net" :label="t('invoices.netAmount')" required>
              <InputNumber
                v-model="form.net"
                mode="currency"
                currency="EUR"
                :min="0"
                fluid
                :pt="{ pcInputText: { root: { 'aria-label': t('invoices.netAmount') } } }"
              />
            </AppFormField>
            <AppFormField field="vat_rate" :label="t('invoices.vatRate')">
              <InputNumber
                v-model="form.vat_rate"
                :min="0"
                :max="100"
                :max-fraction-digits="2"
                suffix=" %"
                fluid
                :pt="{ pcInputText: { root: { 'aria-label': t('invoices.vatRate') } } }"
              />
            </AppFormField>
            <div class="flex flex-col gap-1 justify-end text-sm">
              <span class="text-surface-500">{{ t('common.total') }}</span>
              <span class="text-lg font-semibold"><AppMoneyDisplay :amount="total" /></span>
            </div>
          </template>
          <AppFormField v-else field="net" :label="t('common.amount')" required>
            <InputNumber
              v-model="form.net"
              mode="currency"
              currency="EUR"
              :min="0"
              fluid
              :pt="{ pcInputText: { root: { 'aria-label': t('common.amount') } } }"
            />
          </AppFormField>
          <AppFormField field="pdf" :label="t('invoices.pdfFile')" required>
            <div class="flex items-center gap-2 min-w-0">
              <Button
                :label="t('common.chooseFile')"
                icon="pi pi-file-pdf"
                severity="secondary"
                outlined
                @click="pdfInput?.click()"
              />
              <span class="text-sm truncate">{{ pdf?.name ?? '' }}</span>
              <input
                ref="pdfInput"
                type="file"
                accept="application/pdf,.pdf"
                class="hidden"
                :aria-label="t('invoices.pdfFile')"
                @change="pdf = fileOf($event)"
              />
            </div>
          </AppFormField>
          <AppFormField field="xml" :label="t('invoices.xmlFile')">
            <div class="flex items-center gap-2 min-w-0">
              <Button
                :label="t('common.chooseFile')"
                icon="pi pi-code"
                severity="secondary"
                outlined
                @click="xmlInput?.click()"
              />
              <span class="text-sm truncate">{{ xml?.name ?? '' }}</span>
              <input
                ref="xmlInput"
                type="file"
                accept="application/xml,text/xml,.xml"
                class="hidden"
                :aria-label="t('invoices.xmlFile')"
                @change="xml = fileOf($event)"
              />
            </div>
          </AppFormField>
        </div>
      </section>

      <section class="app-card p-4">
        <div class="flex flex-wrap items-baseline gap-3 mb-3">
          <h2 class="font-semibold">{{ t('invoices.billedTimes') }}</h2>
          <span class="text-sm text-surface-500">
            {{ t('invoices.selectedEntries', { selected: picked.size, total: entries.length }) }}
            · <AppDurationDisplay :minutes="pickedMinutes" />
          </span>
        </div>
        <p v-if="!form.customer" class="text-sm text-surface-500">
          {{ t('invoices.importPickCustomer') }}
        </p>
        <p v-else-if="!entries.length" class="text-sm text-surface-500">
          {{ t('invoices.noOpenEntries') }}
        </p>
        <AppDataTable
          v-else
          :rows="entries"
          :state-key="tableStateKeys.invoiceImportEntries"
          @row-click="togglePick"
        >
          <Column class="w-10" :reorderable-column="false">
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
      </section>
    </div>
  </div>
</template>
