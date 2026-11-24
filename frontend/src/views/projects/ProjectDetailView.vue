<script setup lang="ts">
import AppEnumSelect from '../../components/ui/AppEnumSelect.vue'
import { ref } from 'vue'
import { useLoadFailed } from '../../composables/useLoadFailed'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import ProgressBar from 'primevue/progressbar'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import AppLoadState from '../../components/ui/AppLoadState.vue'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import NumberField from '../../components/NumberField.vue'
import AppMoneyDisplay from '../../components/ui/AppMoneyDisplay.vue'
import AppDurationDisplay from '../../components/ui/AppDurationDisplay.vue'
import AttachmentList from '../../components/AttachmentList.vue'
import CustomerSelect from '../../components/CustomerSelect.vue'
import RelatedOverview from '../../components/RelatedOverview.vue'
import { projectsApi, type Project } from '../../api'
import { useNotify } from '../../composables/useNotify'
import { useConfirmDelete } from '../../composables/useConfirmDelete'
import { useUnsavedChanges } from '../../composables/useUnsavedChanges'
import { projectStatusValues as statuses } from '../../utils/enums'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const id = route.params.id as string
const project = ref<Project | null>(null)
const form = ref<Partial<Project>>({})
const { markSaved } = useUnsavedChanges(form)
const saving = ref(false)
const tab = ref('overview')

async function load() {
  project.value = await projectsApi.get(id)
  form.value = { ...project.value }
  markSaved()
}
const loadFailed = useLoadFailed(load)

async function save() {
  saving.value = true
  try {
    project.value = await projectsApi.update(id, form.value)
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
  <div v-if="project">
    <AppPageHeader
      back-to="/projects"
      :back-label="t('nav.projects')"
      :title="project.name"
      :subtitle="[project.number, project.customer_name].filter(Boolean).join(' · ')"
    >
      <template #actions>
        <Button
          :label="t('common.delete')"
          text
          severity="danger"
          @click="
            confirmDelete(async () => {
              await projectsApi.remove(id)
              router.push('/projects')
            })
          "
        />
        <Button
          v-if="tab === 'overview'"
          :label="t('overview.createInvoice')"
          icon="pi pi-file"
          @click="router.push(`/invoices/new?customer=${project.customer}&project=${id}`)"
        />
        <Button
          v-if="tab === 'details'"
          :label="t('common.save')"
          :loading="saving"
          @click="save"
        />
      </template>
    </AppPageHeader>

    <Tabs v-model:value="tab">
      <TabList>
        <Tab value="overview">{{ t('overview.title') }}</Tab>
        <Tab value="details">{{ t('overview.masterData') }}</Tab>
        <Tab value="attachments">{{ t('customers.attachments') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="overview">
          <div class="flex flex-col gap-4 pt-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="app-card p-4">
                <div class="flex justify-between text-sm mb-1">
                  <span>{{ t('projects.usedHours') }}</span>
                  <span class="tabular-nums"
                    ><AppDurationDisplay :minutes="project.used_hours * 60" /> /
                    <AppDurationDisplay
                      :minutes="project.budget_hours == null ? null : project.budget_hours * 60"
                  /></span>
                </div>
                <ProgressBar
                  :value="project.budget_hours_percent ?? 0"
                  :show-value="false"
                  :pt="{
                    value: { class: (project.budget_hours_percent ?? 0) >= 80 ? 'bg-danger' : '' },
                  }"
                />
              </div>
              <div class="app-card p-4">
                <div class="flex justify-between text-sm mb-1">
                  <span>{{ t('projects.usedAmount') }}</span>
                  <span class="tabular-nums"
                    ><AppMoneyDisplay :amount="project.used_amount" /> /
                    <AppMoneyDisplay :amount="project.budget_amount"
                  /></span>
                </div>
                <ProgressBar
                  :value="project.budget_amount_percent ?? 0"
                  :show-value="false"
                  :pt="{
                    value: { class: (project.budget_amount_percent ?? 0) >= 80 ? 'bg-danger' : '' },
                  }"
                />
              </div>
            </div>
            <RelatedOverview scope="project" :id="id" />
          </div>
        </TabPanel>
        <TabPanel value="details">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl pt-4">
            <NumberField v-model="form.number" :locked="project?.number_locked" />
            <AppFormField field="customer" :label="t('projects.customer')"
              ><CustomerSelect v-model="form.customer"
            /></AppFormField>
            <AppFormField field="name" :label="t('common.name')"
              ><InputText v-model="form.name" class="w-full"
            /></AppFormField>
            <AppFormField :label="t('common.status')">
              <AppEnumSelect
                v-model="form.status"
                :options="statuses"
                label-prefix="projects.status"
                class="w-full"
              />
            </AppFormField>
            <AppFormField field="rounding_increment_minutes" :label="t('customers.rounding')"
              ><InputNumber v-model="form.rounding_increment_minutes" :min="0" class="w-full"
            /></AppFormField>
            <AppFormField field="budget_hours" :label="t('projects.budgetHours')"
              ><InputNumber v-model="form.budget_hours" class="w-full"
            /></AppFormField>
            <AppFormField field="budget_amount" :label="t('projects.budgetAmount')"
              ><InputNumber
                v-model="form.budget_amount"
                mode="currency"
                currency="EUR"
                class="w-full"
            /></AppFormField>
            <AppFormField field="description" :label="t('time.description')" class="md:col-span-2"
              ><Textarea v-model="form.description" rows="3" class="w-full"
            /></AppFormField>
          </div>
        </TabPanel>
        <TabPanel value="attachments">
          <div class="pt-4"><AttachmentList model="project" :object-id="id" /></div>
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
  <AppLoadState v-else :failed="loadFailed" back-to="/projects" :back-label="t('nav.projects')" />
</template>
