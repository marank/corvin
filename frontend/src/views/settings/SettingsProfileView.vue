<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import { settingsApi } from '../../api'
import { useNotify } from '../../composables/useNotify'

const { t } = useI18n()
const router = useRouter()
const notify = useNotify()
const form = ref<Record<string, unknown>>({})
const saving = ref(false)

onMounted(async () => {
  form.value = await settingsApi.get()
})

async function save() {
  saving.value = true
  try {
    form.value = await settingsApi.update(form.value)
    notify.ok(t('common.save'))
  } catch (e) {
    notify.error(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <AppPageHeader :title="t('settings.title')">
      <template #actions>
        <Button :label="t('settings.security')" text icon="pi pi-shield" @click="router.push('/settings/security')" />
        <Button :label="t('common.save')" :loading="saving" @click="save" />
      </template>
    </AppPageHeader>

    <h2 class="font-semibold mb-3">{{ t('settings.company') }}</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl">
      <AppFormField :label="t('settings.companyName')"><InputText v-model="(form.company_name as string)" class="w-full" /></AppFormField>
      <AppFormField :label="t('common.email')"><InputText v-model="(form.email as string)" class="w-full" /></AppFormField>
      <AppFormField :label="t('common.address')" class="md:col-span-2"><InputText v-model="(form.street as string)" class="w-full" /></AppFormField>
      <AppFormField label="PLZ"><InputText v-model="(form.postal_code as string)" class="w-full" /></AppFormField>
      <AppFormField :label="t('common.address')"><InputText v-model="(form.city as string)" class="w-full" /></AppFormField>
      <AppFormField :label="t('settings.taxId')"><InputText v-model="(form.tax_id as string)" class="w-full" /></AppFormField>
      <AppFormField :label="t('settings.vatId')"><InputText v-model="(form.vat_id as string)" class="w-full" /></AppFormField>
      <AppFormField :label="t('settings.iban')"><InputText v-model="(form.iban as string)" class="w-full" /></AppFormField>
      <AppFormField :label="t('settings.bic')"><InputText v-model="(form.bic as string)" class="w-full" /></AppFormField>
      <AppFormField :label="t('settings.invoicePrefix')"><InputText v-model="(form.invoice_prefix as string)" class="w-full" /></AppFormField>
      <AppFormField :label="t('settings.defaultVat')"><InputNumber v-model="(form.default_vat_rate as number)" :min-fraction-digits="2" class="w-full" /></AppFormField>
      <AppFormField :label="t('settings.paymentTerms')"><InputNumber v-model="(form.payment_terms_days as number)" class="w-full" /></AppFormField>
    </div>
  </div>
</template>
