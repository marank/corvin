<script setup lang="ts">
import { isoDate } from '../dateTimeInput'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Column from 'primevue/column'
import InputNumber from 'primevue/inputnumber'
import AppCheckboxField from './ui/AppCheckboxField.vue'
import AppDataTable from './ui/AppDataTable.vue'
import AppDateInput from './ui/AppDateInput.vue'
import AppDateTimeDisplay from './ui/AppDateTimeDisplay.vue'
import AppEnumSelect from './ui/AppEnumSelect.vue'
import AppFormField from './ui/AppFormField.vue'
import AppIconButton from './ui/AppIconButton.vue'
import AppModal from './ui/AppModal.vue'
import AppMoneyDisplay from './ui/AppMoneyDisplay.vue'
import { travelRatesApi, type TravelRate } from '../api'
import { useNotify } from '../composables/useNotify'
import { useConfirmDelete } from '../composables/useConfirmDelete'
import { tableStateKeys } from '../tableStateKeys'

// Travel rates of a customer, or without `customerId` the company's defaults.
const props = defineProps<{ customerId?: string }>()
const { t } = useI18n()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const rates = ref<TravelRate[]>([])
const modal = ref<InstanceType<typeof AppModal>>()
const editing = ref<TravelRate | null>(null)
const form = ref<Partial<TravelRate>>({})
const kinds = ['flat', 'km']
const emptyForm = (): Partial<TravelRate> => ({
  kind: 'flat',
  amount: 0,
  round_trip: true,
  valid_from: isoDate(),
  valid_to: null,
})

async function load() {
  const scope = props.customerId
    ? `customer=${props.customerId}&project__isnull=true`
    : 'customer__isnull=true&project__isnull=true'
  rates.value = (await travelRatesApi.list(`${scope}&page_size=500&ordering=-valid_from`)).results
}
onMounted(() => load().catch((e: unknown) => notify.error(e)))

function open(rate?: TravelRate) {
  editing.value = rate ?? null
  form.value = rate ? { ...rate } : emptyForm()
  modal.value?.open()
}

async function save() {
  try {
    if (editing.value) await travelRatesApi.update(editing.value.id, form.value)
    else await travelRatesApi.create({ ...form.value, customer: props.customerId ?? null })
    modal.value?.close()
    notify.ok(t('common.saved'))
    await load()
  } catch (e) {
    notify.error(e)
  }
}

function remove(rate: TravelRate) {
  confirmDelete(async () => {
    await travelRatesApi.remove(rate.id)
    await load()
  })
}
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-2">
      <h3 class="font-semibold">{{ t('travel.rates') }}</h3>
      <Button
        :label="t('travel.newRate')"
        icon="pi pi-plus"
        size="small"
        class="ms-auto"
        @click="open()"
      />
    </div>
    <AppDataTable
      :rows="rates"
      :state-key="customerId ? tableStateKeys.customerTravelRates : tableStateKeys.travelRates"
      @row-click="open"
    >
      <Column field="valid_from" :header="t('customers.validFrom')" sortable
        ><template #body="{ data }"><AppDateTimeDisplay :value="data.valid_from" /></template
      ></Column>
      <Column field="valid_to" :header="t('customers.validTo')">
        <template #body="{ data }"
          ><AppDateTimeDisplay v-if="data.valid_to" :value="data.valid_to" /><span v-else
            >—</span
          ></template
        >
      </Column>
      <Column field="kind" :header="t('travel.kind')" header-style="width: 12rem">
        <template #body="{ data }"
          >{{ t(`travel.kinds.${data.kind}`)
          }}{{
            data.kind === 'km' && data.round_trip ? ` · ${t('travel.roundTrip')}` : ''
          }}</template
        >
      </Column>
      <Column class="app-num" field="amount" :header="t('common.amount')" sortable>
        <template #body="{ data }"
          ><AppMoneyDisplay :amount="data.amount" />{{
            data.kind === 'km' ? t('travel.perKm') : ''
          }}</template
        >
      </Column>
      <Column :reorderable-column="false">
        <template #body="{ data }">
          <AppIconButton
            icon="pi pi-trash"
            severity="danger"
            :label="t('common.delete')"
            @click.stop="remove(data)"
          />
        </template>
      </Column>
    </AppDataTable>

    <AppModal
      ref="modal"
      :form="form"
      :title="editing ? t('travel.editRate') : t('travel.newRate')"
      @confirm="save"
    >
      <div class="flex flex-col gap-4">
        <AppFormField field="kind" :label="t('travel.kind')" required>
          <AppEnumSelect
            v-model="form.kind"
            :options="kinds"
            label-prefix="travel.kinds"
            class="w-full"
          />
        </AppFormField>
        <AppFormField field="amount" :label="t('common.amount')" required
          ><InputNumber v-model="form.amount" mode="currency" currency="EUR" class="w-full"
        /></AppFormField>
        <AppCheckboxField
          v-if="form.kind === 'km'"
          v-model="form.round_trip"
          :label="t('travel.roundTrip')"
          class="self-start!"
        />
        <AppFormField field="valid_from" :label="t('customers.validFrom')" required
          ><AppDateInput v-model="form.valid_from as any"
        /></AppFormField>
        <AppFormField field="valid_to" :label="t('customers.validTo')"
          ><AppDateInput v-model="form.valid_to as any"
        /></AppFormField>
      </div>
    </AppModal>
  </div>
</template>
