<script setup lang="ts">
import { useTabQuery } from '../../composables/useTabQuery'
import { ref } from 'vue'
import dayjs from 'dayjs'
import { useFormattingStore } from '../../stores/formatting'
import { useLoadFailed } from '../../composables/useLoadFailed'
import { useUnsavedChanges } from '../../composables/useUnsavedChanges'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Column from 'primevue/column'
import AppLoadState from '../../components/ui/AppLoadState.vue'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppFormTabs from '../../components/ui/AppFormTabs.vue'
import VisitTravelFields from '../../components/VisitTravelFields.vue'
import AppMarkdownEditor from '../../components/ui/AppMarkdownEditor.vue'
import NumberField from '../../components/NumberField.vue'
import AppDateInput from '../../components/ui/AppDateInput.vue'
import AppDateTimeDisplay from '../../components/ui/AppDateTimeDisplay.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppIconButton from '../../components/ui/AppIconButton.vue'
import AppDurationDisplay from '../../components/ui/AppDurationDisplay.vue'
import AttachmentList from '../../components/AttachmentList.vue'
import CustomerSelect from '../../components/CustomerSelect.vue'
import ProjectSelect from '../../components/ProjectSelect.vue'
import { timeTrackingApi, visitsApi, type TimeEntry, type Visit } from '../../api'
import { useNotify } from '../../composables/useNotify'
import { useConfirmDelete } from '../../composables/useConfirmDelete'
import { tableStateKeys } from '../../tableStateKeys'

const { t } = useI18n()
const tab = useTabQuery('entries', ['entries', 'attachments'])
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
// The customer's entries of the visit's day that belong to no visit yet.
const suggested = ref<TimeEntry[]>([])
const saving = ref(false)
const linking = ref(false)

async function loadEntries() {
  if (!visit.value) return
  const day = visit.value.date
  const [linked, open] = await Promise.all([
    timeTrackingApi.list(`visit=${id}&ordering=start_datetime&page_size=500`),
    timeTrackingApi.list(
      `customer=${visit.value.customer}&visit__isnull=true&start_datetime__date__gte=${day}` +
        `&start_datetime__date__lte=${day}&ordering=start_datetime&page_size=500`,
    ),
  ])
  entries.value = linked.results
  suggested.value = open.results
}

async function load() {
  visit.value = await visitsApi.get(id)
  form.value = { ...visit.value }
  markSaved()
  await loadEntries()
}

async function setVisit(rows: TimeEntry[], visitId: string | null) {
  if (linking.value) return
  linking.value = true
  try {
    await Promise.all(rows.map((row) => timeTrackingApi.patch(row.id, { visit: visitId })))
  } catch (e) {
    notify.error(e)
  } finally {
    linking.value = false
    await loadEntries()
  }
}
const loadFailed = useLoadFailed(load)

async function save() {
  saving.value = true
  try {
    visit.value = await visitsApi.update(id, form.value)
    markSaved()
    notify.ok(t('common.saved'))
    // Another day or customer suggests other entries.
    await loadEntries()
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

    <!-- Side by side once both fit, else stacked at full width. -->
    <div class="@container">
      <div class="grid items-start gap-6 @min-[77.5rem]:grid-cols-[minmax(0,48rem)_minmax(0,1fr)]">
        <AppFormTabs :report-label="t('common.notes')" class="min-w-0">
          <template #details>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
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
              <div class="grid grid-cols-2 gap-4">
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
              <VisitTravelFields
                v-model:bill="form.bill_travel!"
                v-model:distance="form.distance_km"
                v-model:price="form.travel_price"
                :customer="form.customer"
                :project="form.project"
                :date="form.date"
                :invoice-id="visit.invoice"
                :invoice-number="visit.invoice_number"
                class="md:col-span-2"
              />
            </div>
          </template>
          <template #report="{ fill }">
            <AppMarkdownEditor
              :model-value="form.notes ?? ''"
              :rows="16"
              :label="t('common.notes')"
              :fill="fill"
              @update:model-value="(text: string) => (form.notes = text)"
            />
          </template>
        </AppFormTabs>

        <Tabs v-model:value="tab" class="min-w-0">
          <TabList>
            <Tab value="entries">{{ t('time.title') }}</Tab>
            <Tab value="attachments">{{ t('customers.attachments') }}</Tab>
          </TabList>
          <TabPanels>
            <TabPanel value="entries" class="pt-4">
              <AppDataTable :rows="entries" :state-key="tableStateKeys.visitTimeEntries">
                <Column
                  field="start_datetime"
                  :header="t('common.date')"
                  header-style="width: 9.5rem"
                  sortable
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
                <Column :reorderable-column="false">
                  <template #body="{ data }"
                    ><AppIconButton
                      icon="iconify lucide--x"
                      :label="t('visits.unlink')"
                      :title="t('visits.unlink')"
                      @click="setVisit([data], null)"
                  /></template>
                </Column>
              </AppDataTable>
              <template v-if="suggested.length">
                <div class="flex items-center justify-between mt-6 mb-2">
                  <h3 class="font-semibold">{{ t('visits.suggested') }}</h3>
                  <Button
                    :label="t('visits.linkAll')"
                    icon="iconify lucide--plus"
                    size="small"
                    text
                    :loading="linking"
                    @click="setVisit(suggested, id)"
                  />
                </div>
                <AppDataTable :rows="suggested" :state-key="tableStateKeys.visitSuggestedEntries">
                  <Column
                    field="start_datetime"
                    :header="t('common.date')"
                    header-style="width: 9.5rem"
                    ><template #body="{ data }"
                      ><AppDateTimeDisplay :value="data.start_datetime" type="datetime" /></template
                  ></Column>
                  <Column class="app-text" field="description" :header="t('time.description')" />
                  <Column class="app-num" field="duration_minutes" :header="t('time.duration')">
                    <template #body="{ data }"
                      ><AppDurationDisplay :minutes="data.duration_minutes"
                    /></template>
                  </Column>
                  <Column :reorderable-column="false">
                    <template #body="{ data }"
                      ><AppIconButton
                        icon="iconify lucide--plus"
                        :label="t('visits.link')"
                        :title="t('visits.link')"
                        @click="setVisit([data], id)"
                    /></template>
                  </Column>
                </AppDataTable>
              </template>
            </TabPanel>
            <TabPanel value="attachments" class="pt-4"
              ><AttachmentList model="onsitevisit" :object-id="id"
            /></TabPanel>
          </TabPanels>
        </Tabs>
      </div>
    </div>
  </div>
  <AppLoadState v-else :failed="loadFailed" back-to="/visits" :back-label="t('nav.visits')" />
</template>
