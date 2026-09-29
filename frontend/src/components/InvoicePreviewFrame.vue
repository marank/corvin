<script setup lang="ts">
defineProps<{ url: string; mode?: 'html' | 'pdf' }>()
</script>

<template>
  <iframe v-if="mode !== 'pdf'" :src="url" class="w-full h-full border-0 bg-white" title="preview" />
  <iframe v-else :src="url" class="w-full h-full border-0 bg-neutral-200" title="PDF preview" />
</template>
