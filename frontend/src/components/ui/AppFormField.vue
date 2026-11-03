<script setup lang="ts">
import { computed, onMounted, onUnmounted, useId } from 'vue'
import { formErrors, registerField, unregisterField } from '../../composables/formErrors'

// `field` is the API field name; server-side errors for it are shown here.
const props = defineProps<{ label: string; error?: string; required?: boolean; field?: string }>()
const labelId = useId()
const shownError = computed(() => props.error || (props.field ? formErrors[props.field] : undefined))

onMounted(() => props.field && registerField(props.field))
onUnmounted(() => props.field && unregisterField(props.field))
</script>

<template>
  <div class="flex flex-col gap-1" role="group" :aria-labelledby="labelId">
    <label :id="labelId" class="text-sm font-medium">
      {{ label }}<span v-if="required" class="text-red-500"> *</span>
    </label>
    <slot />
    <small v-if="shownError" class="text-red-500">{{ shownError }}</small>
  </div>
</template>
