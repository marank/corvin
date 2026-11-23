<script setup lang="ts">
import AppEnumSelect from './ui/AppEnumSelect.vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import AppFormField from './ui/AppFormField.vue'
import AppCheckboxField from './ui/AppCheckboxField.vue'
import AppDateInput from './ui/AppDateInput.vue'
import CustomerSelect from './CustomerSelect.vue'
import ProjectSelect from './ProjectSelect.vue'
import type { SupportContract } from '../api'
import { contractPeriodValues as periods } from '../utils/enums'

// Contract fields, shared by the create modal and the contract's master data tab.
const form = defineModel<Partial<SupportContract>>({ required: true })
const { t } = useI18n()
</script>

<template>
  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <AppFormField field="name" :label="t('common.name')" required
      ><InputText v-model="form.name" class="w-full"
    /></AppFormField>
    <AppFormField field="customer" :label="t('projects.customer')" required
      ><CustomerSelect v-model="form.customer"
    /></AppFormField>
    <AppFormField field="project" :label="t('projects.project')"
      ><ProjectSelect v-model="form.project" :customer-id="form.customer"
    /></AppFormField>
    <AppFormField field="period" :label="t('contracts.period')">
      <AppEnumSelect
        v-model="form.period"
        :options="periods"
        label-prefix="contracts.periods"
        class="w-full"
      />
    </AppFormField>
    <AppFormField field="included_hours" :label="t('contracts.includedHours')"
      ><InputNumber v-model="form.included_hours" :min="0" :max-fraction-digits="2" class="w-full"
    /></AppFormField>
    <AppFormField field="fixed_price" :label="t('contracts.fixedPrice')" required
      ><InputNumber v-model="form.fixed_price" mode="currency" currency="EUR" class="w-full"
    /></AppFormField>
    <AppFormField field="start_date" :label="t('contracts.startDate')" required
      ><AppDateInput v-model="form.start_date as any"
    /></AppFormField>
    <AppFormField field="end_date" :label="t('contracts.endDate')"
      ><AppDateInput v-model="form.end_date as any"
    /></AppFormField>
    <AppFormField field="next_billing_date" :label="t('contracts.nextBilling')" required
      ><AppDateInput v-model="form.next_billing_date as any"
    /></AppFormField>
    <div />
    <AppCheckboxField v-model="form.bill_overage" :label="t('contracts.billOverage')" />
    <AppFormField v-if="form.bill_overage" field="overage_rate" :label="t('contracts.overageRate')"
      ><InputNumber v-model="form.overage_rate" mode="currency" currency="EUR" class="w-full"
    /></AppFormField>
    <div v-else />
    <AppCheckboxField v-model="form.active" :label="t('common.active')" />
  </div>
</template>
