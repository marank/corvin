<script setup lang="ts">
import InputText from 'primevue/inputtext'
import { useI18n } from 'vue-i18n'
import AppFormField from './ui/AppFormField.vue'

// The number of a saved record: assigned by its numbering scheme, correctable by hand until a
// finalized invoice shows it (`locked`, decided by the API).
defineProps<{ locked?: boolean }>()
const number = defineModel<string | undefined>({ required: true })
const { t } = useI18n()
</script>

<template>
  <AppFormField field="number" :label="t('common.number')">
    <InputText v-model="number" class="w-full" :disabled="locked" />
    <small v-if="locked" class="text-surface-500">{{ t('common.numberLocked') }}</small>
  </AppFormField>
</template>
