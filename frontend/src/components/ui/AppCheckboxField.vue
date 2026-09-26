<script setup lang="ts">
import Checkbox from 'primevue/checkbox'

defineProps<{ label: string; disabled?: boolean }>()
const model = defineModel<boolean | null | undefined>()
</script>

<template>
  <label class="flex items-center gap-2 min-h-10 self-end text-sm cursor-pointer" :class="disabled ? 'opacity-60 cursor-not-allowed' : ''">
    <Checkbox v-model="model" binary :disabled="disabled" />
    <span>{{ label }}</span>
  </label>
</template>
