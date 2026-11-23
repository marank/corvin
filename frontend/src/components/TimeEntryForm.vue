<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import Textarea from 'primevue/textarea'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Button from 'primevue/button'
import AppFormField from './ui/AppFormField.vue'
import AppCheckboxField from './ui/AppCheckboxField.vue'
import AppDateTimeInput from './ui/AppDateTimeInput.vue'
import AppDateTimeDisplay from './ui/AppDateTimeDisplay.vue'
import AppIconButton from './ui/AppIconButton.vue'
import CustomerSelect from './CustomerSelect.vue'
import ProjectSelect from './ProjectSelect.vue'
import { contractsApi, timeTrackingApi, type SupportContract, type TimeEntry } from '../api'
import { useNotify } from '../composables/useNotify'
import { formatDuration, parseDuration } from '../dateTimeInput'

const props = defineProps<{ entry?: TimeEntry | null }>()
const emit = defineEmits<{ saved: [entry: TimeEntry] }>()
const { t } = useI18n()
const notify = useNotify()

interface BreakForm {
  id?: string
  start_datetime: string
  end_datetime: string | null
}

const customerId = ref<string | null>(null)
const form = ref({
  project: null as string | null,
  visit: null as string | null,
  contract: null as string | null,
  start_datetime: new Date().toISOString(),
  end_datetime: null as string | null,
  duration_minutes: 0,
  breaks: [] as BreakForm[],
  description: '',
  billable: true,
})
const saving = ref(false)
const contracts = ref<SupportContract[]>([])
const updating = ref(false)
const durationText = ref('00:00')
const durationInvalid = ref(false)

function breakMinutes(): number {
  let total = 0
  for (const b of form.value.breaks) {
    if (b.end_datetime) {
      total += Math.max(
        0,
        Math.round(
          (new Date(b.end_datetime).getTime() - new Date(b.start_datetime).getTime()) / 60_000,
        ),
      )
    }
  }
  return total
}

function recalcEndFromDuration() {
  if (updating.value) return
  const start = new Date(form.value.start_datetime)
  updating.value = true
  form.value.end_datetime = new Date(
    start.getTime() + (form.value.duration_minutes + breakMinutes()) * 60_000,
  ).toISOString()
  durationText.value = formatDuration(form.value.duration_minutes)
  void nextTick(() => {
    updating.value = false
  })
}

function recalcDurationFromTimes() {
  if (updating.value) return
  const start = new Date(form.value.start_datetime)
  const end = form.value.end_datetime ? new Date(form.value.end_datetime) : null
  if (!end) return
  updating.value = true
  form.value.duration_minutes = Math.max(
    0,
    Math.round((end.getTime() - start.getTime()) / 60_000) - breakMinutes(),
  )
  durationText.value = formatDuration(form.value.duration_minutes)
  void nextTick(() => {
    updating.value = false
  })
}

// Read on Enter or when leaving the field: "3" is 3 h, "3,5" 3:30, also "3:30", "90m", "1h30".
function commitDuration() {
  const minutes = parseDuration(durationText.value)
  durationInvalid.value = minutes === null
  if (minutes === null) return
  durationText.value = formatDuration(minutes)
  form.value.duration_minutes = minutes
}

watch(() => form.value.start_datetime, recalcDurationFromTimes)
watch(() => form.value.end_datetime, recalcDurationFromTimes)
watch(() => form.value.duration_minutes, recalcEndFromDuration)
watch(() => form.value.breaks, recalcDurationFromTimes, { deep: true })

watch(
  () => props.entry,
  (e) => {
    if (!e) return
    customerId.value = e.customer
    form.value = {
      project: e.project,
      visit: e.visit,
      contract: e.contract,
      start_datetime: e.start_datetime,
      end_datetime: e.end_datetime,
      duration_minutes: e.duration_minutes,
      breaks: e.breaks.map((b) => ({
        id: b.id,
        start_datetime: b.start_datetime,
        end_datetime: b.end_datetime,
      })),
      description: e.description,
      billable: e.billable,
    }
    durationText.value = formatDuration(e.duration_minutes)
  },
  { immediate: true },
)

watch(customerId, async (cid) => {
  contracts.value = []
  if (!cid) return
  contracts.value = (await contractsApi.list(`customer=${cid}&active=true&page_size=100`)).results
})

const normalizedDurationText = computed(() => {
  const start = props.entry?.normalized_start_datetime
  const end = props.entry?.normalized_end_datetime
  if (!start || !end) return '—'
  const minutes = Math.max(
    0,
    Math.round((new Date(end).getTime() - new Date(start).getTime()) / 60_000),
  )
  return formatDuration(minutes)
})

const contractOptions = computed(() => [
  { id: null, name: `— ${t('common.no')} —` },
  ...contracts.value,
])

function addBreak() {
  form.value.breaks.push({
    start_datetime: new Date().toISOString(),
    end_datetime: null,
  })
}

function removeBreak(index: number) {
  form.value.breaks.splice(index, 1)
}

async function save() {
  saving.value = true
  try {
    const payload = {
      project: form.value.project,
      visit: form.value.visit,
      contract: form.value.contract,
      customer: customerId.value,
      start_datetime: form.value.start_datetime,
      end_datetime: form.value.end_datetime,
      breaks: form.value.breaks,
      description: form.value.description,
      billable: form.value.billable,
    }
    const saved = props.entry
      ? await timeTrackingApi.update(props.entry.id, payload)
      : await timeTrackingApi.create(payload)
    notify.ok(t('common.saved'))
    emit('saved', saved)
  } catch (e) {
    notify.error(e)
  } finally {
    saving.value = false
  }
}

// The surrounding AppModal renders Save/Cancel and checks `state` for unsaved changes.
const state = computed(() => ({ ...form.value, customer: customerId.value }))
defineExpose({ save, saving, state })
</script>

<template>
  <div class="flex flex-col gap-4">
    <AppFormField field="customer" :label="t('projects.customer')"
      ><CustomerSelect v-model="customerId"
    /></AppFormField>
    <AppFormField field="project" :label="t('projects.project')">
      <ProjectSelect v-model="form.project" :customer-id="customerId" />
    </AppFormField>
    <AppFormField v-if="contracts.length" field="contract" :label="t('time.coveredByContract')">
      <Select
        v-model="form.contract"
        :options="contractOptions"
        option-label="name"
        option-value="id"
        class="w-full"
      />
    </AppFormField>
    <div class="grid grid-cols-1 sm:grid-cols-5 gap-3">
      <AppFormField field="start_datetime" class="sm:col-span-2" :label="t('time.start')" required
        ><AppDateTimeInput v-model="form.start_datetime"
      /></AppFormField>
      <AppFormField field="end_datetime" class="sm:col-span-2" :label="t('time.end')"
        ><AppDateTimeInput v-model="form.end_datetime" :reference="form.start_datetime"
      /></AppFormField>
      <AppFormField :label="t('time.duration')">
        <InputText
          v-model="durationText"
          class="w-full"
          :invalid="durationInvalid"
          :placeholder="t('time.durationPlaceholder')"
          @blur="commitDuration"
          @keydown.enter.prevent="commitDuration"
        />
      </AppFormField>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-5 gap-3">
      <AppFormField class="sm:col-span-2" :label="t('time.normalizedStart')">
        <div
          class="min-h-10 flex items-center px-3 border border-surface-300 dark:border-surface-700 bg-surface-100 dark:bg-surface-800 text-sm"
        >
          <AppDateTimeDisplay
            v-if="props.entry?.normalized_start_datetime"
            :value="props.entry.normalized_start_datetime"
            type="datetime"
          />
          <span v-else class="text-surface-500">—</span>
        </div>
      </AppFormField>
      <AppFormField class="sm:col-span-2" :label="t('time.normalizedEnd')">
        <div
          class="min-h-10 flex items-center px-3 border border-surface-300 dark:border-surface-700 bg-surface-100 dark:bg-surface-800 text-sm"
        >
          <AppDateTimeDisplay
            v-if="props.entry?.normalized_end_datetime"
            :value="props.entry.normalized_end_datetime"
            type="datetime"
          />
          <span v-else class="text-surface-500">—</span>
        </div>
      </AppFormField>
      <AppFormField :label="t('time.normalizedDuration')">
        <div
          class="min-h-10 flex items-center px-3 border border-surface-300 dark:border-surface-700 bg-surface-100 dark:bg-surface-800 text-sm"
        >
          <span
            v-if="props.entry?.normalized_start_datetime && props.entry?.normalized_end_datetime"
            >{{ normalizedDurationText }}</span
          >
          <span v-else class="text-surface-500">—</span>
        </div>
      </AppFormField>
    </div>
    <div class="flex flex-col gap-2">
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium">{{ t('time.breaks') }}</span>
        <Button :label="t('time.addBreak')" icon="pi pi-plus" size="small" text @click="addBreak" />
      </div>
      <div
        v-for="(b, index) in form.breaks"
        :key="index"
        class="grid grid-cols-[1fr_1fr_auto] sm:grid-cols-5 gap-3 items-end"
      >
        <AppFormField class="sm:col-span-2" :label="t('time.start')">
          <AppDateTimeInput v-model="b.start_datetime" :reference="form.start_datetime" />
        </AppFormField>
        <AppFormField class="sm:col-span-2" :label="t('time.end')">
          <AppDateTimeInput v-model="b.end_datetime" :reference="b.start_datetime" />
        </AppFormField>
        <AppIconButton
          icon="pi pi-trash"
          severity="danger"
          :label="t('common.delete')"
          @click="removeBreak(index)"
        />
      </div>
    </div>
    <AppFormField field="description" :label="t('time.description')">
      <Textarea v-model="form.description" rows="3" class="w-full" />
    </AppFormField>
    <AppCheckboxField v-model="form.billable" :label="t('time.billable')" />
  </div>
</template>
