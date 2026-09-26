<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppStatusTag from '../../components/ui/AppStatusTag.vue'
import AppMoneyDisplay from '../../components/ui/AppMoneyDisplay.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppModal from '../../components/ui/AppModal.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppDateInput from '../../components/ui/AppDateInput.vue'
import AttachmentList from '../../components/AttachmentList.vue'
import InvoicePreviewFrame from '../../components/InvoicePreviewFrame.vue'
import { invoicesApi, paymentsApi, type Invoice } from '../../api'
import { useNotify } from '../../composables/useNotify'

const { t } = useI18n()
const route = useRoute()
const notify = useNotify()
const id = Number(route.params.id)

const invoice = ref<Invoice | null>(null)
const busy = ref(false)
const emailModal = ref<InstanceType<typeof AppModal>>()
const paymentModal = ref<InstanceType<typeof AppModal>>()
const emailForm = ref({ to: '', subject: '', body: '' })
const paymentForm = ref({ date: new Date().toISOString().slice(0, 10), amount: 0, note: '' })

const previewUrl = computed(() => invoicesApi.previewUrl(id))
const pdfUrl = computed(() => invoicesApi.pdfUrl(id))
const xmlUrl = computed(() => invoicesApi.xmlUrl(id))
const isDraft = computed(() => invoice.value?.status === 'draft')

async function load() {
  invoice.value = await invoicesApi.get(id)
  emailForm.value.to = invoice.value.customer_name ? '' : ''
}
onMounted(load)

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

async function sendEmail() {
  await act(async () => {
    await invoicesApi.sendEmail(id, emailForm.value)
    emailModal.value?.close()
    notify.ok(t('invoices.sendEmail'))
  })
}

async function addPayment() {
  await act(async () => {
    await paymentsApi.create({ ...paymentForm.value, invoice: id })
    paymentModal.value?.close()
    notify.ok(t('invoices.addPayment'))
  })
}
</script>

<template>
  <div v-if="invoice">
    <AppPageHeader :title="invoice.number || '—'" :subtitle="invoice.customer_name">
      <template #actions>
        <AppStatusTag :status="invoice.partially_paid ? 'partially_paid' : invoice.status" :label="invoice.partially_paid ? t('invoices.status.paid') + ' (teilw.)' : t(`invoices.status.${invoice.status}`)" />
        <Button v-if="isDraft" :label="t('invoices.finalize')" icon="pi pi-lock" :loading="busy" @click="act(() => invoicesApi.finalize(id))" />
        <Button v-if="invoice.status === 'issued'" :label="t('invoices.sendEmail')" icon="pi pi-send" :loading="busy" @click="emailModal?.open()" />
        <Button v-if="invoice.status === 'issued' && Number(invoice.remaining) > 0" :label="t('invoices.addPayment')" icon="pi pi-money-bill" @click="paymentForm.amount = Number(invoice.remaining); paymentModal?.open()" />
        <Button v-if="invoice.status === 'issued'" :label="t('invoices.markSent')" text :loading="busy" @click="act(() => invoicesApi.markSent(id))" />
        <Button v-if="isDraft" :label="t('common.delete')" text severity="danger" @click="act(() => invoicesApi.remove(id))" />
      </template>
    </AppPageHeader>

    <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
      <div>
        <div class="border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-4 mb-4 grid grid-cols-2 gap-3 text-sm">
          <div><span class="text-surface-500">{{ t('invoices.issueDate') }}</span><br>{{ invoice.issue_date }}</div>
          <div><span class="text-surface-500">{{ t('invoices.dueDate') }}</span><br>{{ invoice.due_date ?? '—' }}</div>
          <div><span class="text-surface-500">{{ t('invoices.eInvoice') }}</span><br>{{ invoice.e_invoice_format }}</div>
          <div><span class="text-surface-500">{{ t('invoices.vatRate') }}</span><br>{{ invoice.vat_rate }}%</div>
        </div>

        <AppDataTable :rows="invoice.items">
          <Column field="position" header="#" class="w-10" />
          <Column field="description" :header="t('time.description')" />
          <Column field="quantity" :header="t('invoices.quantity')" />
          <Column :header="t('invoices.unitPrice')">
            <template #body="{ data }"><AppMoneyDisplay :amount="data.unit_price" :currency="invoice!.currency" /></template>
          </Column>
          <Column :header="t('common.total')">
            <template #body="{ data }"><AppMoneyDisplay :amount="data.total" :currency="invoice!.currency" /></template>
          </Column>
        </AppDataTable>

        <div class="border border-t-0 border-surface-200 dark:border-surface-800 p-4 text-sm">
          <div class="flex justify-between"><span>{{ t('invoices.subtotal') }}</span><AppMoneyDisplay :amount="invoice.subtotal" :currency="invoice.currency" /></div>
          <div class="flex justify-between"><span>{{ t('invoices.vat') }}</span><AppMoneyDisplay :amount="invoice.vat_amount" :currency="invoice.currency" /></div>
          <div class="flex justify-between font-semibold text-base mt-1"><span>{{ t('common.total') }}</span><AppMoneyDisplay :amount="invoice.total" :currency="invoice.currency" /></div>
          <div v-if="Number(invoice.amount_paid) > 0" class="flex justify-between text-green-600"><span>{{ t('invoices.paid') }}</span><AppMoneyDisplay :amount="invoice.amount_paid" :currency="invoice.currency" /></div>
          <div v-if="Number(invoice.remaining) > 0" class="flex justify-between text-red-500"><span>{{ t('invoices.remaining') }}</span><AppMoneyDisplay :amount="invoice.remaining" :currency="invoice.currency" /></div>
        </div>

        <div class="flex gap-2 mt-3">
          <a :href="pdfUrl" target="_blank"><Button :label="t('common.download') + ' PDF'" icon="pi pi-file-pdf" size="small" /></a>
          <a v-if="invoice.e_invoice_format === 'xrechnung'" :href="xmlUrl" target="_blank"><Button :label="t('invoices.downloadXml')" icon="pi pi-code" size="small" severity="secondary" /></a>
        </div>

        <Tabs value="payments" class="mt-6">
          <TabList>
            <Tab value="payments">{{ t('invoices.payments') }}</Tab>
            <Tab value="attachments">{{ t('customers.attachments') }}</Tab>
          </TabList>
          <TabPanels>
            <TabPanel value="payments">
              <AppDataTable :rows="invoice.payments">
                <Column field="date" :header="t('common.date')" />
                <Column :header="t('common.total')">
                  <template #body="{ data }"><AppMoneyDisplay :amount="data.amount" :currency="invoice.currency" /></template>
                </Column>
                <Column field="note" :header="t('common.notes')" />
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

    <AppModal ref="emailModal" :title="t('invoices.sendEmail')" @confirm="sendEmail">
      <div class="flex flex-col gap-4">
        <AppFormField :label="t('common.email')" required><InputText v-model="emailForm.to" class="w-full" /></AppFormField>
        <AppFormField :label="t('designer.mailSubject')"><InputText v-model="emailForm.subject" class="w-full" /></AppFormField>
        <AppFormField :label="t('designer.mailBody')"><Textarea v-model="emailForm.body" rows="5" class="w-full" /></AppFormField>
      </div>
    </AppModal>

    <AppModal ref="paymentModal" :title="t('invoices.addPayment')" @confirm="addPayment">
      <div class="flex flex-col gap-4">
        <AppFormField :label="t('common.date')"><AppDateInput v-model="paymentForm.date" /></AppFormField>
        <AppFormField :label="t('common.total')"><InputNumber v-model="paymentForm.amount" mode="currency" currency="EUR" class="w-full" /></AppFormField>
        <AppFormField :label="t('common.notes')"><InputText v-model="paymentForm.note" class="w-full" /></AppFormField>
      </div>
    </AppModal>
  </div>
</template>
