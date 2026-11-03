<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
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
import { usePagination } from '../../composables/usePagination'
import { tableStateKeys } from '../../tableStateKeys'

const { t } = useI18n()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const rows = ref<Customer[]>([])
const search = ref('')
const modal = ref<InstanceType<typeof AppModal>>()
const saving = ref(false)
const form = ref({ name: '', email: '', phone: '', website: '', vat_id: '', buyer_reference: '', payment_terms_days: null as number | null, notes: '' })
const pagination = usePagination(load, 'name')
const sortOptions = [
  { label: '#', value: 'number' },
  { label: t('common.name'), value: 'name' },
  { label: t('common.email'), value: 'email' },
  { label: t('nav.projects'), value: 'project_count' },
  { label: t('customers.uninvoicedHours'), value: 'uninvoiced_hours' },
]
let searchTimer: ReturnType<typeof setTimeout> | undefined

onMounted(pagination.start)
onBeforeUnmount(() => clearTimeout(searchTimer))

async function load() {
  const params = new URLSearchParams()
  if (search.value.trim()) params.set('search', search.value.trim())
  const results = await pagination.fetchPage(customersApi.list, params)
  if (results) rows.value = results
}

function searchChanged() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(pagination.refresh, 300)
}

async function save() {
  saving.value = true
  try {
    await customersApi.create(form.value)
    modal.value?.close()
    form.value = { name: '', email: '', phone: '', website: '', vat_id: '', buyer_reference: '', payment_terms_days: null, notes: '' }
    notify.ok(t('common.created'))
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
        <InputText v-model="search" :placeholder="t('common.search')" class="w-48" @input="searchChanged" />
        <Button :label="t('customers.new')" icon="pi pi-plus" @click="modal?.open()" />
      </template>
    </AppPageHeader>

    <AppDataTable
      :rows="rows"
      :loading="pagination.loading.value"
      lazy
      selectable
      :total-records="pagination.totalRecords.value"
      :first="pagination.first.value"
      :page-size="pagination.pageSize.value"
      :sort-field="pagination.sortField.value"
      :sort-order="pagination.sortOrder.value"
      :sort-options="sortOptions"
      :state-key="tableStateKeys.customers"
      @state-restore="pagination.onRestore"
      @page="pagination.onPage"
      @sort="pagination.onSort"
      @row-click="(r: Customer) => router.push(`/customers/${r.id}`)"
    >
      <Column field="number" header="#" sortable />
      <Column field="name" :header="t('common.name')" sortable />
      <Column :header="t('common.address')">
        <template #body="{ data }">{{ data.primary_address ? `${data.primary_address.postal_code} ${data.primary_address.city}` : '—' }}</template>
      </Column>
      <Column field="email" :header="t('common.email')" sortable />
      <Column field="project_count" :header="t('nav.projects')" sortable />
      <Column field="uninvoiced_hours" :header="t('customers.uninvoicedHours')" sortable>
        <template #body="{ data }"><AppDurationDisplay :minutes="(data.uninvoiced_hours ?? 0) * 60" /></template>
      </Column>
      <Column :header="t('common.status')">
        <template #body="{ data }"><AppStatusTag :status="data.is_active ? 'active' : 'inactive'" :label="data.is_active ? t('common.active') : t('common.inactive')" /></template>
      </Column>
      <Column :header="t('common.actions')" :reorderable-column="false">
        <template #body="{ data }"><AppIconButton icon="pi pi-trash" severity="danger" @click.stop="confirmDelete(async () => { await customersApi.remove(data.id); load() })" /></template>
      </Column>
      <template #card="{ row }">
        <div class="font-medium">{{ row.name }}</div>
        <div class="text-sm text-surface-500">{{ row.primary_address ? `${row.primary_address.postal_code} ${row.primary_address.city}` : '' }}</div>
      </template>
    </AppDataTable>

    <AppModal ref="modal" :title="t('customers.new')" :loading="saving" @confirm="save">
      <div class="flex flex-col gap-4">
        <AppFormField field="name" :label="t('common.name')" required><InputText v-model="form.name" class="w-full" /></AppFormField>
        <div class="grid grid-cols-2 gap-3">
          <AppFormField field="email" :label="t('common.email')"><InputText v-model="form.email" class="w-full" /></AppFormField>
          <AppFormField field="phone" :label="t('common.phone')"><InputText v-model="form.phone" class="w-full" /></AppFormField>
        </div>
        <AppFormField field="website" :label="t('customers.website')"><InputText v-model="form.website" class="w-full" /></AppFormField>
        <AppFormField field="vat_id" :label="t('customers.vatId')"><InputText v-model="form.vat_id" class="w-full" /></AppFormField>
        <AppFormField field="buyer_reference" :label="t('customers.buyerReference')"><InputText v-model="form.buyer_reference" class="w-full" /></AppFormField>
        <AppFormField field="payment_terms_days" :label="t('customers.paymentTerms')"><InputNumber v-model="form.payment_terms_days" :min="0" :placeholder="t('customers.paymentTermsDefault')" class="w-full" /></AppFormField>
      </div>
    </AppModal>
  </div>
</template>
