<script setup lang="ts">
defineProps<{ label: string; error?: string; required?: boolean }>()
</script>

<template>
  <div class="flex flex-col gap-1">
    <label class="text-sm font-medium">
      {{ label }}<span v-if="required" class="text-red-500"> *</span>
    </label>
    <slot />
    <small v-if="error" class="text-red-500">{{ error }}</small>
  </div>
</template>
