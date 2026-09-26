<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppModal from '../../components/ui/AppModal.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppDateInput from '../../components/ui/AppDateInput.vue'
import AppDateTimeDisplay from '../../components/ui/AppDateTimeDisplay.vue'
import CustomerSelect from '../../components/CustomerSelect.vue'
import ProjectSelect from '../../components/ProjectSelect.vue'
import { visitsApi, type Visit } from '../../api'
import { useNotify } from '../../composables/useNotify'

const { t } = useI18n()
const router = useRouter()
const notify = useNotify()
const rows = ref<Visit[]>([])
const loading = ref(true)
const modal = ref<InstanceType<typeof AppModal>>()
const saving = ref(false)
const form = ref<Partial<Visit>>({ date: new Date().toISOString().slice(0, 10) })

async function load() {
  loading.value = true
  rows.value = (await visitsApi.list('ordering=-date&page_size=500')).results
  loading.value = false
}
onMounted(load)

async function save() {
  saving.value = true
  try {
    await visitsApi.create(form.value)
    modal.value?.close()
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
    <AppPageHeader :title="t('visits.title')">
      <template #actions>
        <Button :label="t('visits.new')" icon="pi pi-plus" @click="form = { date: new Date().toISOString().slice(0, 10) }; modal?.open()" />
      </template>
    </AppPageHeader>

    <AppDataTable :rows="rows" :loading="loading" @row-click="(r: Visit) => router.push(`/visits/${r.id}`)">
      <Column field="number" header="#" />
      <Column :header="t('common.date')"><template #body="{ data }"><AppDateTimeDisplay :value="data.date" /></template></Column>
      <Column field="customer_name" :header="t('projects.customer')" />
      <Column field="project_name" :header="t('nav.projects')" />
      <Column field="location" :header="t('visits.location')" />
      <template #card="{ row }">
        <div class="font-medium">{{ row.customer_name }}</div>
        <div class="text-sm text-surface-500"><AppDateTimeDisplay :value="row.date" /> · {{ row.location }}</div>
      </template>
    </AppDataTable>

    <AppModal ref="modal" :title="t('visits.new')" :loading="saving" @confirm="save">
      <div class="flex flex-col gap-4">
        <AppFormField :label="t('projects.customer')" required><CustomerSelect v-model="form.customer" /></AppFormField>
        <AppFormField :label="t('nav.projects')"><ProjectSelect v-model="form.project" :customer-id="form.customer" /></AppFormField>
        <div class="grid grid-cols-3 gap-3">
          <AppFormField :label="t('common.date')" required><AppDateInput v-model="(form.date as any)" /></AppFormField>
          <AppFormField :label="t('visits.arrival')"><InputText v-model="form.arrival" type="time" class="w-full" /></AppFormField>
          <AppFormField :label="t('visits.departure')"><InputText v-model="form.departure" type="time" class="w-full" /></AppFormField>
        </div>
        <AppFormField :label="t('visits.location')"><InputText v-model="form.location" class="w-full" /></AppFormField>
        <AppFormField :label="t('common.notes')"><Textarea v-model="form.notes" rows="3" class="w-full" /></AppFormField>
      </div>
    </AppModal>
  </div>
</template>
