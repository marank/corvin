<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
  <div class="flex flex-wrap items-center gap-3 mb-4">
    <div class="min-w-0">
      <h1 class="text-xl font-semibold truncate">{{ title }}</h1>
      <p v-if="subtitle" class="text-sm text-surface-500 truncate">{{ subtitle }}</p>
    </div>
    <div class="ms-auto flex gap-2">
      <slot name="actions" />
    </div>
  </div>
</template>
