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
import Textarea from 'primevue/textarea'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppModal from '../../components/ui/AppModal.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppDateInput from '../../components/ui/AppDateInput.vue'
import AppMoneyDisplay from '../../components/ui/AppMoneyDisplay.vue'
import AttachmentList from '../../components/AttachmentList.vue'
import {
  contactsApi, customersApi, ratesApi,
  type Contact, type Customer, type HourlyRate,
} from '../../api'
import { useNotify } from '../../composables/useNotify'

const { t } = useI18n()
const route = useRoute()
const notify = useNotify()
const id = Number(route.params.id)

const customer = ref<Customer | null>(null)
const contacts = ref<Contact[]>([])
const rates = ref<HourlyRate[]>([])
const saving = ref(false)

const form = ref<Partial<Customer>>({})
const contactModal = ref<InstanceType<typeof AppModal>>()
const rateModal = ref<InstanceType<typeof AppModal>>()
const contactForm = ref<Partial<Contact>>({})
const rateForm = ref<Partial<HourlyRate>>({ amount: 0, valid_from: '', valid_to: null })

const contentTypeId = computed(() => 'customer')

async function load() {
  customer.value = await customersApi.get(id)
  form.value = { ...customer.value }
  contacts.value = (await contactsApi.list(id)).results
  rates.value = (await ratesApi.list(`customer=${id}&page_size=100`)).results
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

async function saveContact() {
  try {
    await contactsApi.create({ ...contactForm.value, customer: id })
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
    <AppPageHeader :title="customer.name" :subtitle="`${customer.postal_code} ${customer.city}`">
      <template #actions>
        <Button :label="t('common.save')" :loading="saving" @click="saveCustomer" />
      </template>
    </AppPageHeader>

    <Tabs value="details">
      <TabList>
        <Tab value="details">{{ t('settings.profile') }}</Tab>
        <Tab value="contacts">{{ t('customers.contacts') }}</Tab>
        <Tab value="rates">{{ t('customers.rates') }}</Tab>
        <Tab value="attachments">{{ t('customers.attachments') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="details">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl pt-4">
            <AppFormField :label="t('common.name')"><InputText v-model="form.name" class="w-full" /></AppFormField>
            <AppFormField :label="t('customers.buyerReference')"><InputText v-model="form.buyer_reference" class="w-full" /></AppFormField>
            <AppFormField :label="t('common.email')"><InputText v-model="form.email" class="w-full" /></AppFormField>
            <AppFormField :label="t('common.phone')"><InputText v-model="form.phone" class="w-full" /></AppFormField>
            <AppFormField :label="t('common.address')" class="md:col-span-2"><InputText v-model="form.street" class="w-full" /></AppFormField>
            <AppFormField label="PLZ"><InputText v-model="form.postal_code" class="w-full" /></AppFormField>
            <AppFormField :label="t('common.address')"><InputText v-model="form.city" class="w-full" /></AppFormField>
            <AppFormField :label="t('customers.rounding')"><InputNumber v-model="form.rounding_increment_minutes" :min="0" class="w-full" /></AppFormField>
            <label class="flex items-center gap-2 text-sm md:col-span-2">
              <Checkbox v-model="form.is_active" binary /> {{ t('customers.active') }}
            </label>
            <AppFormField :label="t('common.notes')" class="md:col-span-2"><Textarea v-model="form.notes" rows="3" class="w-full" /></AppFormField>
          </div>
        </TabPanel>
        <TabPanel value="contacts">
          <div class="flex justify-end pt-4 mb-2">
            <Button :label="t('common.new')" icon="pi pi-plus" size="small" @click="contactForm = {}; contactModal?.open()" />
          </div>
          <AppDataTable :rows="contacts">
            <Column field="name" :header="t('common.name')" />
            <Column field="role" :header="t('customers.role')" />
            <Column field="email" :header="t('common.email')" />
            <Column field="phone" :header="t('common.phone')" />
            <Column :header="t('common.actions')">
              <template #body="{ data }"><Button icon="pi pi-trash" text size="small" severity="danger" @click.stop="removeContact(data)" /></template>
            </Column>
          </AppDataTable>
        </TabPanel>
        <TabPanel value="rates">
          <div class="flex justify-end pt-4 mb-2">
            <Button :label="t('common.new')" icon="pi pi-plus" size="small" @click="rateForm = { amount: 0, valid_from: '', valid_to: null }; rateModal?.open()" />
          </div>
          <AppDataTable :rows="rates">
            <Column field="valid_from" :header="t('common.date')" />
            <Column :header="t('invoices.unitPrice')">
              <template #body="{ data }"><AppMoneyDisplay :amount="data.amount" />/h</template>
            </Column>
            <Column field="valid_to" :header="t('time.end')">
              <template #body="{ data }">{{ data.valid_to ?? '—' }}</template>
            </Column>
          </AppDataTable>
        </TabPanel>
        <TabPanel value="attachments">
          <div class="pt-4"><AttachmentList :model="contentTypeId" :object-id="id" /></div>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <AppModal ref="contactModal" :title="t('customers.contacts')" @confirm="saveContact">
      <div class="flex flex-col gap-4">
        <AppFormField :label="t('common.name')" required><InputText v-model="contactForm.name" class="w-full" /></AppFormField>
        <AppFormField :label="t('customers.role')"><InputText v-model="contactForm.role" class="w-full" /></AppFormField>
        <AppFormField :label="t('common.email')"><InputText v-model="contactForm.email" class="w-full" /></AppFormField>
        <AppFormField :label="t('common.phone')"><InputText v-model="contactForm.phone" class="w-full" /></AppFormField>
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
