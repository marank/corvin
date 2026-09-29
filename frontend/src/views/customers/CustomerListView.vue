<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import AppIconButton from '../../components/ui/AppIconButton.vue'
import InputNumber from 'primevue/inputnumber'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppStatusTag from '../../components/ui/AppStatusTag.vue'
import AppModal from '../../components/ui/AppModal.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppDurationDisplay from '../../components/ui/AppDurationDisplay.vue'
import { customersApi, type Customer } from '../../api'
import { useNotify } from '../../composables/useNotify'
import { useConfirmDelete } from '../../composables/useConfirmDelete'

const { t } = useI18n()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const rows = ref<Customer[]>([])
const loading = ref(true)
const search = ref('')
const modal = ref<InstanceType<typeof AppModal>>()
const saving = ref(false)
const form = ref({ name: '', email: '', phone: '', website: '', vat_id: '', buyer_reference: '', payment_terms_days: null as number | null, notes: '' })

async function load() {
  loading.value = true
  rows.value = (await customersApi.list(`search=${search.value}&page_size=200`)).results
  loading.value = false
}
onMounted(load)

async function save() {
  saving.value = true
  try {
    await customersApi.create(form.value)
    modal.value?.close()
    form.value = { name: '', email: '', phone: '', website: '', vat_id: '', buyer_reference: '', payment_terms_days: null, notes: '' }
    notify.ok(t('customers.new'))
    load()
  } catch (e) {
    notify.error(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <AppPageHeader :title="t('customers.title')">
      <template #actions>
        <InputText v-model="search" :placeholder="t('common.search')" class="w-48" @input="load" />
        <Button :label="t('customers.new')" icon="pi pi-plus" @click="modal?.open()" />
      </template>
    </AppPageHeader>

    <AppDataTable :rows="rows" :loading="loading" @row-click="(r: Customer) => router.push(`/customers/${r.id}`)">
      <Column field="number" header="#" />
      <Column field="name" :header="t('common.name')" />
      <Column :header="t('common.address')">
        <template #body="{ data }">{{ data.primary_address ? `${data.primary_address.postal_code} ${data.primary_address.city}` : '—' }}</template>
      </Column>
      <Column field="email" :header="t('common.email')" />
      <Column field="project_count" :header="t('nav.projects')" />
      <Column :header="t('customers.uninvoicedHours')">
        <template #body="{ data }"><AppDurationDisplay :minutes="(data.uninvoiced_hours ?? 0) * 60" /></template>
      </Column>
      <Column :header="t('common.status')">
        <template #body="{ data }"><AppStatusTag :status="data.is_active ? 'active' : 'cancelled'" :label="data.is_active ? t('customers.active') : '—'" /></template>
      </Column>
      <Column :header="t('common.actions')">
        <template #body="{ data }"><AppIconButton icon="pi pi-trash" severity="danger" @click.stop="confirmDelete(async () => { await customersApi.remove(data.id); load() })" /></template>
      </Column>
      <template #card="{ row }">
        <div class="font-medium">{{ row.name }}</div>
        <div class="text-sm text-surface-500">{{ row.primary_address ? `${row.primary_address.postal_code} ${row.primary_address.city}` : '' }}</div>
      </template>
    </AppDataTable>

    <AppModal ref="modal" :title="t('customers.new')" :loading="saving" @confirm="save">
      <div class="flex flex-col gap-4">
        <AppFormField :label="t('common.name')" required><InputText v-model="form.name" class="w-full" /></AppFormField>
        <div class="grid grid-cols-2 gap-3">
          <AppFormField :label="t('common.email')"><InputText v-model="form.email" class="w-full" /></AppFormField>
          <AppFormField :label="t('common.phone')"><InputText v-model="form.phone" class="w-full" /></AppFormField>
        </div>
        <AppFormField :label="t('customers.website')"><InputText v-model="form.website" class="w-full" /></AppFormField>
        <AppFormField :label="t('customers.vatId')"><InputText v-model="form.vat_id" class="w-full" /></AppFormField>
        <AppFormField :label="t('customers.buyerReference')"><InputText v-model="form.buyer_reference" class="w-full" /></AppFormField>
        <AppFormField :label="t('customers.paymentTerms')"><InputNumber v-model="form.payment_terms_days" :min="0" :placeholder="t('customers.paymentTermsDefault')" class="w-full" /></AppFormField>
      </div>
    </AppModal>
  </div>
</template>
