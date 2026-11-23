<script setup lang="ts">
// A date as free text ("021126", "2.11.", "2", "heute", see dateTimeInput.ts), read on Enter
// or when leaving the field; the calendar button still offers a picker. Model: "YYYY-MM-DD".
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'
import Popover from 'primevue/popover'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDate, isoDate, parseDate } from '../../dateTimeInput'

const props = defineProps<{ modelValue: string | null; placeholder?: string }>()
const emit = defineEmits<{ 'update:modelValue': [string | null] }>()
const { t } = useI18n()

const text = ref('')
const focused = ref(false)
const invalid = ref(false)
const popover = ref<InstanceType<typeof Popover>>()

function show(value: string | null) {
  text.value = value ? formatDate(value) : ''
  invalid.value = false
}
watch(
  () => props.modelValue,
  (value) => {
    if (!focused.value) show(value)
  },
  { immediate: true },
)

const reference = computed(() =>
  props.modelValue ? new Date(props.modelValue + 'T00:00:00') : new Date(),
)
// While typing: what the text would become, so surprises show before leaving the field.
const preview = computed(() => {
  if (!focused.value || !text.value.trim()) return ''
  const parsed = parseDate(text.value, reference.value)
  if (!parsed) return t('time.dateUnreadable')
  return formatDate(parsed) === text.value.trim() ? '' : `→ ${formatDate(parsed)}`
})

function commit() {
  if (!text.value.trim()) {
    invalid.value = false
    if (props.modelValue !== null) emit('update:modelValue', null)
    return
  }
  const parsed = parseDate(text.value, reference.value)
  if (!parsed) {
    invalid.value = true
    return
  }
  invalid.value = false
  text.value = formatDate(parsed)
  if (parsed !== props.modelValue) emit('update:modelValue', parsed)
}

function onBlur() {
  focused.value = false
  commit()
}

const picked = computed({
  get: () => (props.modelValue ? new Date(props.modelValue + 'T00:00:00') : null),
  set: (d: Date | Date[] | (Date | null)[] | null | undefined) => {
    if (!(d instanceof Date)) return
    const iso = isoDate(d)
    emit('update:modelValue', iso)
    show(iso)
    popover.value?.hide()
  },
})
</script>

<template>
  <div class="relative">
    <div class="flex">
      <InputText
        v-model="text"
        class="flex-1 min-w-0"
        :invalid="invalid"
        :placeholder="placeholder ?? t('time.datePlaceholder')"
        @focus="focused = true"
        @blur="onBlur"
        @keydown.enter.prevent="commit"
        @keydown.esc="show(props.modelValue)"
      />
      <Button
        icon="pi pi-calendar"
        severity="secondary"
        class="picker-button"
        :aria-label="t('time.pickDate')"
        @click="popover?.toggle($event)"
      />
    </div>
    <small
      v-if="preview"
      class="absolute left-0 top-full text-xs text-surface-500 whitespace-nowrap"
      >{{ preview }}</small
    >
    <Popover ref="popover">
      <!-- The popover already draws the frame and padding. -->
      <DatePicker v-model="picked" inline :pt="{ panel: { style: 'border: 0; padding: 0' } }" />
    </Popover>
  </div>
</template>

<style scoped>
/* Framed like the text field next to it, sharing its border. */
.picker-button {
  border-color: var(--p-inputtext-border-color);
  border-left-width: 0;
}
</style>
