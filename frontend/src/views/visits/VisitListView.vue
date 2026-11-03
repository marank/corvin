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
import AppIconButton from '../../components/ui/AppIconButton.vue'
import AppModal from '../../components/ui/AppModal.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppDateInput from '../../components/ui/AppDateInput.vue'
import AppDateTimeDisplay from '../../components/ui/AppDateTimeDisplay.vue'
import CustomerSelect from '../../components/CustomerSelect.vue'
import ProjectSelect from '../../components/ProjectSelect.vue'
import { visitsApi, type Visit } from '../../api'
import { useNotify } from '../../composables/useNotify'
import { useConfirmDelete } from '../../composables/useConfirmDelete'
import { usePagination } from '../../composables/usePagination'
import { tableStateKeys } from '../../tableStateKeys'

const { t } = useI18n()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const rows = ref<Visit[]>([])
const modal = ref<InstanceType<typeof AppModal>>()
const saving = ref(false)
const form = ref<Partial<Visit>>({ date: new Date().toISOString().slice(0, 10) })
const pagination = usePagination(load, '-date')
const sortOptions = [
  { label: '#', value: 'number' },
  { label: t('common.date'), value: 'date' },
  { label: t('projects.customer'), value: 'customer__name' },
  { label: t('nav.projects'), value: 'project__name' },
  { label: t('visits.location'), value: 'location' },
]

onMounted(pagination.start)

async function load() {
  const results = await pagination.fetchPage(visitsApi.list)
  if (results) rows.value = results
}

async function save() {
  saving.value = true
  try {
    await visitsApi.create(form.value)
    modal.value?.close()
    form.value = { date: new Date().toISOString().slice(0, 10) }
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

    <AppDataTable
      :rows="rows" :loading="pagination.loading.value" lazy selectable
      :total-records="pagination.totalRecords.value" :first="pagination.first.value"
      :page-size="pagination.pageSize.value" :sort-field="pagination.sortField.value"
      :sort-order="pagination.sortOrder.value" :sort-options="sortOptions"
      :state-key="tableStateKeys.visits" @state-restore="pagination.onRestore" @page="pagination.onPage" @sort="pagination.onSort"
      @row-click="(r: Visit) => router.push(`/visits/${r.id}`)"
    >
      <Column field="number" header="#" sortable />
      <Column field="date" :header="t('common.date')" sortable><template #body="{ data }"><AppDateTimeDisplay :value="data.date" /></template></Column>
      <Column field="customer_name" sort-field="customer__name" :header="t('projects.customer')" sortable />
      <Column field="project_name" sort-field="project__name" :header="t('nav.projects')" sortable />
      <Column field="location" :header="t('visits.location')" sortable />
      <Column :header="t('common.actions')" :reorderable-column="false">
        <template #body="{ data }"><AppIconButton icon="pi pi-trash" severity="danger" @click.stop="confirmDelete(async () => { await visitsApi.remove(data.id); load() })" /></template>
      </Column>
      <template #card="{ row }">
        <div class="font-medium">{{ row.customer_name }}</div>
        <div class="text-sm text-surface-500"><AppDateTimeDisplay :value="row.date" /> · {{ row.location }}</div>
      </template>
    </AppDataTable>

    <AppModal ref="modal" :title="t('visits.new')" :loading="saving" @confirm="save">
      <div class="flex flex-col gap-4">
        <AppFormField field="customer" :label="t('projects.customer')" required><CustomerSelect v-model="form.customer" /></AppFormField>
        <AppFormField field="project" :label="t('nav.projects')"><ProjectSelect v-model="form.project" :customer-id="form.customer" /></AppFormField>
        <div class="grid grid-cols-3 gap-3">
          <AppFormField field="date" :label="t('common.date')" required><AppDateInput v-model="(form.date as any)" /></AppFormField>
          <AppFormField field="arrival" :label="t('visits.arrival')"><InputText v-model="form.arrival" type="time" class="w-full" /></AppFormField>
          <AppFormField field="departure" :label="t('visits.departure')"><InputText v-model="form.departure" type="time" class="w-full" /></AppFormField>
        </div>
        <AppFormField field="location" :label="t('visits.location')"><InputText v-model="form.location" class="w-full" /></AppFormField>
        <AppFormField field="notes" :label="t('common.notes')"><Textarea v-model="form.notes" rows="3" class="w-full" /></AppFormField>
      </div>
    </AppModal>
  </div>
</template>
