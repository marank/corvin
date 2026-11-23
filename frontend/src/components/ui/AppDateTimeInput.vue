<script setup lang="ts">
// Date and time as free text ("021126 1800", "2.11. 18", "18:00", "jetzt", see dateTimeInput.ts),
// read on Enter or when leaving the field; the calendar button still offers a picker.
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'
import Popover from 'primevue/popover'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDateTime, parseDateTime } from '../../dateTimeInput'

// `reference`: the day typed times fall on while the field is empty (e.g. the start for an end).
const props = defineProps<{ modelValue: string | null; reference?: string | null }>()
const emit = defineEmits<{ 'update:modelValue': [string | null] }>()
const { t } = useI18n()

const text = ref('')
const focused = ref(false)
const invalid = ref(false)
const popover = ref<InstanceType<typeof Popover>>()

function show(value: string | null) {
  text.value = value ? formatDateTime(new Date(value)) : ''
  invalid.value = false
}
watch(
  () => props.modelValue,
  (value) => {
    if (!focused.value) show(value)
  },
  { immediate: true },
)

const reference = computed(() => {
  const base = props.modelValue ?? props.reference
  return base ? new Date(base) : new Date()
})
// While typing: what the text would become, so surprises show before leaving the field.
const preview = computed(() => {
  if (!focused.value || !text.value.trim()) return ''
  const parsed = parseDateTime(text.value, reference.value)
  if (!parsed) return t('time.inputUnreadable')
  const formatted = formatDateTime(parsed)
  return formatted === text.value.trim() ? '' : `→ ${formatted}`
})

function commit() {
  if (!text.value.trim()) {
    invalid.value = false
    if (props.modelValue !== null) emit('update:modelValue', null)
    return
  }
  const parsed = parseDateTime(text.value, reference.value)
  if (!parsed) {
    invalid.value = true
    return
  }
  invalid.value = false
  text.value = formatDateTime(parsed)
  const iso = parsed.toISOString()
  if (!props.modelValue || new Date(props.modelValue).getTime() !== parsed.getTime())
    emit('update:modelValue', iso)
}

function onBlur() {
  focused.value = false
  commit()
}

// Mouse wheel over the hour or minute of the picker steps it, like its arrow buttons.
function onPickerWheel(event: WheelEvent) {
  const section = (event.target as HTMLElement).closest(
    '[data-pc-section="hourpicker"], [data-pc-section="minutepicker"]',
  )
  if (!section || event.deltaY === 0) return
  event.preventDefault()
  const step = event.deltaY < 0 ? 1 : -1
  const date = props.modelValue ? new Date(props.modelValue) : new Date()
  date.setSeconds(0, 0)
  if (section.getAttribute('data-pc-section') === 'hourpicker')
    date.setHours(date.getHours() + step)
  else date.setMinutes(date.getMinutes() + step)
  emit('update:modelValue', date.toISOString())
  show(date.toISOString())
}

const picked = computed({
  get: () => (props.modelValue ? new Date(props.modelValue) : null),
  set: (d: Date | Date[] | (Date | null)[] | null | undefined) => {
    if (!(d instanceof Date)) return
    emit('update:modelValue', d.toISOString())
    show(d.toISOString())
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
        :placeholder="t('time.dateTimePlaceholder')"
        @focus="focused = true"
        @blur="onBlur"
        @keydown.enter.prevent="commit"
        @keydown.esc="show(props.modelValue)"
      />
      <Button
        icon="pi pi-calendar"
        severity="secondary"
        class="picker-button"
        :aria-label="t('time.pickDateTime')"
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
      <div @wheel="onPickerWheel">
        <DatePicker
          v-model="picked"
          inline
          show-time
          hour-format="24"
          :pt="{ panel: { style: 'border: 0; padding: 0' } }"
        />
      </div>
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
