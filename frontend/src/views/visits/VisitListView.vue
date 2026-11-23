<script setup lang="ts">
import { isoDate } from '../../dateTimeInput'
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppFilterBar, { type ActiveFilter } from '../../components/ui/AppFilterBar.vue'
import AppSearchInput from '../../components/ui/AppSearchInput.vue'
import { useQueryFilters } from '../../composables/useQueryFilters'
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
const form = ref<Partial<Visit>>({ date: isoDate() })

function openNew() {
  form.value = { date: isoDate() }
  modal.value?.open()
}
const preset = useQueryFilters()
const names = preset.names
const search = ref('')
const filters = ref({ customer: preset.customer, project: preset.project })
const activeFilters = computed<ActiveFilter[]>(() => {
  const f = filters.value
  const active: ActiveFilter[] = []
  if (f.customer)
    active.push({ key: 'customer', label: t('projects.customer'), value: names.value.customer })
  if (f.project)
    active.push({ key: 'project', label: t('projects.project'), value: names.value.project })
  return active
})
const pagination = usePagination(load, '-date')
const sortOptions = [
  { label: '#', value: 'number' },
  { label: t('common.date'), value: 'date' },
  { label: t('projects.customer'), value: 'customer__name' },
  { label: t('projects.project'), value: 'project__name' },
  { label: t('visits.location'), value: 'location' },
]

onMounted(pagination.start)
watch([search, filters], () => pagination.refresh(), { deep: true })

async function load() {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters.value)) if (value) params.set(key, value)
  if (search.value) params.set('search', search.value)
  const results = await pagination.fetchPage(visitsApi.list, params)
  if (results) rows.value = results
}

async function save() {
  saving.value = true
  try {
    await visitsApi.create(form.value)
    modal.value?.close()
    notify.ok(t('common.created'))
    form.value = { date: isoDate() }
    void load()
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
        <Button :label="t('visits.new')" icon="pi pi-plus" @click="openNew" />
      </template>
    </AppPageHeader>

    <AppDataTable
      :rows="rows"
      :loading="pagination.loading.value"
      lazy
      selectable
      :delete-row="(row) => visitsApi.remove(row.id)"
      @bulk-deleted="load"
      :total-records="pagination.totalRecords.value"
      :first="pagination.first.value"
      :page-size="pagination.pageSize.value"
      :sort-field="pagination.sortField.value"
      :sort-order="pagination.sortOrder.value"
      :sort-options="sortOptions"
      :state-key="tableStateKeys.visits"
      @state-restore="pagination.onRestore"
      @page="pagination.onPage"
      @sort="pagination.onSort"
      @row-click="(r: Visit) => router.push(`/visits/${r.id}`)"
    >
      <template #toolbar>
        <AppFilterBar
          :active="activeFilters"
          @remove="(key) => (filters[key as 'customer' | 'project'] = null)"
          @clear="filters = { customer: null, project: null }"
        >
          <AppFormField :label="t('projects.customer')">
            <CustomerSelect
              v-model="filters.customer"
              :placeholder="t('common.allCustomers')"
              @select="(c) => (names.customer = c?.name ?? '')"
            />
          </AppFormField>
          <AppFormField :label="t('projects.project')">
            <ProjectSelect
              v-model="filters.project"
              :customer-id="filters.customer"
              :placeholder="t('common.allProjects')"
              @select="(p) => (names.project = p?.name ?? '')"
            />
          </AppFormField>
          <template #end><AppSearchInput v-model="search" /></template>
        </AppFilterBar>
      </template>
      <Column field="number" :header="t('common.numberShort')" sortable />
      <Column field="date" :header="t('common.date')" sortable
        ><template #body="{ data }"><AppDateTimeDisplay :value="data.date" /></template
      ></Column>
      <Column
        class="app-text"
        field="customer_name"
        sort-field="customer__name"
        :header="t('projects.customer')"
        sortable
      />
      <Column
        class="app-text"
        field="project_name"
        sort-field="project__name"
        :header="t('projects.project')"
        sortable
      />
      <Column class="app-text" field="location" :header="t('visits.location')" sortable />
      <Column :header="t('common.actions')" :reorderable-column="false">
        <template #body="{ data }"
          ><AppIconButton
            icon="pi pi-trash"
            severity="danger"
            @click.stop="
              confirmDelete(async () => {
                await visitsApi.remove(data.id)
                load()
              })
            "
        /></template>
      </Column>
      <template #card="{ row }">
        <div class="font-medium">{{ row.customer_name }}</div>
        <div class="text-sm text-surface-500">
          <AppDateTimeDisplay :value="row.date" /> · {{ row.location }}
        </div>
      </template>
    </AppDataTable>

    <AppModal ref="modal" :form="form" :title="t('visits.new')" :loading="saving" @confirm="save">
      <div class="flex flex-col gap-4">
        <AppFormField field="customer" :label="t('projects.customer')" required
          ><CustomerSelect v-model="form.customer"
        /></AppFormField>
        <AppFormField field="project" :label="t('projects.project')"
          ><ProjectSelect v-model="form.project" :customer-id="form.customer"
        /></AppFormField>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <AppFormField field="date" :label="t('common.date')" required
            ><AppDateInput v-model="form.date as any"
          /></AppFormField>
          <AppFormField field="arrival" :label="t('visits.arrival')"
            ><InputText v-model="form.arrival" type="time" class="w-full"
          /></AppFormField>
          <AppFormField field="departure" :label="t('visits.departure')"
            ><InputText v-model="form.departure" type="time" class="w-full"
          /></AppFormField>
        </div>
        <AppFormField field="location" :label="t('visits.location')"
          ><InputText v-model="form.location" class="w-full"
        /></AppFormField>
        <AppFormField field="notes" :label="t('common.notes')"
          ><Textarea v-model="form.notes" rows="3" class="w-full"
        /></AppFormField>
      </div>
    </AppModal>
  </div>
</template>
