<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'

// Search field for list toolbars (AppFilterBar's #end slot). The model updates
// 300 ms after the last keystroke, so lists don't refetch on every key.
const model = defineModel<string>({ default: '' })
const { t } = useI18n()
const text = ref(model.value)
let timer: ReturnType<typeof setTimeout> | undefined

watch(model, (value) => {
  if (value !== text.value.trim()) text.value = value
})
watch(text, (value) => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    model.value = value.trim()
  }, 300)
})
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <IconField>
    <InputIcon class="iconify lucide--search" />
    <InputText
      v-model="text"
      :placeholder="t('common.search')"
      :aria-label="t('common.search')"
      size="small"
      class="w-48"
    />
  </IconField>
</template>
