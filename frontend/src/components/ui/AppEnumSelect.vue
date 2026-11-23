<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'

// Select over fixed backend values, labelled via `${labelPrefix}.${value}`. The options
// carry the translated label, so the selected text (and its accessible name) is never the raw value.
const props = defineProps<{
  options: readonly string[]
  labelPrefix: string
  placeholder?: string
  showClear?: boolean
}>()
const model = defineModel<string | null | undefined>()
const { t } = useI18n()
const items = computed(() =>
  props.options.map((value) => ({ value, label: t(`${props.labelPrefix}.${value}`) })),
)
</script>

<template>
  <!-- eslint-disable-next-line vuejs-accessibility/form-control-has-label -- a wrapper: the caller labels it (AppFormField or an aria-label that falls through to the Select). -->
  <Select
    v-model="model"
    :options="items"
    option-label="label"
    option-value="value"
    :placeholder="placeholder"
    :show-clear="showClear"
  />
</template>
