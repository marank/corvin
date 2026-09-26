<script setup lang="ts">
import DatePicker from 'primevue/datepicker'
import { computed } from 'vue'

const props = defineProps<{ modelValue: string | null }>()
const emit = defineEmits<{ 'update:modelValue': [string | null] }>()

const value = computed({
  get: () => (props.modelValue ? new Date(props.modelValue + 'T00:00:00') : null),
  set: (d: Date | Date[] | null) => {
    if (!d || Array.isArray(d)) return emit('update:modelValue', null)
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    emit('update:modelValue', `${y}-${m}-${day}`)
  },
})
</script>

<template>
  <DatePicker v-model="value" date-format="dd.mm.yy" show-icon class="w-full" />
</template>
