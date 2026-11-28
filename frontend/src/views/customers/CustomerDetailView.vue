<script setup lang="ts">
import { useTabQuery } from '../../composables/useTabQuery'
import { computed, ref } from 'vue'
import { useLoadFailed } from '../../composables/useLoadFailed'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
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
import AppLoadState from '../../components/ui/AppLoadState.vue'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import NumberField from '../../components/NumberField.vue'
import AppCheckboxField from '../../components/ui/AppCheckboxField.vue'
import AppModal from '../../components/ui/AppModal.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import HourlyRateList from '../../components/HourlyRateList.vue'
import TravelRateList from '../../components/TravelRateList.vue'
import AttachmentList from '../../components/AttachmentList.vue'
import RelatedOverview from '../../components/RelatedOverview.vue'
import AppIconButton from '../../components/ui/AppIconButton.vue'
import AppEnumSelect from '../../components/ui/AppEnumSelect.vue'
import { eInvoiceFormatValues as eInvoiceFormats } from '../../utils/enums'
import {
  addressesApi,
  bankAccountsApi,
  contactsApi,
  customersApi,
  type Address,
  type BankAccount,
  type Contact,
  type Customer,
} from '../../api'
import { useNotify } from '../../composables/useNotify'
import { useConfirmDelete } from '../../composables/useConfirmDelete'
import { useUnsavedChanges } from '../../composables/useUnsavedChanges'
import { tableStateKeys } from '../../tableStateKeys'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const id = route.params.id as string

const customer = ref<Customer | null>(null)
const contacts = ref<Contact[]>([])
const addresses = ref<Address[]>([])
const bankAccounts = ref<BankAccount[]>([])
const saving = ref(false)
const tab = useTabQuery('overview', [
  'overview',
  'details',
  'contacts',
  'addresses',
  'rates',
  'attachments',
])

const form = ref<Partial<Customer>>({})
const { markSaved } = useUnsavedChanges(form)
const contactModal = ref<InstanceType<typeof AppModal>>()
const addressModal = ref<InstanceType<typeof AppModal>>()
const editingContact = ref<Contact | null>(null)
const contactForm = ref<Partial<Contact>>({ is_invoice_contact: false })
const editingAddress = ref<Address | null>(null)
const addressForm = ref<Partial<Address>>({
  country: 'Deutschland',
  is_primary: false,
  is_invoice_address: false,
  is_delivery_address: false,
})

const subtitle = computed(() => {
  const a = customer.value?.primary_address
  const place = a ? `${a.postal_code} ${a.city}`.trim() : ''
  return [customer.value?.number, place].filter(Boolean).join(' · ')
})

async function load() {
  customer.value = await customersApi.get(id)
  form.value = { ...customer.value }
  markSaved()
  contacts.value = (await contactsApi.list(id)).results
  addresses.value = (await addressesApi.list(id)).results
  bankAccounts.value = (await bankAccountsApi.list()).results.filter((account) => account.is_active)
}
const loadFailed = useLoadFailed(load)

// After an address change: the list and the header's primary address, but not the master
// data form, which may hold unsaved edits.
async function reloadAddresses() {
  addresses.value = (await addressesApi.list(id)).results
  customer.value = await customersApi.get(id)
}

async function saveCustomer() {
  saving.value = true
  try {
    customer.value = await customersApi.update(id, form.value)
    markSaved()
    notify.ok(t('common.saved'))
  } catch (e) {
    notify.error(e)
  } finally {
    saving.value = false
  }
}

function openContact(contact?: Contact) {
  editingContact.value = contact ?? null
  contactForm.value = contact ? { ...contact } : { is_invoice_contact: false }
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
    notify.ok(t('common.saved'))
    contactForm.value = { is_invoice_contact: false }
    contacts.value = (await contactsApi.list(id)).results
  } catch (e) {
    notify.error(e)
  }
}

function removeContact(c: Contact) {
  confirmDelete(async () => {
    await contactsApi.remove(c.id)
    contacts.value = (await contactsApi.list(id)).results
  })
}

// The address's roles as icons (named for screen readers and in the tooltip), so the
// column stays narrow with all three set.
function addressRoles(address: Address) {
  return [
    address.is_primary && { icon: 'iconify lucide--star', label: t('customers.primary') },
    address.is_invoice_address && {
      icon: 'iconify lucide--receipt',
      label: t('customers.invoiceAddress'),
    },
    address.is_delivery_address && {
      icon: 'iconify lucide--truck',
      label: t('customers.deliveryAddress'),
    },
  ].filter((role) => role !== false)
}

function openAddress(address?: Address) {
  editingAddress.value = address ?? null
  addressForm.value = address
    ? { ...address }
    : {
        country: 'Deutschland',
        is_primary: false,
        is_invoice_address: false,
        is_delivery_address: false,
      }
  addressModal.value?.open()
}

async function saveAddress() {
  try {
    if (editingAddress.value) {
      await addressesApi.update(editingAddress.value.id, addressForm.value)
    } else {
      await addressesApi.create({ ...addressForm.value, customer: id })
    }
    addressModal.value?.close()
    notify.ok(t('common.saved'))
    addressForm.value = {
      country: 'Deutschland',
      is_primary: false,
      is_invoice_address: false,
      is_delivery_address: false,
    }
    editingAddress.value = null
    await reloadAddresses()
  } catch (e) {
    notify.error(e)
  }
}

function removeAddress(a: Address) {
  confirmDelete(async () => {
    await addressesApi.remove(a.id)
    await reloadAddresses()
  })
}
</script>

<template>
  <div v-if="customer">
    <AppPageHeader
      back-to="/customers"
      :back-label="t('nav.customers')"
      :title="customer.name"
      :subtitle="subtitle"
    >
      <template #actions>
        <Button
          :label="t('common.delete')"
          text
          severity="danger"
          @click="
            confirmDelete(async () => {
              await customersApi.remove(id)
              router.push('/customers')
            })
          "
        />
        <Button
          v-if="tab === 'overview'"
          :label="t('overview.createInvoice')"
          icon="iconify lucide--receipt"
          @click="router.push(`/invoices/new?customer=${id}`)"
        />
        <Button
          v-if="tab === 'details'"
          :label="t('common.save')"
          :loading="saving"
          @click="saveCustomer"
        />
      </template>
    </AppPageHeader>

    <Tabs v-model:value="tab">
      <TabList>
        <Tab value="overview">{{ t('overview.title') }}</Tab>
        <Tab value="details">{{ t('overview.masterData') }}</Tab>
        <Tab value="contacts">{{ t('customers.contacts') }}</Tab>
        <Tab value="addresses">{{ t('customers.addresses') }}</Tab>
        <Tab value="rates">{{ t('customers.rates') }}</Tab>
        <Tab value="attachments">{{ t('customers.attachments') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="overview">
          <RelatedOverview scope="customer" :id="id" class="pt-4" />
        </TabPanel>
        <TabPanel value="details">
          <div class="flex flex-col gap-6 max-w-3xl pt-4">
            <fieldset class="border-t border-surface-200 dark:border-surface-700 pt-4">
              <legend class="ml-4 px-2 font-medium">{{ t('customers.groups.masterData') }}</legend>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <NumberField v-model="form.number" :locked="customer?.number_locked" />
                <AppFormField field="name" :label="t('common.name')"
                  ><InputText v-model="form.name" class="w-full"
                /></AppFormField>
                <AppCheckboxField v-model="form.is_active" :label="t('customers.active')" />
                <AppFormField field="notes" :label="t('common.notes')" class="md:col-span-2"
                  ><Textarea v-model="form.notes" rows="3" class="w-full"
                /></AppFormField>
              </div>
            </fieldset>

            <fieldset class="border-t border-surface-200 dark:border-surface-700 pt-4">
              <legend class="ml-4 px-2 font-medium">{{ t('customers.groups.contact') }}</legend>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <AppFormField field="email" :label="t('common.email')"
                  ><InputText v-model="form.email" class="w-full"
                /></AppFormField>
                <AppFormField field="phone" :label="t('common.phone')"
                  ><InputText v-model="form.phone" class="w-full"
                /></AppFormField>
                <AppFormField field="website" :label="t('customers.website')" class="md:col-span-2"
                  ><InputText v-model="form.website" class="w-full"
                /></AppFormField>
              </div>
            </fieldset>

            <fieldset class="border-t border-surface-200 dark:border-surface-700 pt-4">
              <legend class="ml-4 px-2 font-medium">{{ t('customers.groups.billing') }}</legend>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <AppFormField field="vat_id" :label="t('customers.vatId')"
                  ><InputText v-model="form.vat_id" class="w-full"
                /></AppFormField>
                <AppFormField field="buyer_reference" :label="t('customers.buyerReference')"
                  ><InputText v-model="form.buyer_reference" class="w-full"
                /></AppFormField>
                <AppFormField field="payment_terms_days" :label="t('customers.paymentTerms')"
                  ><InputNumber
                    v-model="form.payment_terms_days"
                    :min="0"
                    :placeholder="t('customers.paymentTermsDefault')"
                    class="w-full"
                /></AppFormField>
                <AppFormField field="bank_account" :label="t('settings.bankAccount')"
                  ><Select
                    v-model="form.bank_account"
                    :options="bankAccounts"
                    option-label="name"
                    option-value="id"
                    show-clear
                    :placeholder="t('settings.companyDefault')"
                    class="w-full"
                /></AppFormField>
                <AppFormField field="e_invoice_format" :label="t('invoices.eInvoice')">
                  <AppEnumSelect
                    v-model="form.e_invoice_format"
                    :options="eInvoiceFormats"
                    label-prefix="invoices.eInvoiceFormats"
                    class="w-full"
                  />
                </AppFormField>
              </div>
            </fieldset>

            <fieldset class="border-t border-surface-200 dark:border-surface-700 pt-4">
              <legend class="ml-4 px-2 font-medium">
                {{ t('customers.groups.timeTracking') }}
              </legend>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <AppFormField field="rounding_increment_minutes" :label="t('customers.rounding')"
                  ><InputNumber v-model="form.rounding_increment_minutes" :min="0" class="w-full"
                /></AppFormField>
                <AppFormField field="travel_distance_km" :label="t('travel.distance')"
                  ><InputNumber
                    v-model="form.travel_distance_km"
                    :min="0"
                    :max-fraction-digits="1"
                    class="w-full"
                /></AppFormField>
              </div>
            </fieldset>
          </div>
        </TabPanel>
        <TabPanel value="contacts">
          <div class="flex justify-end pt-4 mb-2">
            <Button
              :label="t('customers.newContact')"
              icon="iconify lucide--plus"
              size="small"
              @click="openContact()"
            />
          </div>
          <AppDataTable
            :rows="contacts"
            :state-key="tableStateKeys.customerContacts"
            @row-click="openContact"
          >
            <Column class="app-text app-fill" field="last_name" :header="t('common.name')" sortable>
              <template #body="{ data }">{{ data.first_name }} {{ data.last_name }}</template>
            </Column>
            <Column class="app-text" field="role" :header="t('customers.role')" sortable />
            <Column class="app-text" field="email" :header="t('common.email')" sortable />
            <Column class="app-text" field="phone" :header="t('common.phone')" sortable />
            <Column :header="t('customers.forInvoices')">
              <template #body="{ data }"
                ><i v-if="data.is_invoice_contact" class="iconify lucide--check"
              /></template>
            </Column>
            <Column header-style="width: 5.5rem" :reorderable-column="false">
              <template #body="{ data }">
                <AppIconButton icon="iconify lucide--pencil" @click.stop="openContact(data)" />
                <AppIconButton
                  icon="iconify lucide--trash-2"
                  severity="danger"
                  @click.stop="removeContact(data)"
                />
              </template>
            </Column>
          </AppDataTable>
        </TabPanel>
        <TabPanel value="addresses">
          <div class="flex justify-end pt-4 mb-2">
            <Button
              :label="t('customers.newAddress')"
              icon="iconify lucide--plus"
              size="small"
              @click="openAddress()"
            />
          </div>
          <AppDataTable :rows="addresses" :state-key="tableStateKeys.customerAddresses">
            <Column class="app-text" field="label" :header="t('customers.addressLabel')" sortable />
            <Column
              class="app-text app-fill"
              field="street"
              :header="t('customers.street')"
              sortable
            />
            <Column
              class="app-text"
              :header="t('customers.postalCode') + ' / ' + t('customers.city')"
            >
              <template #body="{ data }">{{ data.postal_code }} {{ data.city }}</template>
            </Column>
            <Column class="app-text" field="country" :header="t('customers.country')" sortable />
            <Column :header="t('common.status')">
              <template #body="{ data }">
                <span class="inline-flex gap-2 text-primary">
                  <i
                    v-for="role in addressRoles(data)"
                    :key="role.icon"
                    :class="role.icon"
                    role="img"
                    :aria-label="role.label"
                    :title="role.label"
                  />
                </span>
              </template>
            </Column>
            <Column header-style="width: 5.5rem" :reorderable-column="false">
              <template #body="{ data }">
                <AppIconButton icon="iconify lucide--pencil" @click.stop="openAddress(data)" />
                <AppIconButton
                  icon="iconify lucide--trash-2"
                  severity="danger"
                  @click.stop="removeAddress(data)"
                />
              </template>
            </Column>
          </AppDataTable>
        </TabPanel>
        <TabPanel value="rates">
          <div class="pt-4 flex flex-col gap-8">
            <HourlyRateList :customer-id="id" />
            <TravelRateList :customer-id="id" />
          </div>
        </TabPanel>
        <TabPanel value="attachments">
          <div class="pt-4"><AttachmentList model="customer" :object-id="id" /></div>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <AppModal
      ref="contactModal"
      :form="contactForm"
      :title="editingContact ? t('customers.editContact') : t('customers.newContact')"
      @confirm="saveContact"
    >
      <div class="flex flex-col gap-4">
        <div class="grid grid-cols-2 gap-3">
          <AppFormField field="first_name" :label="t('customers.firstName')" required
            ><InputText v-model="contactForm.first_name" class="w-full"
          /></AppFormField>
          <AppFormField field="last_name" :label="t('customers.lastName')"
            ><InputText v-model="contactForm.last_name" class="w-full"
          /></AppFormField>
        </div>
        <AppFormField field="salutation_name" :label="t('customers.salutationName')">
          <!-- Empty: mails greet them with the full name, which the placeholder shows. -->
          <InputText
            v-model="contactForm.salutation_name"
            :placeholder="[contactForm.first_name, contactForm.last_name].filter(Boolean).join(' ')"
            class="w-full"
          />
        </AppFormField>
        <AppFormField field="role" :label="t('customers.role')"
          ><InputText v-model="contactForm.role" class="w-full"
        /></AppFormField>
        <AppFormField field="email" :label="t('common.email')"
          ><InputText v-model="contactForm.email" class="w-full"
        /></AppFormField>
        <AppFormField field="phone" :label="t('common.phone')"
          ><InputText v-model="contactForm.phone" class="w-full"
        /></AppFormField>
        <AppCheckboxField
          v-model="contactForm.is_invoice_contact"
          :label="t('customers.invoiceContact')"
        />
      </div>
    </AppModal>

    <AppModal
      ref="addressModal"
      :form="addressForm"
      :title="editingAddress ? t('customers.editAddress') : t('customers.newAddress')"
      @confirm="saveAddress"
    >
      <div class="flex flex-col gap-4">
        <AppFormField field="label" :label="t('customers.addressLabel')"
          ><InputText v-model="addressForm.label" class="w-full"
        /></AppFormField>
        <AppFormField field="street" :label="t('customers.street')"
          ><InputText v-model="addressForm.street" class="w-full"
        /></AppFormField>
        <div class="grid grid-cols-3 gap-3">
          <AppFormField field="postal_code" :label="t('customers.postalCode')"
            ><InputText v-model="addressForm.postal_code" class="w-full"
          /></AppFormField>
          <AppFormField field="city" :label="t('customers.city')" class="col-span-2"
            ><InputText v-model="addressForm.city" class="w-full"
          /></AppFormField>
        </div>
        <AppFormField field="country" :label="t('customers.country')"
          ><InputText v-model="addressForm.country" class="w-full"
        /></AppFormField>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <AppCheckboxField v-model="addressForm.is_primary" :label="t('customers.primary')" />
          <AppCheckboxField
            v-model="addressForm.is_invoice_address"
            :label="t('customers.invoiceAddress')"
          />
          <AppCheckboxField
            v-model="addressForm.is_delivery_address"
            :label="t('customers.deliveryAddress')"
          />
        </div>
      </div>
    </AppModal>
  </div>
  <AppLoadState v-else :failed="loadFailed" back-to="/customers" :back-label="t('nav.customers')" />
</template>
