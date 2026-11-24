<script setup lang="ts">
import { ref } from 'vue'
import dayjs from 'dayjs'
import { useFormattingStore } from '../../stores/formatting'
import { useLoadFailed } from '../../composables/useLoadFailed'
import { useUnsavedChanges } from '../../composables/useUnsavedChanges'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Column from 'primevue/column'
import AppLoadState from '../../components/ui/AppLoadState.vue'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import NumberField from '../../components/NumberField.vue'
import AppDateInput from '../../components/ui/AppDateInput.vue'
import AppDateTimeDisplay from '../../components/ui/AppDateTimeDisplay.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppDurationDisplay from '../../components/ui/AppDurationDisplay.vue'
import AttachmentList from '../../components/AttachmentList.vue'
import CustomerSelect from '../../components/CustomerSelect.vue'
import ProjectSelect from '../../components/ProjectSelect.vue'
import { timeTrackingApi, visitsApi, type TimeEntry, type Visit } from '../../api'
import { useNotify } from '../../composables/useNotify'
import { useConfirmDelete } from '../../composables/useConfirmDelete'
import { tableStateKeys } from '../../tableStateKeys'

const { t } = useI18n()
const formatting = useFormattingStore()
const route = useRoute()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const id = route.params.id as string
const visit = ref<Visit | null>(null)
const form = ref<Partial<Visit>>({})
const { markSaved } = useUnsavedChanges(form)
const entries = ref<TimeEntry[]>([])
const saving = ref(false)

async function load() {
  visit.value = await visitsApi.get(id)
  form.value = { ...visit.value }
  markSaved()
  entries.value = (await timeTrackingApi.list(`visit=${id}&page_size=500`)).results
}
const loadFailed = useLoadFailed(load)

async function save() {
  saving.value = true
  try {
    visit.value = await visitsApi.update(id, form.value)
    markSaved()
    notify.ok(t('common.saved'))
  } catch (e) {
    notify.error(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div v-if="visit">
    <AppPageHeader
      back-to="/visits"
      :back-label="t('nav.visits')"
      :title="`${visit.customer_name} — ${dayjs(visit.date).format(formatting.dateFormat)}`"
      :subtitle="[visit.number, visit.location].filter(Boolean).join(' · ')"
    >
      <template #actions>
        <Button
          :label="t('common.delete')"
          text
          severity="danger"
          @click="
            confirmDelete(async () => {
              await visitsApi.remove(id)
              router.push('/visits')
            })
          "
        />
        <Button :label="t('common.save')" :loading="saving" @click="save" />
      </template>
    </AppPageHeader>

    <div class="flex flex-wrap items-start gap-6">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl flex-[1_1_48rem]">
        <NumberField v-model="form.number" />
        <AppFormField field="customer" :label="t('projects.customer')"
          ><CustomerSelect v-model="form.customer"
        /></AppFormField>
        <AppFormField field="project" :label="t('projects.project')"
          ><ProjectSelect v-model="form.project" :customer-id="form.customer"
        /></AppFormField>
        <AppFormField field="date" :label="t('common.date')"
          ><AppDateInput v-model="form.date as any"
        /></AppFormField>
        <AppFormField field="location" :label="t('visits.location')"
          ><InputText v-model="form.location" class="w-full"
        /></AppFormField>
        <AppFormField field="arrival" :label="t('visits.arrival')"
          ><InputText v-model="form.arrival" type="time" class="w-full"
        /></AppFormField>
        <AppFormField field="departure" :label="t('visits.departure')"
          ><InputText v-model="form.departure" type="time" class="w-full"
        /></AppFormField>
        <AppFormField field="notes" :label="t('visits.report')" class="md:col-span-2"
          ><Textarea v-model="form.notes" rows="6" class="w-full"
        /></AppFormField>
      </div>

      <Tabs value="entries" class="min-w-0 flex-[1_1_28rem]">
        <TabList>
          <Tab value="entries">{{ t('time.title') }}</Tab>
          <Tab value="attachments">{{ t('customers.attachments') }}</Tab>
        </TabList>
        <TabPanels>
          <TabPanel value="entries" class="pt-4">
            <AppDataTable :rows="entries" :state-key="tableStateKeys.visitTimeEntries">
              <Column field="start_datetime" :header="t('common.date')" sortable
                ><template #body="{ data }"
                  ><AppDateTimeDisplay :value="data.start_datetime" type="datetime" /></template
              ></Column>
              <Column
                class="app-text"
                field="description"
                :header="t('time.description')"
                sortable
              />
              <Column
                class="app-num"
                field="duration_minutes"
                :header="t('time.duration')"
                sortable
              >
                <template #body="{ data }"
                  ><AppDurationDisplay :minutes="data.duration_minutes"
                /></template>
              </Column>
            </AppDataTable>
          </TabPanel>
          <TabPanel value="attachments" class="pt-4"
            ><AttachmentList model="onsitevisit" :object-id="id"
          /></TabPanel>
        </TabPanels>
      </Tabs>
    </div>
  </div>
  <AppLoadState v-else :failed="loadFailed" back-to="/visits" :back-label="t('nav.visits')" />
</template>
