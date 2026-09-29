<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Select from 'primevue/select'
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
  bankAccountsApi, contactsApi, invoicesApi, timeEntriesApi,
  type BankAccount, type Contact, type TimeEntry,
} from '../../api'
import { useNotify } from '../../composables/useNotify'

const { t } = useI18n()
const router = useRouter()
const notify = useNotify()

const step = ref(0)
const customerId = ref<string | null>(null)
const projectId = ref<string | null>(null)
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
  { label: t('invoices.title') },
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
})

watch([customerId, projectId, dateFrom, dateTo], async () => {
  if (!customerId.value) {
    entries.value = []
    return
  }
  const params = new URLSearchParams({
    customer: String(customerId.value),
    billable: 'true',
    invoice__isnull: 'true',
    contract__isnull: 'true',
    page_size: '500',
  })
  if (projectId.value) params.set('project', String(projectId.value))
  if (dateFrom.value) params.set('date__gte', dateFrom.value)
  if (dateTo.value) params.set('date__lte', dateTo.value)
  entries.value = (await timeEntriesApi.list(params.toString())).results
})

const totalHours = computed(() => entries.value.reduce((s, e) => s + e.duration_minutes, 0) / 60)

async function create() {
  if (!customerId.value) return
  creating.value = true
  try {
    const inv = await invoicesApi.consolidate({
      customer_id: customerId.value,
      project_id: projectId.value,
      contact_ids: contactIds.value,
      bank_account_id: bankAccountId.value,
      date_from: dateFrom.value,
      date_to: dateTo.value,
      group_by: groupBy.value,
      e_invoice_format: eInvoiceFormat.value,
      extra_lines: manualLines.value,
    })
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
    <AppPageHeader :title="t('invoices.new')" />
    <Steps :model="steps" :active-step="step" class="mb-6" :readonly="false" @update:active-step="(s: number) => step = s" />

    <div v-if="step === 0" class="flex flex-col gap-4 max-w-lg">
      <AppFormField :label="t('projects.customer')" required><CustomerSelect v-model="customerId" /></AppFormField>
      <AppFormField :label="t('nav.projects')"><ProjectSelect v-model="projectId" :customer-id="customerId" /></AppFormField>
      <AppFormField :label="t('invoices.contacts')">
        <MultiSelect v-model="contactIds" :options="availableContacts" option-label="name" option-value="id" display="chip" class="w-full" />
      </AppFormField>
      <div class="grid grid-cols-2 gap-3">
        <AppFormField :label="t('common.date') + ' ≥'"><AppDateInput v-model="dateFrom" /></AppFormField>
        <AppFormField :label="t('common.date') + ' ≤'"><AppDateInput v-model="dateTo" /></AppFormField>
      </div>
      <Button :label="t('common.confirm')" class="self-start" :disabled="!customerId" @click="step = 1" />
    </div>

    <div v-else-if="step === 1">
      <p class="text-sm text-surface-500 mb-3"><AppNumberDisplay :value="entries.length" :maximum-fraction-digits="0" /> · <AppNumberDisplay :value="totalHours" :minimum-fraction-digits="2" />h</p>
      <AppDataTable :rows="entries">
        <Column :header="t('common.date')"><template #body="{ data }"><AppDateTimeDisplay :value="data.date" /></template></Column>
        <Column field="project_name" :header="t('nav.projects')" />
        <Column field="description" :header="t('time.description')" />
        <Column :header="t('time.duration')">
          <template #body="{ data }"><AppDurationDisplay :minutes="data.duration_minutes" /></template>
        </Column>
      </AppDataTable>

      <h3 class="font-medium mt-6 mb-2">{{ t('invoices.manualLines') }}</h3>
      <AppDataTable v-if="manualLines.length" :rows="manualLines" class="mb-3">
        <Column field="description" :header="t('time.description')" />
        <Column field="quantity" :header="t('invoices.quantity')" />
        <Column :header="t('invoices.unitPrice')">
          <template #body="{ data }"><AppMoneyDisplay :amount="data.unit_price" /></template>
        </Column>
        <Column :header="t('common.total')">
          <template #body="{ data }"><AppMoneyDisplay :amount="data.quantity * data.unit_price" /></template>
        </Column>
        <Column :header="t('common.actions')">
          <template #body="{ index }"><AppIconButton icon="pi pi-trash" severity="danger" @click.stop="manualLines.splice(index, 1)" /></template>
        </Column>
      </AppDataTable>
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-[minmax(240px,1fr)_120px_140px_140px] gap-2 items-end">
        <AppFormField :label="t('time.description')" class="min-w-0"><InputText v-model="lineForm.description" class="w-full min-w-0" /></AppFormField>
        <AppFormField :label="t('invoices.quantity')" class="min-w-0"><InputNumber v-model="lineForm.quantity" :min="0" :min-fraction-digits="0" :max-fraction-digits="2" class="w-full min-w-0" fluid /></AppFormField>
        <AppFormField :label="t('invoices.unit')" class="min-w-0">
          <Select v-model="lineForm.unit" :options="units" class="w-full min-w-0">
            <template #option="{ option }">{{ t(`invoices.units.${option}`) }}</template>
            <template #value="{ value }">{{ t(`invoices.units.${value}`) }}</template>
          </Select>
        </AppFormField>
        <AppFormField :label="t('invoices.unitPrice')" class="min-w-0"><InputNumber v-model="lineForm.unit_price" mode="currency" currency="EUR" class="w-full min-w-0" fluid /></AppFormField>
      </div>
      <Button :label="t('invoices.addLine')" icon="pi pi-plus" size="small" class="mt-2" @click="addLine" />

      <div class="flex gap-2 mt-4">
        <Button :label="t('common.back')" text @click="step = 0" />
        <Button :label="t('common.confirm')" @click="step = 2" />
      </div>
    </div>

    <div v-else class="flex flex-col gap-4 max-w-lg">
      <AppFormField :label="t('invoices.groupBy')">
        <Select v-model="groupBy" :options="groupBys" class="w-full">
          <template #option="{ option }">{{ t(`invoices.groupBys.${option}`) }}</template>
          <template #value="{ value }">{{ t(`invoices.groupBys.${value}`) }}</template>
        </Select>
      </AppFormField>
      <AppFormField :label="t('settings.bankAccount')">
        <Select v-model="bankAccountId" :options="bankAccounts" option-label="name" option-value="id" show-clear :placeholder="t('invoices.inheritedBankAccount')" class="w-full" />
      </AppFormField>
      <AppFormField :label="t('invoices.eInvoice')">
        <Select v-model="eInvoiceFormat" :options="formats" class="w-full">
          <template #option="{ option }">{{ t(`invoices.eInvoiceFormats.${option}`) }}</template>
          <template #value="{ value }">{{ t(`invoices.eInvoiceFormats.${value}`) }}</template>
        </Select>
      </AppFormField>
      <div class="flex gap-2">
        <Button :label="t('common.back')" text @click="step = 1" />
        <Button :label="t('common.create')" icon="pi pi-check" :loading="creating" :disabled="!entries.length && !manualLines.length" @click="create" />
      </div>
    </div>
  </div>
</template>
