<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppCheckboxField from '../../components/ui/AppCheckboxField.vue'
import AppModal from '../../components/ui/AppModal.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppDateInput from '../../components/ui/AppDateInput.vue'
import AppMoneyDisplay from '../../components/ui/AppMoneyDisplay.vue'
import AppDateTimeDisplay from '../../components/ui/AppDateTimeDisplay.vue'
import AttachmentList from '../../components/AttachmentList.vue'
import {
  addressesApi, bankAccountsApi, contactsApi, customersApi, ratesApi,
  type Address, type BankAccount, type Contact, type Customer, type HourlyRate,
} from '../../api'
import { useNotify } from '../../composables/useNotify'

const { t } = useI18n()
const route = useRoute()
const notify = useNotify()
const id = route.params.id as string

const customer = ref<Customer | null>(null)
const contacts = ref<Contact[]>([])
const addresses = ref<Address[]>([])
const rates = ref<HourlyRate[]>([])
const bankAccounts = ref<BankAccount[]>([])
const saving = ref(false)

const form = ref<Partial<Customer>>({})
const contactModal = ref<InstanceType<typeof AppModal>>()
const rateModal = ref<InstanceType<typeof AppModal>>()
const addressModal = ref<InstanceType<typeof AppModal>>()
const editingContact = ref<Contact | null>(null)
const contactForm = ref<Partial<Contact>>({ is_invoice_contact: false })
const rateForm = ref<Partial<HourlyRate>>({ amount: 0, valid_from: '', valid_to: null })
const addressForm = ref<Partial<Address>>({ country: 'Deutschland' })

const subtitle = computed(() => {
  const a = customer.value?.primary_address
  return a ? `${a.postal_code} ${a.city}`.trim() : ''
})

async function load() {
  customer.value = await customersApi.get(id)
  form.value = { ...customer.value }
  contacts.value = (await contactsApi.list(id)).results
  addresses.value = (await addressesApi.list(id)).results
  rates.value = (await ratesApi.list(`customer=${id}&page_size=100`)).results
  bankAccounts.value = (await bankAccountsApi.list()).results.filter((account) => account.is_active)
}
onMounted(load)

async function saveCustomer() {
  saving.value = true
  try {
    customer.value = await customersApi.update(id, form.value)
    notify.ok(t('common.save'))
  } catch (e) {
    notify.error(e)
  } finally {
    saving.value = false
  }
}

function openContact(contact?: Contact) {
  editingContact.value = contact ?? null
  contactForm.value = contact
    ? { ...contact }
    : { is_invoice_contact: false }
  contactModal.value?.open()
}

async function saveContact() {
  try {
    if (editingContact.value) {
      await contactsApi.update(editingContact.value.id, contactForm.value)
    } else {
      await contactsApi.create({ ...contactForm.value, customer: id })
    }
    contactModal.value?.close()
    contacts.value = (await contactsApi.list(id)).results
  } catch (e) {
    notify.error(e)
  }
}

async function removeContact(c: Contact) {
  await contactsApi.remove(c.id)
  contacts.value = (await contactsApi.list(id)).results
}

async function saveAddress() {
  try {
    await addressesApi.create({ ...addressForm.value, customer: id })
    addressModal.value?.close()
    load()
  } catch (e) {
    notify.error(e)
  }
}

async function removeAddress(a: Address) {
  await addressesApi.remove(a.id)
  load()
}

async function saveRate() {
  try {
    await ratesApi.create({ ...rateForm.value, customer: id })
    rateModal.value?.close()
    rates.value = (await ratesApi.list(`customer=${id}&page_size=100`)).results
  } catch (e) {
    notify.error(e)
  }
}
</script>

<template>
  <div v-if="customer">
    <AppPageHeader :title="customer.name" :subtitle="subtitle">
      <template #actions>
        <Button :label="t('common.save')" :loading="saving" @click="saveCustomer" />
      </template>
    </AppPageHeader>

    <Tabs value="details">
      <TabList>
        <Tab value="details">{{ t('settings.profile') }}</Tab>
        <Tab value="contacts">{{ t('customers.contacts') }}</Tab>
        <Tab value="addresses">{{ t('customers.addresses') }}</Tab>
        <Tab value="rates">{{ t('customers.rates') }}</Tab>
        <Tab value="attachments">{{ t('customers.attachments') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="details">
          <div class="flex flex-col gap-6 max-w-3xl pt-4">
            <fieldset class="border-t border-surface-200 dark:border-surface-700 pt-4">
              <legend class="ml-4 px-2 font-medium">{{ t('customers.groups.masterData') }}</legend>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <AppFormField :label="t('common.number')"><InputText v-model="form.number" class="w-full" readonly /></AppFormField>
                <AppFormField :label="t('common.name')"><InputText v-model="form.name" class="w-full" /></AppFormField>
                <AppCheckboxField v-model="form.is_active" :label="t('customers.active')" />
                <AppFormField :label="t('common.notes')" class="md:col-span-2"><Textarea v-model="form.notes" rows="3" class="w-full" /></AppFormField>
              </div>
            </fieldset>

            <fieldset class="border-t border-surface-200 dark:border-surface-700 pt-4">
              <legend class="ml-4 px-2 font-medium">{{ t('customers.groups.contact') }}</legend>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <AppFormField :label="t('common.email')"><InputText v-model="form.email" class="w-full" /></AppFormField>
                <AppFormField :label="t('common.phone')"><InputText v-model="form.phone" class="w-full" /></AppFormField>
                <AppFormField :label="t('customers.website')" class="md:col-span-2"><InputText v-model="form.website" class="w-full" /></AppFormField>
              </div>
            </fieldset>

            <fieldset class="border-t border-surface-200 dark:border-surface-700 pt-4">
              <legend class="ml-4 px-2 font-medium">{{ t('customers.groups.billing') }}</legend>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <AppFormField :label="t('customers.vatId')"><InputText v-model="form.vat_id" class="w-full" /></AppFormField>
                <AppFormField :label="t('customers.buyerReference')"><InputText v-model="form.buyer_reference" class="w-full" /></AppFormField>
                <AppFormField :label="t('customers.paymentTerms')"><InputNumber v-model="form.payment_terms_days" :min="0" :placeholder="t('customers.paymentTermsDefault')" class="w-full" /></AppFormField>
                <AppFormField :label="t('settings.bankAccount')"><Select v-model="form.bank_account" :options="bankAccounts" option-label="name" option-value="id" show-clear :placeholder="t('settings.companyDefault')" class="w-full" /></AppFormField>
              </div>
            </fieldset>

            <fieldset class="border-t border-surface-200 dark:border-surface-700 pt-4">
              <legend class="ml-4 px-2 font-medium">{{ t('customers.groups.timeTracking') }}</legend>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <AppFormField :label="t('customers.rounding')"><InputNumber v-model="form.rounding_increment_minutes" :min="0" class="w-full" /></AppFormField>
              </div>
            </fieldset>
          </div>
        </TabPanel>
        <TabPanel value="contacts">
          <div class="flex justify-end pt-4 mb-2">
            <Button :label="t('common.new')" icon="pi pi-plus" size="small" @click="openContact()" />
          </div>
          <AppDataTable :rows="contacts" @row-click="openContact">
            <Column field="first_name" :header="t('customers.firstName')" />
            <Column field="last_name" :header="t('customers.lastName')" />
            <Column field="role" :header="t('customers.role')" />
            <Column field="email" :header="t('common.email')" />
            <Column field="phone" :header="t('common.phone')" />
            <Column :header="t('customers.invoiceContact')">
              <template #body="{ data }"><i v-if="data.is_invoice_contact" class="pi pi-check" /></template>
            </Column>
            <Column :header="t('common.actions')">
              <template #body="{ data }"><Button icon="pi pi-trash" text size="small" severity="danger" @click.stop="removeContact(data)" /></template>
            </Column>
          </AppDataTable>
        </TabPanel>
        <TabPanel value="addresses">
          <div class="flex justify-end pt-4 mb-2">
            <Button :label="t('common.new')" icon="pi pi-plus" size="small" @click="addressForm = { country: 'Deutschland' }; addressModal?.open()" />
          </div>
          <AppDataTable :rows="addresses">
            <Column field="label" :header="t('customers.addressLabel')" />
            <Column field="street" :header="t('common.address')" />
            <Column :header="t('common.address')">
              <template #body="{ data }">{{ data.postal_code }} {{ data.city }}</template>
            </Column>
            <Column field="country" :header="t('common.address')" />
            <Column :header="t('common.status')">
              <template #body="{ data }"><Tag v-if="data.is_primary" :value="t('customers.primary')" severity="info" /></template>
            </Column>
            <Column :header="t('common.actions')">
              <template #body="{ data }"><Button icon="pi pi-trash" text size="small" severity="danger" @click.stop="removeAddress(data)" /></template>
            </Column>
          </AppDataTable>
        </TabPanel>
        <TabPanel value="rates">
          <div class="flex justify-end pt-4 mb-2">
            <Button :label="t('common.new')" icon="pi pi-plus" size="small" @click="rateForm = { amount: 0, valid_from: '', valid_to: null }; rateModal?.open()" />
          </div>
          <AppDataTable :rows="rates">
            <Column :header="t('common.date')"><template #body="{ data }"><AppDateTimeDisplay :value="data.valid_from" /></template></Column>
            <Column :header="t('invoices.unitPrice')">
              <template #body="{ data }"><AppMoneyDisplay :amount="data.amount" />/h</template>
            </Column>
            <Column field="valid_to" :header="t('time.end')">
              <template #body="{ data }"><AppDateTimeDisplay :value="data.valid_to" /></template>
            </Column>
          </AppDataTable>
        </TabPanel>
        <TabPanel value="attachments">
          <div class="pt-4"><AttachmentList model="customer" :object-id="id" /></div>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <AppModal ref="contactModal" :title="t('customers.contacts')" @confirm="saveContact">
      <div class="flex flex-col gap-4">
        <div class="grid grid-cols-2 gap-3">
          <AppFormField :label="t('customers.firstName')" required><InputText v-model="contactForm.first_name" class="w-full" /></AppFormField>
          <AppFormField :label="t('customers.lastName')"><InputText v-model="contactForm.last_name" class="w-full" /></AppFormField>
        </div>
        <AppFormField :label="t('customers.role')"><InputText v-model="contactForm.role" class="w-full" /></AppFormField>
        <AppFormField :label="t('common.email')"><InputText v-model="contactForm.email" class="w-full" /></AppFormField>
        <AppFormField :label="t('common.phone')"><InputText v-model="contactForm.phone" class="w-full" /></AppFormField>
        <AppCheckboxField v-model="contactForm.is_invoice_contact" :label="t('customers.invoiceContact')" />
      </div>
    </AppModal>

    <AppModal ref="addressModal" :title="t('customers.addresses')" @confirm="saveAddress">
      <div class="flex flex-col gap-4">
        <div class="grid grid-cols-2 gap-3">
          <AppFormField :label="t('customers.addressLabel')"><InputText v-model="addressForm.label" class="w-full" /></AppFormField>
          <AppFormField :label="t('common.address')"><InputText v-model="addressForm.country" class="w-full" /></AppFormField>
        </div>
        <AppFormField :label="t('common.address')"><InputText v-model="addressForm.street" class="w-full" /></AppFormField>
        <div class="grid grid-cols-3 gap-3">
          <AppFormField label="PLZ"><InputText v-model="addressForm.postal_code" class="w-full" /></AppFormField>
          <AppFormField :label="t('common.address')" class="col-span-2"><InputText v-model="addressForm.city" class="w-full" /></AppFormField>
        </div>
        <AppCheckboxField v-model="addressForm.is_primary" :label="t('customers.primary')" />
      </div>
    </AppModal>

    <AppModal ref="rateModal" :title="t('customers.rates')" @confirm="saveRate">
      <div class="flex flex-col gap-4">
        <AppFormField :label="t('invoices.unitPrice')" required><InputNumber v-model="rateForm.amount" mode="currency" currency="EUR" class="w-full" /></AppFormField>
        <AppFormField :label="t('common.date')" required><AppDateInput v-model="(rateForm.valid_from as any)" /></AppFormField>
        <AppFormField :label="t('time.end')"><AppDateInput v-model="(rateForm.valid_to as any)" /></AppFormField>
      </div>
    </AppModal>
  </div>
</template>
