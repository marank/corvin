<script setup lang="ts">
import { computed, ref, useId, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputNumber from 'primevue/inputnumber'
import AppFormField from './ui/AppFormField.vue'
import AppMoneyDisplay from './ui/AppMoneyDisplay.vue'
import AppSegmented from './ui/AppSegmented.vue'
import { visitsApi, type TravelTerms } from '../api'
import { useFormattingStore } from '../stores/formatting'

// A visit's trip as a form section: billed or not, distance, price, total. Empty fields take
// the customer's distance and the travel rate's amount; once billed, the invoice.
const props = defineProps<{
  customer?: string | null
  project?: string | null
  date?: string | null
  invoiceId?: string | null
  invoiceNumber?: string | null
}>()
const bill = defineModel<boolean>('bill', { required: true })
const distance = defineModel<number | null | undefined>('distance', { required: true })
const price = defineModel<number | null | undefined>('price', { required: true })
const { t } = useI18n()
const formatting = useFormattingStore()
const headingId = useId()
const billOptions = computed(() => [
  { label: t('common.yes'), value: true },
  { label: t('common.no'), value: false },
])

const terms = ref<TravelTerms | null>(null)
let request = 0
watch(
  () => [props.customer, props.project, props.date] as const,
  async ([customer, project, date]) => {
    const current = ++request
    terms.value = null
    if (!customer || !date) return
    const params = new URLSearchParams({ customer, date })
    if (project) params.set('project', project)
    const found = await visitsApi.travelTerms(params.toString()).catch(() => null)
    if (current === request) terms.value = found
  },
  { immediate: true },
)

const num = (value: unknown) => (value == null || value === '' ? null : Number(value))
const decimal = (value: number | null, digits: number) =>
  value == null ? undefined : value.toFixed(digits).replace('.', formatting.decimalSeparator)

const rate = computed(() => terms.value?.rate ?? null)
// Without a rate the visit's own price counts per km, there and back.
const perKm = computed(() => rate.value?.kind !== 'flat')
const factor = computed(() => (rate.value?.round_trip === false ? 1 : 2))
const customerDistance = computed(() => num(terms.value?.customer_distance_km))
const ratePrice = computed(() => num(rate.value?.amount))
const km = computed(() => num(distance.value) ?? customerDistance.value)
const unitPrice = computed(() => num(price.value) ?? ratePrice.value)
const total = computed(() => {
  if (unitPrice.value == null) return null
  if (!perKm.value) return unitPrice.value
  return km.value ? km.value * factor.value * unitPrice.value : null
})
const hint = computed(() => {
  if (!terms.value) return null
  if (terms.value.included) return t('travel.inContract')
  if (unitPrice.value == null) return t('travel.noRate')
  if (perKm.value && !km.value) return t('travel.noDistance')
  return null
})
</script>

<template>
  <section class="mt-4" :aria-labelledby="headingId">
    <!-- A heading on the line, like the legends of the other forms' fieldsets. -->
    <div class="flex items-center gap-2 mb-4">
      <span class="w-2 border-t border-surface-200 dark:border-surface-700" />
      <h3 :id="headingId" class="font-medium">{{ t('travel.trip') }}</h3>
      <span class="flex-1 border-t border-surface-200 dark:border-surface-700" />
      <template v-if="invoiceId">
        <small class="text-surface-500">
          {{ t('travel.billedOn') }}
          <router-link :to="`/invoices/${invoiceId}`" class="text-primary">{{
            invoiceNumber || invoiceId
          }}</router-link>
        </small>
        <span class="w-2 border-t border-surface-200 dark:border-surface-700" />
      </template>
    </div>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 items-start">
      <AppFormField :label="t('travel.bill')">
        <AppSegmented v-model="bill" :options="billOptions" fluid />
      </AppFormField>
      <AppFormField v-if="perKm" field="distance_km" :label="t('travel.oneWay')"
        ><InputNumber
          v-model="distance"
          :min="0"
          :max-fraction-digits="1"
          :placeholder="customerDistance == null ? undefined : `${decimal(customerDistance, 0)} km`"
          :disabled="!bill"
          suffix=" km"
          fluid
      /></AppFormField>
      <AppFormField
        field="travel_price"
        :label="perKm ? t('travel.pricePerKm') : t('travel.kinds.flat')"
        ><InputNumber
          v-model="price"
          :min="0"
          :min-fraction-digits="2"
          :max-fraction-digits="2"
          :placeholder="ratePrice == null ? undefined : `${decimal(ratePrice, 2)} €`"
          :disabled="!bill"
          suffix=" €"
          fluid
        /><small v-if="perKm && factor === 2" class="text-surface-500">{{
          t('travel.roundTrip')
        }}</small></AppFormField
      >
      <AppFormField :label="t('travel.total')">
        <div class="p-inputtext p-component w-full font-medium" :class="{ 'opacity-60': !bill }">
          <AppMoneyDisplay :amount="bill ? total : null" />
        </div>
        <small v-if="bill && hint" class="text-surface-500">{{ hint }}</small>
      </AppFormField>
    </div>
  </section>
</template>
