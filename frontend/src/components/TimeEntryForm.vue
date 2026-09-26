<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Button from 'primevue/button'
import AppFormField from './ui/AppFormField.vue'
import AppCheckboxField from './ui/AppCheckboxField.vue'
import AppDateInput from './ui/AppDateInput.vue'
import CustomerSelect from './CustomerSelect.vue'
import ProjectSelect from './ProjectSelect.vue'
import {
  contractsApi,
  timeEntriesApi,
  type SupportContract,
  type TimeEntry,
} from '../api'
import { useNotify } from '../composables/useNotify'

const props = defineProps<{ entry?: TimeEntry | null }>()
const emit = defineEmits<{ saved: [entry: TimeEntry]; cancel: [] }>()
const { t } = useI18n()
const notify = useNotify()

const customerId = ref<string | null>(null)
const form = ref({
  project: null as string | null,
  visit: null as string | null,
  contract: null as string | null,
  date: new Date().toISOString().slice(0, 10),
  start_time: '',
  end_time: '',
  break_minutes: 0,
  description: '',
  billable: true,
})
const saving = ref(false)
const contracts = ref<SupportContract[]>([])

watch(
  () => props.entry,
  (e) => {
    if (!e) return
    customerId.value = e.customer
    form.value = {
      project: e.project,
      visit: e.visit,
      contract: e.contract,
      date: e.date,
      start_time: e.start_time?.slice(0, 5) ?? '',
      end_time: e.end_time?.slice(0, 5) ?? '',
      break_minutes: e.break_minutes,
      description: e.description,
      billable: e.billable,
    }
  },
  { immediate: true },
)

watch(customerId, async (cid) => {
  contracts.value = []
  if (!cid) return
  contracts.value = (
    await contractsApi.list(`customer=${cid}&active=true&page_size=100`)
  ).results
})

const contractOptions = computed(() => [
  { id: null, name: `— ${t('common.no')} —` },
  ...contracts.value,
])

async function save() {
  saving.value = true
  try {
    const payload = {
      ...form.value,
      customer: customerId.value,
      start_time: form.value.start_time + ':00',
      end_time: form.value.end_time ? form.value.end_time + ':00' : null,
    }
    const saved = props.entry
      ? await timeEntriesApi.update(props.entry.id, payload)
      : await timeEntriesApi.create(payload)
    emit('saved', saved)
  } catch (e) {
    notify.error(e, t('common.save'))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <AppFormField :label="t('projects.customer')" required><CustomerSelect v-model="customerId" /></AppFormField>
    <AppFormField :label="t('nav.projects')">
      <ProjectSelect v-model="form.project" :customer-id="customerId" />
    </AppFormField>
    <AppFormField v-if="contracts.length" :label="t('time.coveredByContract')">
      <Select v-model="form.contract" :options="contractOptions" option-label="name" option-value="id" class="w-full" />
    </AppFormField>
    <AppFormField :label="t('common.date')" required><AppDateInput v-model="form.date" /></AppFormField>
    <div class="grid grid-cols-3 gap-3">
      <AppFormField :label="t('time.start')">
        <InputText v-model="form.start_time" type="time" required class="w-full" />
      </AppFormField>
      <AppFormField :label="t('time.end')">
        <InputText v-model="form.end_time" type="time" class="w-full" />
      </AppFormField>
      <AppFormField :label="t('time.break')">
        <InputNumber v-model="form.break_minutes" :min="0" class="w-full" />
      </AppFormField>
    </div>
    <AppFormField :label="t('time.description')">
      <Textarea v-model="form.description" rows="3" class="w-full" />
    </AppFormField>
    <AppCheckboxField v-model="form.billable" :label="t('time.billable')" />
    <div class="flex justify-end gap-2">
      <Button :label="t('common.cancel')" text @click="emit('cancel')" />
      <Button :label="t('common.save')" :loading="saving" @click="save" />
    </div>
  </div>
</template>
