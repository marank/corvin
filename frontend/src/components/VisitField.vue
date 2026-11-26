<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import AppFormField from './ui/AppFormField.vue'
import { visitsApi, type Visit } from '../api'
import { hhmm, likelyVisit } from '../visits'

// The on-site visit a time entry belongs to: the customer's visits on the entry's day.
// Shown only when there are any. With `suggest`, and when customer or day change, the likely
// one is picked (likelyVisit).
const props = defineProps<{
  customerId: string | null
  day: string
  time: string
  suggest?: boolean
}>()
const model = defineModel<string | null>({ required: true })
const { t } = useI18n()
const visits = ref<Visit[]>([])

const options = computed(() => [
  { id: null, label: `— ${t('common.no')} —` },
  ...visits.value.map((visit) => ({
    id: visit.id,
    label: [
      visit.number,
      visit.arrival ? [hhmm(visit.arrival), hhmm(visit.departure)].filter(Boolean).join('–') : '',
      visit.location,
    ]
      .filter(Boolean)
      .join(' · '),
  })),
])

let request = 0
watch(
  () => [props.customerId, props.day] as const,
  async ([customer, day], old) => {
    const current = ++request
    const found = customer
      ? await visitsApi
          .list(`customer=${customer}&date=${day}&ordering=arrival`)
          .then((page) => page.results)
          .catch(() => [])
      : []
    if (current !== request) return
    visits.value = found
    if (!props.suggest && old === undefined) return
    if (!found.some((visit) => visit.id === model.value))
      model.value = likelyVisit(found, props.time)?.id ?? null
  },
  { immediate: true },
)
</script>

<template>
  <AppFormField v-if="visits.length" field="visit" :label="t('visits.visit')">
    <Select
      v-model="model"
      :options="options"
      option-label="label"
      option-value="id"
      class="w-full"
    />
  </AppFormField>
</template>
