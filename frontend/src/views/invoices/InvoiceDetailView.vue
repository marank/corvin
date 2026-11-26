<script setup lang="ts">
import { useTabQuery } from '../../composables/useTabQuery'
import { isoDate } from '../../dateTimeInput'
import { computed, ref } from 'vue'
import { useLoadFailed } from '../../composables/useLoadFailed'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Menu from 'primevue/menu'
import Message from 'primevue/message'
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
import AppDurationDisplay from '../../components/ui/AppDurationDisplay.vue'
import AttachmentList from '../../components/AttachmentList.vue'
import InvoicePreviewFrame from '../../components/InvoicePreviewFrame.vue'
import {
  customersApi,
  invoicesApi,
  paymentsApi,
  type Invoice,
  type MailKind,
  type TimeEntry,
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
const busy = ref(false)
const emailModal = ref<InstanceType<typeof AppModal>>()
const paymentModal = ref<InstanceType<typeof AppModal>>()
const emailForm = ref<{ to: string; subject: string; kind: MailKind }>({
  to: '',
  subject: '',
  kind: 'invoice',
})
// The mail as it goes out (from the e-mail template of its kind); only the subject is edited here.
const emailHtml = ref('')
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
// The documents to download, behind "Dokumente" in the header.
const documentsMenu = ref<InstanceType<typeof Menu>>()
const documents = computed(() => [
  { label: t('invoices.documentPdf'), icon: 'pi pi-file-pdf', url: pdfUrl.value, target: '_blank' },
  ...(invoice.value?.has_time_entries
    ? [
        {
          label: t('invoices.documentTimeReport'),
          icon: 'pi pi-list',
          url: timeReportUrl.value,
          target: '_blank',
        },
      ]
    : []),
  ...(invoice.value?.e_invoice_format === 'xrechnung'
    ? [
        {
          label: t('invoices.documentXml'),
          icon: 'pi pi-code',
          url: xmlUrl.value,
          target: '_blank',
        },
      ]
    : []),
])
// Rarely needed actions behind the ⋮ button.
const moreMenu = ref<InstanceType<typeof Menu>>()
// The theme colours the link itself; only its label and icon turn red.
const dangerItem = '[&_.p-menu-item-label]:text-danger [&_.p-menu-item-icon]:text-danger'
const moreActions = computed(() => [
  ...(invoice.value?.status === 'issued'
    ? [{ label: t('invoices.markSent'), icon: 'pi pi-envelope', command: openMarkSent }]
    : []),
  ...(canReceivePayment.value && Number(invoice.value?.remaining) > 0
    ? [
        {
          label: t('invoices.sendReminder'),
          icon: 'pi pi-bell',
          command: () => void openEmail('payment_reminder'),
        },
      ]
    : []),
  ...(isDraft.value
    ? [
        {
          label: t('common.delete'),
          icon: 'pi pi-trash',
          class: dangerItem,
          command: () =>
            confirmDelete(async () => {
              await invoicesApi.remove(id)
              void router.push('/invoices')
            }),
        },
      ]
    : []),
  // Only while nothing has been paid on it.
  ...(canReceivePayment.value && Number(invoice.value?.amount_paid) === 0
    ? [
        {
          label: t('invoices.cancelInvoice'),
          icon: 'pi pi-ban',
          class: dangerItem,
          command: confirmCancel,
        },
      ]
    : []),
])
const isDraft = computed(() => invoice.value?.status === 'draft')
const statusKey = computed(() =>
  invoice.value?.partially_paid ? 'partially_paid' : (invoice.value?.status ?? ''),
)
const canReceivePayment = computed(() => ['issued', 'sent'].includes(invoice.value?.status ?? ''))

// Unpaid after its due date (only once it went out).
const overdue = computed(
  () =>
    canReceivePayment.value &&
    Number(invoice.value?.remaining) > 0 &&
    !!invoice.value?.due_date &&
    invoice.value.due_date < isoDate(),
)

// The time entries the invoice bills; the position of the line billing each comes from the
// lines (contract-covered entries are on none).
const tab = useTabQuery('items', ['items', 'times', 'payments', 'attachments'])
const timeEntries = ref<TimeEntry[]>([])
const positions = computed(
  () =>
    new Map(
      (invoice.value?.items ?? []).flatMap((item) =>
        item.time_entry_ids.map((entryId) => [entryId, item.position] as const),
      ),
    ),
)

async function load() {
  invoice.value = await invoicesApi.get(id)
  previewVersion.value++
  timeEntries.value = invoice.value.has_time_entries ? await invoicesApi.timeEntries(id) : []
}

// Prefill the recipient from the invoice contacts, falling back to the customer's address,
// and the subject with the template's; the dialog shows the mail as it will look.
async function openEmail(kind: MailKind = 'invoice') {
  if (!invoice.value) return
  const [customer, draft] = await Promise.all([
    customersApi.get(invoice.value.customer).catch(() => null),
    invoicesApi.emailDraft(id, kind).catch(() => null),
  ])
  emailForm.value = {
    to: invoice.value.contacts.find((contact) => contact.email)?.email ?? customer?.email ?? '',
    subject: draft?.subject ?? '',
    kind,
  }
  emailHtml.value = draft?.html ?? ''
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
    notify.ok(
      emailForm.value.kind === 'invoice' ? t('invoices.emailQueued') : t('invoices.reminderQueued'),
    )
  })
}

// Sent another way (by post, from the mail client): on which day, today unless told.
const markSentModal = ref<InstanceType<typeof AppModal>>()
const markSentForm = ref({ sent_on: isoDate() })

function openMarkSent() {
  markSentForm.value = { sent_on: isoDate() }
  markSentModal.value?.open()
}

async function markSent() {
  await act(async () => {
    await invoicesApi.markSent(id, markSentForm.value)
    markSentModal.value?.close()
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
        <Button
          :label="t('invoices.documents')"
          icon="pi pi-chevron-down"
          icon-pos="right"
          severity="secondary"
          outlined
          aria-haspopup="menu"
          @click="documentsMenu?.toggle($event)"
        />
        <Menu ref="documentsMenu" :model="documents" popup />
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
          @click="openEmail()"
        />
        <Button
          v-if="canReceivePayment && Number(invoice.remaining) > 0"
          :label="t('invoices.addPayment')"
          icon="pi pi-money-bill"
          @click="openPayment"
        />
        <template v-if="moreActions.length">
          <Button
            icon="pi pi-ellipsis-v"
            text
            severity="secondary"
            :aria-label="t('common.moreActions')"
            aria-haspopup="menu"
            @click="moreMenu?.toggle($event)"
          />
          <Menu ref="moreMenu" :model="moreActions" popup />
        </template>
      </template>
    </AppPageHeader>

    <Message v-if="isDraft && !invoice.bank_account?.iban" severity="warn" class="mb-4">
      {{ t('invoices.noIbanHint') }}
      <router-link to="/settings?tab=bankAccounts" class="underline font-medium">{{
        t('invoices.noIbanLink')
      }}</router-link>
    </Message>

    <div class="grid grid-cols-1 xl:grid-cols-2 gap-4 items-start">
      <div class="flex flex-col gap-4 min-w-0">
        <section class="app-card p-4">
          <div class="flex flex-wrap gap-x-8 gap-y-3 items-end">
            <div>
              <p class="text-sm text-surface-500">{{ t('common.total') }}</p>
              <p class="text-2xl font-semibold">
                <AppMoneyDisplay :amount="invoice.total" :currency="invoice.currency" />
              </p>
            </div>
            <template v-if="!isDraft">
              <div>
                <p class="text-sm text-surface-500">{{ t('invoices.paid') }}</p>
                <p class="text-lg tabular-nums">
                  <AppMoneyDisplay :amount="invoice.amount_paid" :currency="invoice.currency" />
                </p>
              </div>
              <div>
                <p class="text-sm text-surface-500">{{ t('invoices.remaining') }}</p>
                <p class="text-lg tabular-nums" :class="{ 'text-danger': overdue }">
                  <AppMoneyDisplay :amount="invoice.remaining" :currency="invoice.currency" />
                </p>
              </div>
            </template>
            <div>
              <p class="text-sm text-surface-500">{{ t('invoices.dueDate') }}</p>
              <p class="text-lg" :class="{ 'text-danger font-medium': overdue }">
                <AppDateTimeDisplay :value="invoice.due_date" />
                <span v-if="overdue" class="text-sm">
                  · {{ t('invoices.receivables.overdue') }}</span
                >
              </p>
            </div>
            <div v-if="invoice.sent_at">
              <p class="text-sm text-surface-500">{{ t('invoices.sentAt') }}</p>
              <p class="text-lg"><AppDateTimeDisplay :value="invoice.sent_at" /></p>
            </div>
          </div>
        </section>

        <section class="app-card p-4">
          <dl class="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            <div>
              <dt class="text-surface-500">{{ t('projects.customer') }}</dt>
              <dd>
                <router-link :to="`/customers/${invoice.customer}`" class="hover:underline">{{
                  invoice.customer_name
                }}</router-link>
              </dd>
            </div>
            <div v-if="invoice.project">
              <dt class="text-surface-500">{{ t('projects.project') }}</dt>
              <dd>
                <router-link :to="`/projects/${invoice.project}`" class="hover:underline">{{
                  invoice.project_name
                }}</router-link>
              </dd>
            </div>
            <div v-if="invoice.contract">
              <dt class="text-surface-500">{{ t('invoices.contract') }}</dt>
              <dd>
                <router-link :to="`/contracts/${invoice.contract}`" class="hover:underline">{{
                  invoice.contract_name
                }}</router-link>
              </dd>
            </div>
            <div>
              <dt class="text-surface-500">{{ t('invoices.issueDate') }}</dt>
              <dd><AppDateTimeDisplay :value="invoice.issue_date" /></dd>
            </div>
            <div v-if="invoice.contacts.length">
              <dt class="text-surface-500">{{ t('invoices.contacts') }}</dt>
              <dd>{{ invoice.contacts.map((contact) => contact.name).join(', ') }}</dd>
            </div>
            <div>
              <dt class="text-surface-500">{{ t('settings.bankAccount') }}</dt>
              <dd>{{ invoice.bank_account?.name || '—' }}</dd>
            </div>
            <div>
              <dt class="text-surface-500">{{ t('invoices.eInvoice') }}</dt>
              <dd>{{ t(`invoices.eInvoiceFormats.${invoice.e_invoice_format}`) }}</dd>
            </div>
            <div>
              <dt class="text-surface-500">{{ t('invoices.vatRate') }}</dt>
              <dd><AppNumberDisplay :value="invoice.vat_rate" :maximum-fraction-digits="2" /> %</dd>
            </div>
            <div v-if="invoice.notes" class="col-span-2">
              <dt class="text-surface-500">{{ t('common.notes') }}</dt>
              <dd class="whitespace-pre-line">{{ invoice.notes }}</dd>
            </div>
          </dl>
        </section>

        <Tabs v-model:value="tab">
          <TabList>
            <Tab value="items">{{ t('invoices.positions') }}</Tab>
            <Tab v-if="invoice.has_time_entries" value="times">{{ t('invoices.times') }}</Tab>
            <Tab v-if="!isDraft" value="payments">{{ t('invoices.payments') }}</Tab>
            <Tab value="attachments">{{ t('customers.attachments') }}</Tab>
          </TabList>
          <TabPanels>
            <TabPanel value="items" class="pt-4">
              <AppDataTable :rows="invoice.items" :state-key="tableStateKeys.invoiceItems">
                <Column field="position" header="#" class="w-10" sortable />
                <Column
                  class="app-text"
                  field="description"
                  :header="t('time.description')"
                  sortable
                />
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
              <div class="flex justify-end pt-3">
                <div class="w-72 flex flex-col gap-1 text-sm tabular-nums">
                  <div class="flex justify-between">
                    <span class="text-surface-500">{{
                      t('invoices.subtotal')
                    }}</span><AppMoneyDisplay
                      :amount="invoice.subtotal"
                      :currency="invoice.currency"
                    />
                  </div>
                  <div class="flex justify-between">
                    <span class="text-surface-500">{{ t('invoices.vat') }}</span><AppMoneyDisplay
                      :amount="invoice.vat_amount"
                      :currency="invoice.currency"
                    />
                  </div>
                  <div
                    class="flex justify-between font-semibold pt-1 border-t border-surface-200 dark:border-surface-800"
                  >
                    <span>{{ t('common.total') }}</span><AppMoneyDisplay
                      :amount="invoice.total"
                      :currency="invoice.currency"
                    />
                  </div>
                </div>
              </div>
            </TabPanel>
            <TabPanel v-if="invoice.has_time_entries" value="times" class="pt-4">
              <AppDataTable :rows="timeEntries" :state-key="tableStateKeys.invoiceTimeEntries">
                <Column field="start_datetime" :header="t('common.date')" sortable
                  ><template #body="{ data }"
                    ><AppDateTimeDisplay :value="data.start_datetime" type="datetime" /></template
                ></Column>
                <Column :header="t('invoices.position')"
                  ><template #body="{ data }">{{ positions.get(data.id) ?? '—' }}</template></Column
                >
                <Column
                  class="app-text"
                  field="project_name"
                  :header="t('projects.project')"
                  sortable
                />
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
            </TabPanel>
            <TabPanel v-if="!isDraft" value="payments" class="pt-4">
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

      <!-- The invoice as it prints: as tall as the window allows, staying in view. -->
      <div
        class="border border-surface-200 dark:border-surface-800 h-[calc(100vh-8rem)] min-h-96 xl:sticky xl:top-4"
      >
        <InvoicePreviewFrame :url="previewUrl" />
      </div>
    </div>

    <AppModal
      ref="emailModal"
      :form="emailForm"
      :title="emailForm.kind === 'invoice' ? t('invoices.sendEmail') : t('invoices.sendReminder')"
      :confirm-label="t('common.send')"
      size="xl"
      @confirm="sendEmail"
    >
      <div class="flex flex-col gap-4">
        <AppFormField field="to" :label="t('common.email')" required
          ><InputText v-model="emailForm.to" class="w-full"
        /></AppFormField>
        <AppFormField field="subject" :label="t('invoices.mailSubject')"
          ><InputText v-model="emailForm.subject" class="w-full"
        /></AppFormField>
        <div class="h-96 border border-surface-200 dark:border-surface-800">
          <InvoicePreviewFrame :html="emailHtml" />
        </div>
      </div>
    </AppModal>

    <AppModal
      ref="markSentModal"
      :form="markSentForm"
      :title="t('invoices.markSent')"
      :confirm-label="t('invoices.markSent')"
      @confirm="markSent"
    >
      <AppFormField field="sent_on" :label="t('invoices.sentAt')" required
        ><AppDateInput v-model="markSentForm.sent_on"
      /></AppFormField>
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
