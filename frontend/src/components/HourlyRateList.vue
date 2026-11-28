<script setup lang="ts">
import { isoDate } from '../dateTimeInput'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Column from 'primevue/column'
import InputNumber from 'primevue/inputnumber'
import AppDataTable from './ui/AppDataTable.vue'
import AppDateInput from './ui/AppDateInput.vue'
import AppDateTimeDisplay from './ui/AppDateTimeDisplay.vue'
import AppFormField from './ui/AppFormField.vue'
import AppIconButton from './ui/AppIconButton.vue'
import AppModal from './ui/AppModal.vue'
import AppMoneyDisplay from './ui/AppMoneyDisplay.vue'
import { ratesApi, type HourlyRate } from '../api'
import { useNotify } from '../composables/useNotify'
import { useConfirmDelete } from '../composables/useConfirmDelete'
import { tableStateKeys } from '../tableStateKeys'

// A customer's hourly rates, or without `customerId` the company's default rates, which
// apply wherever a customer (or project) has no rate of its own.
const props = defineProps<{ customerId?: string }>()
const { t } = useI18n()
const notify = useNotify()
const confirmDelete = useConfirmDelete()
const rates = ref<HourlyRate[]>([])
const defaults = ref<HourlyRate[]>([])
const modal = ref<InstanceType<typeof AppModal>>()
const editing = ref<HourlyRate | null>(null)
const form = ref<Partial<HourlyRate>>({})
const today = isoDate()
const emptyForm = (): Partial<HourlyRate> => ({ amount: 0, valid_from: today, valid_to: null })

const scope = computed(() =>
  props.customerId
    ? `customer=${props.customerId}&project__isnull=true`
    : 'customer__isnull=true&project__isnull=true',
)
// The default rate in effect today, as the backend resolves it.
const currentDefault = computed(
  () =>
    defaults.value
      .filter((rate) => rate.valid_from <= today && (!rate.valid_to || rate.valid_to >= today))
      .sort((a, b) => b.valid_from.localeCompare(a.valid_from))[0],
)

async function load() {
  rates.value = (await ratesApi.list(`${scope.value}&page_size=500&ordering=-valid_from`)).results
  if (props.customerId) {
    defaults.value = (
      await ratesApi.list('customer__isnull=true&project__isnull=true&page_size=500')
    ).results
  }
}
onMounted(() => load().catch((e: unknown) => notify.error(e)))

function open(rate?: HourlyRate) {
  editing.value = rate ?? null
  form.value = rate ? { ...rate } : emptyForm()
  modal.value?.open()
}

async function save() {
  try {
    if (editing.value) await ratesApi.update(editing.value.id, form.value)
    else await ratesApi.create({ ...form.value, customer: props.customerId ?? null })
    modal.value?.close()
    notify.ok(t('common.saved'))
    await load()
  } catch (e) {
    notify.error(e)
  }
}

function remove(rate: HourlyRate) {
  confirmDelete(async () => {
    await ratesApi.remove(rate.id)
    await load()
  })
}
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center gap-3 mb-2">
      <p class="text-sm text-surface-500">
        <template v-if="!customerId">{{ t('rates.defaultsHint') }}</template>
        <template v-else-if="currentDefault">
          {{ t('rates.customerHint') }}
          <AppMoneyDisplay :amount="currentDefault.amount" />{{ t('rates.perHour') }}
        </template>
        <template v-else>{{ t('rates.noDefaultHint') }}</template>
        <router-link v-if="customerId" to="/settings?tab=rates" class="text-primary ms-1">{{
          t('rates.manageDefaults')
        }}</router-link>
      </p>
      <Button
        :label="customerId ? t('customers.newRate') : t('rates.newDefault')"
        icon="iconify lucide--plus"
        size="small"
        class="ms-auto"
        @click="open()"
      />
    </div>
    <AppDataTable
      :rows="rates"
      :state-key="customerId ? tableStateKeys.customerRates : tableStateKeys.defaultRates"
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
      <Column class="app-num" field="amount" :header="t('customers.hourlyRate')" sortable>
        <template #body="{ data }"
          ><AppMoneyDisplay :amount="data.amount" />{{ t('rates.perHour') }}</template
        >
      </Column>
      <Column :reorderable-column="false">
        <template #body="{ data }">
          <AppIconButton
            icon="iconify lucide--trash-2"
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
      :title="
        editing
          ? t('customers.editRate')
          : customerId
            ? t('customers.newRate')
            : t('rates.newDefault')
      "
      @confirm="save"
    >
      <div class="flex flex-col gap-4">
        <AppFormField field="amount" :label="t('customers.hourlyRate')" required
          ><InputNumber v-model="form.amount" mode="currency" currency="EUR" class="w-full"
        /></AppFormField>
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
