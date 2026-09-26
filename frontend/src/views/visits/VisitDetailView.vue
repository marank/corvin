<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Column from 'primevue/column'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppDateInput from '../../components/ui/AppDateInput.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppDurationDisplay from '../../components/ui/AppDurationDisplay.vue'
import AttachmentList from '../../components/AttachmentList.vue'
import CustomerSelect from '../../components/CustomerSelect.vue'
import ProjectSelect from '../../components/ProjectSelect.vue'
import { timeEntriesApi, visitsApi, type TimeEntry, type Visit } from '../../api'
import { useNotify } from '../../composables/useNotify'

const { t } = useI18n()
const route = useRoute()
const notify = useNotify()
const id = Number(route.params.id)
const visit = ref<Visit | null>(null)
const form = ref<Partial<Visit>>({})
const entries = ref<TimeEntry[]>([])
const saving = ref(false)

async function load() {
  visit.value = await visitsApi.get(id)
  form.value = { ...visit.value }
  entries.value = (await timeEntriesApi.list(`visit=${id}&page_size=200`)).results
}
onMounted(load)

async function save() {
  saving.value = true
  try {
    visit.value = await visitsApi.update(id, form.value)
    notify.ok(t('common.save'))
  } catch (e) {
    notify.error(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div v-if="visit">
    <AppPageHeader :title="`${visit.customer_name} — ${visit.date}`" :subtitle="visit.location">
      <template #actions><Button :label="t('common.save')" :loading="saving" @click="save" /></template>
    </AppPageHeader>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl">
      <AppFormField :label="t('projects.customer')"><CustomerSelect v-model="form.customer" /></AppFormField>
      <AppFormField :label="t('nav.projects')"><ProjectSelect v-model="form.project" :customer-id="form.customer" /></AppFormField>
      <AppFormField :label="t('common.date')"><AppDateInput v-model="(form.date as any)" /></AppFormField>
      <AppFormField :label="t('visits.location')"><InputText v-model="form.location" class="w-full" /></AppFormField>
      <AppFormField :label="t('visits.arrival')"><InputText v-model="form.arrival" type="time" class="w-full" /></AppFormField>
      <AppFormField :label="t('visits.departure')"><InputText v-model="form.departure" type="time" class="w-full" /></AppFormField>
      <AppFormField :label="t('visits.report')" class="md:col-span-2"><Textarea v-model="form.notes" rows="6" class="w-full" /></AppFormField>
    </div>

    <Tabs value="entries" class="mt-6">
      <TabList>
        <Tab value="entries">{{ t('time.title') }}</Tab>
        <Tab value="attachments">{{ t('customers.attachments') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="entries">
          <AppDataTable :rows="entries">
            <Column field="date" :header="t('common.date')" />
            <Column field="description" :header="t('time.description')" />
            <Column :header="t('time.duration')">
              <template #body="{ data }"><AppDurationDisplay :minutes="data.duration_minutes" /></template>
            </Column>
          </AppDataTable>
        </TabPanel>
        <TabPanel value="attachments"><AttachmentList model="onsitevisit" :object-id="id" /></TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>
