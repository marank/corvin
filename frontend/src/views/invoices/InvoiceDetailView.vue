<script setup lang="ts">
import { isoDate } from '../../dateTimeInput'
import { computed, ref } from 'vue'
import { useLoadFailed } from '../../composables/useLoadFailed'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
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
import { customersApi, invoicesApi, paymentsApi, type Invoice } from '../../api'
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
const busy = ref(false)
const emailModal = ref<InstanceType<typeof AppModal>>()
const paymentModal = ref<InstanceType<typeof AppModal>>()
const emailForm = ref({ to: '', subject: '', body: '' })
const paymentForm = ref({ date: isoDate(), amount: 0, note: '' })

function openPayment() {
  if (!invoice.value) return
  paymentForm.value = { date: isoDate(), amount: Number(invoice.value.remaining), note: '' }
  paymentModal.value?.open()
}

// Bumped after every change so the preview iframe reloads.
const previewVersion = ref(0)
const previewUrl = computed(() => `${invoicesApi.previewUrl(id)}?v=${previewVersion.value}`)
const pdfUrl = computed(() => invoicesApi.pdfUrl(id))
const xmlUrl = computed(() => invoicesApi.xmlUrl(id))
const timeReportUrl = computed(() => invoicesApi.timeReportUrl(id))
const isDraft = computed(() => invoice.value?.status === 'draft')
const statusKey = computed(() =>
  invoice.value?.partially_paid ? 'partially_paid' : (invoice.value?.status ?? ''),
)
const canReceivePayment = computed(() => ['issued', 'sent'].includes(invoice.value?.status ?? ''))

async function load() {
  invoice.value = await invoicesApi.get(id)
  previewVersion.value++
}

// Prefill the recipient from the invoice contacts, falling back to the customer's address,
// and subject/body with the text the template would send.
async function openEmail() {
  if (!invoice.value) return
  const [customer, draft] = await Promise.all([
    customersApi.get(invoice.value.customer).catch(() => null),
    invoicesApi.emailDraft(id).catch(() => null),
  ])
  emailForm.value = {
    to: invoice.value.contacts.find((contact) => contact.email)?.email ?? customer?.email ?? '',
    subject: '',
    body: '',
    ...draft,
  }
  emailModal.value?.open()
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
    accept: () => void act(() => invoicesApi.finalize(id)),
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
    accept: () => void act(() => invoicesApi.cancel(id)),
  })
}

async function sendEmail() {
  await act(async () => {
    await invoicesApi.sendEmail(id, emailForm.value)
    emailModal.value?.close()
    notify.ok(t('invoices.emailQueued'))
  })
}

async function addPayment() {
  await act(async () => {
    await paymentsApi.create({ ...paymentForm.value, invoice: id })
    paymentModal.value?.close()
    notify.ok(t('invoices.paymentAdded'))
  })
}
</script>

<template>
  <div v-if="invoice">
    <AppPageHeader
      back-to="/invoices"
      :back-label="t('nav.invoices')"
      :title="invoice.number || '—'"
      :subtitle="invoice.customer_name"
    >
      <template #title-end>
        <AppStatusTag :status="statusKey" :label="t(`invoices.status.${statusKey}`)" />
      </template>
      <template #actions>
        <!-- A draft is edited on the create page; nothing is changed here. -->
        <Button
          v-if="isDraft"
          :label="t('common.edit')"
          icon="pi pi-pencil"
          outlined
          @click="router.push(`/invoices/${id}/edit`)"
        />
        <Button
          v-if="isDraft"
          :label="t('invoices.finalize')"
          icon="pi pi-lock"
          :loading="busy"
          @click="confirmFinalize"
        />
        <Button
          v-if="canReceivePayment"
          :label="t('invoices.sendEmail')"
          icon="pi pi-send"
          :loading="busy"
          @click="openEmail"
        />
        <Button
          v-if="canReceivePayment && Number(invoice.remaining) > 0"
          :label="t('invoices.addPayment')"
          icon="pi pi-money-bill"
          @click="openPayment"
        />
        <Button
          v-if="invoice.status === 'issued'"
          :label="t('invoices.markSent')"
          text
          :loading="busy"
          @click="act(() => invoicesApi.markSent(id))"
        />
        <Button
          v-if="canReceivePayment && Number(invoice.amount_paid) === 0"
          :label="t('invoices.cancelInvoice')"
          text
          severity="danger"
          :loading="busy"
          @click="confirmCancel"
        />
        <Button
          v-if="isDraft"
          :label="t('common.delete')"
          text
          severity="danger"
          @click="
            confirmDelete(async () => {
              await invoicesApi.remove(id)
              router.push('/invoices')
            })
          "
        />
      </template>
    </AppPageHeader>

    <Message v-if="isDraft && !invoice.bank_account?.iban" severity="warn" class="mb-4">
      {{ t('invoices.noIbanHint') }}
      <router-link to="/settings?tab=bankAccounts" class="underline font-medium">{{
        t('invoices.noIbanLink')
      }}</router-link>
    </Message>

    <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
      <div>
        <div class="app-card p-4 mb-4 grid grid-cols-2 gap-3 text-sm">
          <div>
            <span class="text-surface-500">{{
              t('invoices.issueDate')
            }}</span><br /><AppDateTimeDisplay :value="invoice.issue_date" />
          </div>
          <div>
            <span class="text-surface-500">{{
              t('invoices.dueDate')
            }}</span><br /><AppDateTimeDisplay :value="invoice.due_date" />
          </div>
          <div>
            <span class="text-surface-500">{{ t('invoices.eInvoice') }}</span><br />{{
              t(`invoices.eInvoiceFormats.${invoice.e_invoice_format}`)
            }}
          </div>
          <div>
            <span class="text-surface-500">{{ t('invoices.vatRate') }}</span><br /><AppNumberDisplay
              :value="invoice.vat_rate"
              :maximum-fraction-digits="2"
            />%
          </div>
          <div v-if="invoice.contacts.length" class="col-span-2">
            <span class="text-surface-500">{{ t('invoices.contacts') }}</span><br />{{
              invoice.contacts.map((contact) => contact.name).join(', ')
            }}
          </div>
          <div v-if="invoice.notes" class="col-span-2 whitespace-pre-line">
            <span class="text-surface-500">{{ t('common.notes') }}</span><br />{{ invoice.notes }}
          </div>
          <div class="col-span-2">
            <span class="text-surface-500">{{ t('settings.bankAccount') }}</span><br />{{
              invoice.bank_account?.name || '—'
            }}
          </div>
        </div>

        <AppDataTable :rows="invoice.items" :state-key="tableStateKeys.invoiceItems">
          <Column field="position" header="#" class="w-10" sortable />
          <Column class="app-text" field="description" :header="t('time.description')" sortable />
          <Column class="app-num" :header="t('invoices.quantity')"
            ><template #body="{ data }"><AppNumberDisplay :value="data.quantity" /></template
          ></Column>
          <Column class="app-num" :header="t('invoices.unitPrice')">
            <template #body="{ data }"
              ><AppMoneyDisplay :amount="data.unit_price" :currency="invoice!.currency"
            /></template>
          </Column>
          <Column class="app-num" :header="t('common.total')">
            <template #body="{ data }"
              ><AppMoneyDisplay :amount="data.total" :currency="invoice!.currency"
            /></template>
          </Column>
        </AppDataTable>

        <div class="border border-t-0 border-surface-200 dark:border-surface-800 p-4 text-sm">
          <div class="flex justify-between">
            <span>{{ t('invoices.subtotal') }}</span><AppMoneyDisplay
              :amount="invoice.subtotal"
              :currency="invoice.currency"
            />
          </div>
          <div class="flex justify-between">
            <span>{{ t('invoices.vat') }}</span><AppMoneyDisplay
              :amount="invoice.vat_amount"
              :currency="invoice.currency"
            />
          </div>
          <div class="flex justify-between font-semibold text-base mt-1">
            <span>{{ t('common.total') }}</span><AppMoneyDisplay
              :amount="invoice.total"
              :currency="invoice.currency"
            />
          </div>
          <div v-if="Number(invoice.amount_paid) > 0" class="flex justify-between text-success">
            <span>{{ t('invoices.paid') }}</span><AppMoneyDisplay
              :amount="invoice.amount_paid"
              :currency="invoice.currency"
            />
          </div>
          <div
            v-if="Number(invoice.remaining) > 0"
            class="flex justify-between"
            :class="{ 'text-danger': !isDraft }"
          >
            <span>{{ t('invoices.remaining') }}</span><AppMoneyDisplay
              :amount="invoice.remaining"
              :currency="invoice.currency"
            />
          </div>
        </div>

        <div class="flex gap-2 mt-3">
          <Button
            as="a"
            :href="pdfUrl"
            target="_blank"
            :label="t('invoices.downloadPdf')"
            icon="pi pi-file-pdf"
            size="small"
          />
          <Button
            v-if="invoice.e_invoice_format === 'xrechnung'"
            as="a"
            :href="xmlUrl"
            target="_blank"
            :label="t('invoices.downloadXml')"
            icon="pi pi-code"
            size="small"
            severity="secondary"
          />
          <Button
            v-if="invoice.has_time_entries"
            as="a"
            :href="timeReportUrl"
            target="_blank"
            :label="t('invoices.downloadTimeReport')"
            icon="pi pi-list"
            size="small"
            severity="secondary"
          />
        </div>

        <Tabs value="payments" class="mt-6">
          <TabList>
            <Tab value="payments">{{ t('invoices.payments') }}</Tab>
            <Tab value="attachments">{{ t('customers.attachments') }}</Tab>
          </TabList>
          <TabPanels>
            <TabPanel value="payments" class="pt-4">
              <AppDataTable :rows="invoice.payments" :state-key="tableStateKeys.invoicePayments">
                <Column field="date" :header="t('common.date')" sortable
                  ><template #body="{ data }"><AppDateTimeDisplay :value="data.date" /></template
                ></Column>
                <Column class="app-num" field="amount" :header="t('common.amount')" sortable>
                  <template #body="{ data }"
                    ><AppMoneyDisplay :amount="data.amount" :currency="invoice.currency"
                  /></template>
                </Column>
                <Column class="app-text" field="note" :header="t('common.notes')" sortable />
                <Column :header="t('common.actions')" :reorderable-column="false">
                  <template #body="{ data }"
                    ><AppIconButton
                      icon="pi pi-trash"
                      severity="danger"
                      @click.stop="
                        confirmDelete(async () => {
                          await paymentsApi.remove(data.id)
                          load()
                        })
                      "
                  /></template>
                </Column>
              </AppDataTable>
            </TabPanel>
            <TabPanel value="attachments" class="pt-4"
              ><AttachmentList model="invoice" :object-id="id"
            /></TabPanel>
          </TabPanels>
        </Tabs>
      </div>

      <div class="border border-surface-200 dark:border-surface-800 h-150 min-h-96">
        <InvoicePreviewFrame :url="previewUrl" />
      </div>
    </div>

    <AppModal
      ref="emailModal"
      :form="emailForm"
      :title="t('invoices.sendEmail')"
      :confirm-label="t('common.send')"
      @confirm="sendEmail"
    >
      <div class="flex flex-col gap-4">
        <AppFormField field="to" :label="t('common.email')" required
          ><InputText v-model="emailForm.to" class="w-full"
        /></AppFormField>
        <AppFormField field="subject" :label="t('designer.mailSubject')"
          ><InputText v-model="emailForm.subject" class="w-full"
        /></AppFormField>
        <AppFormField field="body" :label="t('designer.mailBody')"
          ><Textarea v-model="emailForm.body" rows="8" class="w-full"
        /></AppFormField>
      </div>
    </AppModal>

    <AppModal
      ref="paymentModal"
      :form="paymentForm"
      :title="t('invoices.addPayment')"
      @confirm="addPayment"
    >
      <div class="flex flex-col gap-4">
        <AppFormField field="date" :label="t('common.date')" required
          ><AppDateInput v-model="paymentForm.date"
        /></AppFormField>
        <AppFormField field="amount" :label="t('common.amount')" required
          ><InputNumber
            v-model="paymentForm.amount"
            mode="currency"
            :currency="invoice.currency"
            class="w-full"
        /></AppFormField>
        <AppFormField field="note" :label="t('common.notes')"
          ><InputText v-model="paymentForm.note" class="w-full"
        /></AppFormField>
      </div>
    </AppModal>
  </div>
  <AppLoadState v-else :failed="loadFailed" back-to="/invoices" :back-label="t('nav.invoices')" />
</template>
