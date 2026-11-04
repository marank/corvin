<script setup lang="ts">
// `backTo`/`backLabel` add a link to the parent list above the title (detail pages).
defineProps<{ title: string; subtitle?: string; backTo?: string; backLabel?: string }>()
</script>

<template>
  <div class="mb-4">
    <router-link v-if="backTo" :to="backTo" class="inline-flex items-center gap-1 text-sm text-surface-500 hover:text-primary mb-1">
      <i class="pi pi-arrow-left text-xs" />{{ backLabel }}
    </router-link>
    <div class="flex flex-wrap items-center gap-3">
      <div class="min-w-0">
        <h1 class="text-xl font-semibold truncate">{{ title }}</h1>
        <p v-if="subtitle" class="text-sm text-surface-500 truncate">{{ subtitle }}</p>
      </div>
      <div class="ms-auto flex gap-2">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>
