<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Textarea from 'primevue/textarea'
import AppMarkdown from './AppMarkdown.vue'
import { markdownRenderer } from '../../markdown'

// A Markdown text field: write, or look at the result.
const model = defineModel<string>({ required: true })
// `label` names the text field for screen readers (it has no visible label of its own).
// `fill`: as tall as its container, scrolling inside instead of growing with the text.
defineProps<{ rows?: number; label?: string; fill?: boolean }>()
const { t } = useI18n()
const mode = ref<'write' | 'preview'>('write')
// Load the parser while the user writes, so the preview doesn't wait for it.
void markdownRenderer()
</script>

<template>
  <div
    class="border border-surface-300 dark:border-surface-700"
    :class="{ 'flex flex-col h-full min-h-0': fill }"
  >
    <div
      class="flex items-center gap-1 px-1 border-b border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900"
      role="tablist"
    >
      <button
        v-for="tab in ['write', 'preview'] as const"
        :key="tab"
        type="button"
        role="tab"
        :aria-selected="mode === tab"
        class="px-3 py-1.5 text-sm border-b-2 -mb-px"
        :class="
          mode === tab
            ? 'border-primary text-primary font-medium'
            : 'border-transparent text-surface-500 hover:text-surface-900 dark:hover:text-surface-0'
        "
        @click="mode = tab"
      >
        {{ t(`markdown.${tab}`) }}
      </button>
      <span
        class="ml-auto min-w-0 truncate pr-2 text-xs text-surface-500 hidden sm:inline"
        :title="t('markdown.hint')"
        >{{ t('markdown.hint') }}</span
      >
    </div>
    <Textarea
      v-if="mode === 'write'"
      v-model="model"
      :aria-label="label"
      :rows="rows ?? 8"
      :auto-resize="!fill"
      class="w-full border-0! shadow-none! rounded-none!"
      :class="{ 'flex-1 min-h-0 resize-none': fill }"
    />
    <div v-else class="px-3 py-2 min-h-24" :class="{ 'flex-1 min-h-0 overflow-y-auto': fill }">
      <AppMarkdown v-if="model.trim()" :source="model" />
      <span v-else class="text-sm text-surface-500">{{ t('markdown.empty') }}</span>
    </div>
  </div>
</template>
