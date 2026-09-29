<script setup lang="ts">
import DatePicker from 'primevue/datepicker'
import { computed } from 'vue'

const props = defineProps<{ modelValue: string | null }>()
const emit = defineEmits<{ 'update:modelValue': [string | null] }>()

const value = computed({
  get: () => (props.modelValue ? new Date(props.modelValue) : null),
  set: (d: Date | Date[] | null) => {
    if (!d || Array.isArray(d)) return emit('update:modelValue', null)
    emit('update:modelValue', d.toISOString())
  },
})
</script>

<template>
  <DatePicker v-model="value" date-format="dd.mm.yy" show-time hour-format="24" show-icon class="w-full" />
</template>
