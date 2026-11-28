<script setup lang="ts">
// `backTo`/`backLabel` add a link to the parent list above the title (detail pages);
// the `title-end` slot holds status tags next to the title, away from the action buttons.
defineProps<{ title: string; subtitle?: string; backTo?: string; backLabel?: string }>()
</script>

<template>
  <div class="mb-4">
    <router-link
      v-if="backTo"
      :to="backTo"
      class="inline-flex items-center gap-1 text-sm text-surface-500 hover:text-primary mb-1"
    >
      <i class="iconify lucide--arrow-left text-xs" />{{ backLabel }}
    </router-link>
    <div class="flex flex-wrap items-center gap-3">
      <div class="min-w-0">
        <div class="flex items-center gap-2 min-w-0">
          <h1 class="text-xl font-semibold truncate">{{ title }}</h1>
          <slot name="title-end" />
        </div>
        <p v-if="subtitle" class="text-sm text-surface-500 truncate">{{ subtitle }}</p>
      </div>
      <div class="ms-auto flex flex-wrap gap-2">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>
