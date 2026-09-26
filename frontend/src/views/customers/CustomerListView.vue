<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppStatusTag from '../../components/ui/AppStatusTag.vue'
import AppModal from '../../components/ui/AppModal.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppDurationDisplay from '../../components/ui/AppDurationDisplay.vue'
import { customersApi, type Customer } from '../../api'
import { useNotify } from '../../composables/useNotify'

const { t } = useI18n()
const router = useRouter()
const notify = useNotify()
const rows = ref<Customer[]>([])
const loading = ref(true)
const search = ref('')
const modal = ref<InstanceType<typeof AppModal>>()
const saving = ref(false)
const form = ref({ name: '', email: '', phone: '', street: '', postal_code: '', city: '', country: 'DE', buyer_reference: '', notes: '' })

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
      <Column field="name" :header="t('common.name')" />
      <Column field="city" :header="t('common.address')">
        <template #body="{ data }">{{ data.postal_code }} {{ data.city }}</template>
      </Column>
      <Column field="email" :header="t('common.email')" />
      <Column field="project_count" :header="t('nav.projects')" />
      <Column :header="t('customers.uninvoicedHours')">
        <template #body="{ data }"><AppDurationDisplay :minutes="(data.uninvoiced_hours ?? 0) * 60" /></template>
      </Column>
      <Column :header="t('common.status')">
        <template #body="{ data }"><AppStatusTag :status="data.is_active ? 'active' : 'cancelled'" :label="data.is_active ? t('customers.active') : '—'" /></template>
      </Column>
      <template #card="{ row }">
        <div class="font-medium">{{ row.name }}</div>
        <div class="text-sm text-surface-500">{{ row.postal_code }} {{ row.city }}</div>
      </template>
    </AppDataTable>

    <AppModal ref="modal" :title="t('customers.new')" :loading="saving" @confirm="save">
      <div class="flex flex-col gap-4">
        <AppFormField :label="t('common.name')" required><InputText v-model="form.name" class="w-full" /></AppFormField>
        <div class="grid grid-cols-2 gap-3">
          <AppFormField :label="t('common.email')"><InputText v-model="form.email" class="w-full" /></AppFormField>
          <AppFormField :label="t('common.phone')"><InputText v-model="form.phone" class="w-full" /></AppFormField>
        </div>
        <AppFormField :label="t('common.address')"><InputText v-model="form.street" class="w-full" /></AppFormField>
        <div class="grid grid-cols-3 gap-3">
          <AppFormField label="PLZ"><InputText v-model="form.postal_code" class="w-full" /></AppFormField>
          <AppFormField :label="t('common.address')" class="col-span-2"><InputText v-model="form.city" class="w-full" /></AppFormField>
        </div>
        <AppFormField :label="t('customers.buyerReference')"><InputText v-model="form.buyer_reference" class="w-full" /></AppFormField>
      </div>
    </AppModal>
  </div>
</template>
