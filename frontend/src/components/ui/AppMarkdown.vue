<script setup lang="ts">
import { ref, watch } from 'vue'
import { markdownRenderer } from '../../markdown'

// Renders Markdown (see markdown.ts: raw HTML is escaped, links are checked).
const props = defineProps<{ source: string }>()
const html = ref('')

watch(
  () => props.source,
  async (source) => {
    const render = await markdownRenderer()
    if (source === props.source) html.value = render(source)
  },
  { immediate: true },
)
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html -- markdown-it output with raw HTML escaped (markdown.ts). -->
  <div class="app-markdown" v-html="html" />
</template>
