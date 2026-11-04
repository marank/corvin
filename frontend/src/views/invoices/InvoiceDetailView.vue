<script setup lang="ts">
import { computed, ref } from 'vue'
import { useLoadFailed } from '../../composables/useLoadFailed'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Message from 'primevue/message'
import MultiSelect from 'primevue/multiselect'
import Textarea from 'primevue/textarea'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import AppLoadState from '../../components/ui/AppLoadState.vue'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppStatusTag from '../../components/ui/AppStatusTag.vue'
import AppMoneyDisplay from '../../components/ui/AppMoneyDisplay.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppModal from '../../components/ui/AppModal.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppIconButton from '../../components/ui/AppIconButton.vue'
import AppDateInput from '../../components/ui/AppDateInput.vue'
import AppDateTimeDisplay from '../../components/ui/AppDateTimeDisplay.vue'
import AppNumberDisplay from '../../components/ui/AppNumberDisplay.vue'
import AttachmentList from '../../components/AttachmentList.vue'
import InvoicePreviewFrame from '../../components/InvoicePreviewFrame.vue'
import {
  bankAccountsApi, contactsApi, customersApi, invoiceItemsApi, invoicesApi, paymentsApi,
  type BankAccount, type Contact, type Invoice, type LineItem,
} from '../../api'
import { useNotify } from '../../composables/useNotify'
import { useConfirmDelete } from '../../composables/useConfirmDelete'
import { useConfirm } from 'primevue/useconfirm'
import { tableStateKeys } from '../../tableStateKeys'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const confirm = useConfirm()
const id = route.params.id as string

const invoice = ref<Invoice | null>(null)
const bankAccounts = ref<BankAccount[]>([])
const busy = ref(false)
const emailModal = ref<InstanceType<typeof AppModal>>()
const paymentModal = ref<InstanceType<typeof AppModal>>()
const emailForm = ref({ to: '', subject: '', body: '' })
const paymentForm = ref({ date: new Date().toISOString().slice(0, 10), amount: 0, note: '' })

// Bumped after every change so the preview iframe reloads.
const previewVersion = ref(0)
const previewUrl = computed(() => `${invoicesApi.previewUrl(id)}?v=${previewVersion.value}`)
const pdfUrl = computed(() => invoicesApi.pdfUrl(id))
const xmlUrl = computed(() => invoicesApi.xmlUrl(id))
const isDraft = computed(() => invoice.value?.status === 'draft')
const statusKey = computed(() => invoice.value?.partially_paid ? 'partially_paid' : invoice.value?.status ?? '')
const canReceivePayment = computed(() => ['issued', 'sent'].includes(invoice.value?.status ?? ''))

async function load() {
  const [loadedInvoice, accountPage] = await Promise.all([
    invoicesApi.get(id), bankAccountsApi.list(),
  ])
  invoice.value = loadedInvoice
  previewVersion.value++
  bankAccounts.value = accountPage.results.filter((account) => account.is_active)
}

// Prefill the recipient from the invoice contacts, falling back to the customer's address.
async function openEmail() {
  if (!invoice.value) return
  if (!emailForm.value.to) {
    emailForm.value.to = invoice.value.contacts.find((contact) => contact.email)?.email
      ?? (await customersApi.get(invoice.value.customer).catch(() => null))?.email
      ?? ''
  }
  emailModal.value?.open()
}

// Draft editing: header fields in one modal, line items one at a time.
const headerModal = ref<InstanceType<typeof AppModal>>()
const headerForm = ref<Partial<Invoice> & { contact_ids?: string[] }>({})
const customerContacts = ref<Contact[]>([])
const itemModal = ref<InstanceType<typeof AppModal>>()
const editingItem = ref<LineItem | null>(null)
const itemForm = ref<Partial<LineItem>>({})
const units = ['hours', 'flat', 'piece']
const formats = ['none', 'zugferd', 'xrechnung']

async function openHeader() {
  if (!invoice.value) return
  const { issue_date, due_date, vat_rate, notes, e_invoice_format, contacts } = invoice.value
  headerForm.value = {
    issue_date, due_date, vat_rate: Number(vat_rate), notes, e_invoice_format,
    contact_ids: contacts.map((contact) => contact.id),
  }
  customerContacts.value = (await contactsApi.list(invoice.value.customer)).results
  headerModal.value?.open()
}

async function saveHeader() {
  await act(async () => {
    await invoicesApi.patch(id, headerForm.value)
    headerModal.value?.close()
    notify.ok(t('common.saved'))
  })
}

function openItem(item?: LineItem) {
  if (!isDraft.value) return
  editingItem.value = item ?? null
  itemForm.value = item
    ? { description: item.description, quantity: Number(item.quantity), unit: item.unit, unit_price: Number(item.unit_price) }
    : { description: '', quantity: 1, unit: 'flat', unit_price: 0 }
  itemModal.value?.open()
}

async function saveItem() {
  await act(async () => {
    if (editingItem.value) await invoiceItemsApi.update(editingItem.value.id, itemForm.value)
    else await invoiceItemsApi.create({ ...itemForm.value, invoice: id })
    itemModal.value?.close()
  })
}

async function updateBankAccount(value: string | null) {
  if (!invoice.value) return
  await act(() => invoicesApi.update(id, { ...invoice.value!, bank_account_override: value }))
}
const loadFailed = useLoadFailed(load)

async function act(fn: () => Promise<unknown>) {
  busy.value = true
  try {
    await fn()
    await load()
  } catch (e) {
    notify.error(e)
  } finally {
    busy.value = false
  }
}

// Finalizing archives the PDF (GoBD) and cancelling is final too, so both ask first.
function confirmFinalize() {
  confirm.require({
    header: t('invoices.finalize'),
    message: t('invoices.finalizeConfirm'),
    icon: 'pi pi-lock',
    rejectLabel: t('common.cancel'),
    rejectProps: { text: true },
    acceptLabel: t('invoices.finalize'),
    accept: () => act(() => invoicesApi.finalize(id)),
  })
}

function confirmCancel() {
  confirm.require({
    header: t('invoices.cancelInvoice'),
    message: t('invoices.cancelConfirm'),
    icon: 'pi pi-ban',
    rejectLabel: t('common.cancel'),
    rejectProps: { text: true },
    acceptLabel: t('invoices.cancelInvoice'),
    acceptClass: 'p-button-danger',
    accept: () => act(() => invoicesApi.cancel(id)),
  })
}

async function sendEmail() {
  await act(async () => {
    await invoicesApi.sendEmail(id, emailForm.value)
    emailModal.value?.close()
    notify.ok(t('invoices.emailSent'))
  })
}

async function addPayment() {
  await act(async () => {
    await paymentsApi.create({ ...paymentForm.value, invoice: id })
    paymentModal.value?.close()
    paymentForm.value = { date: new Date().toISOString().slice(0, 10), amount: 0, note: '' }
    notify.ok(t('invoices.paymentAdded'))
  })
}
</script>

<template>
  <div v-if="invoice">
    <AppPageHeader back-to="/invoices" :back-label="t('nav.invoices')" :title="invoice.number || '—'" :subtitle="invoice.customer_name">
      <template #actions>
        <AppStatusTag :status="statusKey" :label="t(`invoices.status.${statusKey}`)" />
        <Button v-if="isDraft" :label="t('invoices.finalize')" icon="pi pi-lock" :loading="busy" @click="confirmFinalize" />
        <Button v-if="canReceivePayment" :label="t('invoices.sendEmail')" icon="pi pi-send" :loading="busy" @click="openEmail" />
        <Button v-if="canReceivePayment && Number(invoice.remaining) > 0" :label="t('invoices.addPayment')" icon="pi pi-money-bill" @click="paymentForm.amount = Number(invoice.remaining); paymentModal?.open()" />
        <Button v-if="invoice.status === 'issued'" :label="t('invoices.markSent')" text :loading="busy" @click="act(() => invoicesApi.markSent(id))" />
        <Button v-if="canReceivePayment && Number(invoice.amount_paid) === 0" :label="t('invoices.cancelInvoice')" text severity="danger" :loading="busy" @click="confirmCancel" />
        <Button v-if="isDraft" :label="t('common.delete')" text severity="danger" @click="confirmDelete(async () => { await invoicesApi.remove(id); router.push('/invoices') })" />
      </template>
    </AppPageHeader>

    <Message v-if="isDraft && !invoice.bank_account?.iban" severity="warn" class="mb-4">
      {{ t('invoices.noIbanHint') }}
      <router-link to="/settings?tab=bankAccounts" class="underline font-medium">{{ t('invoices.noIbanLink') }}</router-link>
    </Message>

    <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
      <div>
        <div class="relative border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-4 mb-4 grid grid-cols-2 gap-3 text-sm">
          <Button v-if="isDraft" :label="t('common.edit')" icon="pi pi-pencil" text size="small" class="absolute! top-2 right-2" @click="openHeader" />
          <div><span class="text-surface-500">{{ t('invoices.issueDate') }}</span><br><AppDateTimeDisplay :value="invoice.issue_date" /></div>
          <div><span class="text-surface-500">{{ t('invoices.dueDate') }}</span><br><AppDateTimeDisplay :value="invoice.due_date" /></div>
          <div><span class="text-surface-500">{{ t('invoices.eInvoice') }}</span><br>{{ t(`invoices.eInvoiceFormats.${invoice.e_invoice_format}`) }}</div>
          <div><span class="text-surface-500">{{ t('invoices.vatRate') }}</span><br><AppNumberDisplay :value="invoice.vat_rate" :maximum-fraction-digits="2" />%</div>
          <div v-if="invoice.contacts.length" class="col-span-2"><span class="text-surface-500">{{ t('invoices.contacts') }}</span><br>{{ invoice.contacts.map((contact) => contact.name).join(', ') }}</div>
          <div v-if="invoice.notes" class="col-span-2 whitespace-pre-line"><span class="text-surface-500">{{ t('common.notes') }}</span><br>{{ invoice.notes }}</div>
          <div class="col-span-2">
            <span class="text-surface-500">{{ t('settings.bankAccount') }}</span>
            <Select v-if="isDraft" :model-value="invoice.bank_account_override" :options="bankAccounts" option-label="name" option-value="id" show-clear :placeholder="invoice.bank_account?.name || t('invoices.inheritedBankAccount')" class="w-full mt-1" @update:model-value="updateBankAccount" />
            <div v-else>{{ invoice.bank_account?.name || '—' }}</div>
          </div>
        </div>

        <AppDataTable v-if="isDraft" :rows="invoice.items" :state-key="tableStateKeys.invoiceDraftItems" @row-click="openItem">
          <Column field="position" header="#" class="w-10" sortable />
          <Column class="app-text" field="description" :header="t('time.description')" sortable />
          <Column class="app-num" :header="t('invoices.quantity')"><template #body="{ data }"><AppNumberDisplay :value="data.quantity" /></template></Column>
          <Column class="app-num" :header="t('invoices.unitPrice')">
            <template #body="{ data }"><AppMoneyDisplay :amount="data.unit_price" :currency="invoice!.currency" /></template>
          </Column>
          <Column class="app-num" :header="t('common.total')">
            <template #body="{ data }"><AppMoneyDisplay :amount="data.total" :currency="invoice!.currency" /></template>
          </Column>
          <Column :reorderable-column="false">
            <template #body="{ data }"><AppIconButton icon="pi pi-trash" severity="danger" @click.stop="confirmDelete(async () => { await invoiceItemsApi.remove(data.id); await load() })" /></template>
          </Column>
        </AppDataTable>
        <AppDataTable v-else :rows="invoice.items" :state-key="tableStateKeys.invoiceItems">
          <Column field="position" header="#" class="w-10" sortable />
          <Column class="app-text" field="description" :header="t('time.description')" sortable />
          <Column class="app-num" :header="t('invoices.quantity')"><template #body="{ data }"><AppNumberDisplay :value="data.quantity" /></template></Column>
          <Column class="app-num" :header="t('invoices.unitPrice')">
            <template #body="{ data }"><AppMoneyDisplay :amount="data.unit_price" :currency="invoice!.currency" /></template>
          </Column>
          <Column class="app-num" :header="t('common.total')">
            <template #body="{ data }"><AppMoneyDisplay :amount="data.total" :currency="invoice!.currency" /></template>
          </Column>
        </AppDataTable>

        <div v-if="isDraft" class="border border-t-0 border-surface-200 dark:border-surface-800 px-2 py-1">
          <Button :label="t('invoices.addLine')" icon="pi pi-plus" text size="small" @click="openItem()" />
        </div>
        <div class="border border-t-0 border-surface-200 dark:border-surface-800 p-4 text-sm">
          <div class="flex justify-between"><span>{{ t('invoices.subtotal') }}</span><AppMoneyDisplay :amount="invoice.subtotal" :currency="invoice.currency" /></div>
          <div class="flex justify-between"><span>{{ t('invoices.vat') }}</span><AppMoneyDisplay :amount="invoice.vat_amount" :currency="invoice.currency" /></div>
          <div class="flex justify-between font-semibold text-base mt-1"><span>{{ t('common.total') }}</span><AppMoneyDisplay :amount="invoice.total" :currency="invoice.currency" /></div>
          <div v-if="Number(invoice.amount_paid) > 0" class="flex justify-between text-green-600"><span>{{ t('invoices.paid') }}</span><AppMoneyDisplay :amount="invoice.amount_paid" :currency="invoice.currency" /></div>
          <div v-if="Number(invoice.remaining) > 0" class="flex justify-between" :class="{ 'text-red-500': !isDraft }"><span>{{ t('invoices.remaining') }}</span><AppMoneyDisplay :amount="invoice.remaining" :currency="invoice.currency" /></div>
        </div>

        <div class="flex gap-2 mt-3">
          <a :href="pdfUrl" target="_blank"><Button :label="t('invoices.downloadPdf')" icon="pi pi-file-pdf" size="small" /></a>
          <a v-if="invoice.e_invoice_format === 'xrechnung'" :href="xmlUrl" target="_blank"><Button :label="t('invoices.downloadXml')" icon="pi pi-code" size="small" severity="secondary" /></a>
        </div>

        <Tabs value="payments" class="mt-6">
          <TabList>
            <Tab value="payments">{{ t('invoices.payments') }}</Tab>
            <Tab value="attachments">{{ t('customers.attachments') }}</Tab>
          </TabList>
          <TabPanels>
            <TabPanel value="payments">
              <AppDataTable :rows="invoice.payments" :state-key="tableStateKeys.invoicePayments">
                <Column field="date" :header="t('common.date')" sortable><template #body="{ data }"><AppDateTimeDisplay :value="data.date" /></template></Column>
                <Column class="app-num" field="amount" :header="t('common.amount')" sortable>
                  <template #body="{ data }"><AppMoneyDisplay :amount="data.amount" :currency="invoice.currency" /></template>
                </Column>
                <Column class="app-text" field="note" :header="t('common.notes')" sortable />
                <Column :header="t('common.actions')" :reorderable-column="false">
                  <template #body="{ data }"><AppIconButton icon="pi pi-trash" severity="danger" @click.stop="confirmDelete(async () => { await paymentsApi.remove(data.id); load() })" /></template>
                </Column>
              </AppDataTable>
            </TabPanel>
            <TabPanel value="attachments"><AttachmentList model="invoice" :object-id="id" /></TabPanel>
          </TabPanels>
        </Tabs>
      </div>

      <div class="border border-surface-200 dark:border-surface-800 h-150 min-h-96">
        <InvoicePreviewFrame :url="previewUrl" />
      </div>
    </div>

    <AppModal ref="emailModal" :form="emailForm" :title="t('invoices.sendEmail')" :confirm-label="t('common.send')" @confirm="sendEmail">
      <div class="flex flex-col gap-4">
        <AppFormField field="to" :label="t('common.email')" required><InputText v-model="emailForm.to" class="w-full" /></AppFormField>
        <AppFormField field="subject" :label="t('designer.mailSubject')"><InputText v-model="emailForm.subject" class="w-full" /></AppFormField>
        <AppFormField field="body" :label="t('designer.mailBody')"><Textarea v-model="emailForm.body" rows="5" class="w-full" /></AppFormField>
      </div>
    </AppModal>

    <AppModal ref="headerModal" :form="headerForm" :title="t('invoices.editInvoice')" :loading="busy" @confirm="saveHeader">
      <div class="flex flex-col gap-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <AppFormField field="issue_date" :label="t('invoices.issueDate')" required><AppDateInput v-model="(headerForm.issue_date as any)" /></AppFormField>
          <AppFormField field="due_date" :label="t('invoices.dueDate')"><AppDateInput v-model="(headerForm.due_date as any)" /></AppFormField>
          <AppFormField field="vat_rate" :label="t('invoices.vatRate')"><InputNumber v-model="headerForm.vat_rate" :min="0" :max="100" :max-fraction-digits="2" suffix=" %" class="w-full" fluid /></AppFormField>
          <AppFormField field="e_invoice_format" :label="t('invoices.eInvoice')">
            <Select v-model="headerForm.e_invoice_format" :options="formats" class="w-full">
              <template #option="{ option }">{{ t(`invoices.eInvoiceFormats.${option}`) }}</template>
              <template #value="{ value }">{{ value ? t(`invoices.eInvoiceFormats.${value}`) : '' }}</template>
            </Select>
          </AppFormField>
        </div>
        <AppFormField field="contact_ids" :label="t('invoices.contacts')">
          <MultiSelect v-model="headerForm.contact_ids" :options="customerContacts" option-label="name" option-value="id" display="chip" class="w-full" />
        </AppFormField>
        <AppFormField field="notes" :label="t('common.notes')"><Textarea v-model="headerForm.notes" rows="3" class="w-full" /></AppFormField>
      </div>
    </AppModal>

    <AppModal ref="itemModal" :form="itemForm" :title="editingItem ? t('invoices.editLine') : t('invoices.addLine')" :loading="busy" @confirm="saveItem">
      <div class="flex flex-col gap-4">
        <AppFormField field="description" :label="t('time.description')" required><Textarea v-model="itemForm.description" rows="2" auto-resize class="w-full" /></AppFormField>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <AppFormField field="quantity" :label="t('invoices.quantity')" required><InputNumber v-model="itemForm.quantity" :min="0" :max-fraction-digits="2" class="w-full" fluid /></AppFormField>
          <AppFormField field="unit" :label="t('invoices.unit')">
            <Select v-model="itemForm.unit" :options="units" class="w-full">
              <template #option="{ option }">{{ t(`invoices.units.${option}`) }}</template>
              <template #value="{ value }">{{ value ? t(`invoices.units.${value}`) : '' }}</template>
            </Select>
          </AppFormField>
          <AppFormField field="unit_price" :label="t('invoices.unitPrice')" required><InputNumber v-model="itemForm.unit_price" mode="currency" :currency="invoice.currency" class="w-full" fluid /></AppFormField>
        </div>
        <p v-if="editingItem" class="text-xs text-surface-500">{{ t('invoices.lineDeleteHint') }}</p>
      </div>
    </AppModal>

    <AppModal ref="paymentModal" :form="paymentForm" :title="t('invoices.addPayment')" @confirm="addPayment">
      <div class="flex flex-col gap-4">
        <AppFormField field="date" :label="t('common.date')" required><AppDateInput v-model="paymentForm.date" /></AppFormField>
        <AppFormField field="amount" :label="t('common.amount')" required><InputNumber v-model="paymentForm.amount" mode="currency" currency="EUR" class="w-full" /></AppFormField>
        <AppFormField field="note" :label="t('common.notes')"><InputText v-model="paymentForm.note" class="w-full" /></AppFormField>
      </div>
    </AppModal>
  </div>
  <AppLoadState v-else :failed="loadFailed" back-to="/invoices" :back-label="t('nav.invoices')" />
</template>
