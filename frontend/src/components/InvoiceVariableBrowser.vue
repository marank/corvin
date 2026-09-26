<script setup lang="ts">
export interface VariableGroup {
  label: string
  entries: { label: string; code: string }[]
}

defineProps<{ groups: VariableGroup[] }>()
defineEmits<{ insert: [code: string] }>()
</script>

<template>
  <details class="border-t border-surface-200 dark:border-surface-800 text-xs">
    <summary class="cursor-pointer text-surface-500 p-2"><slot name="title" /></summary>
    <div class="p-2 max-h-56 overflow-auto">
      <section v-for="group in groups" :key="group.label" class="mb-3 last:mb-0">
        <h4 class="font-medium mb-1">{{ group.label }}</h4>
        <div class="flex flex-wrap gap-1">
          <button v-for="entry in group.entries" :key="entry.code" type="button" class="font-mono border border-surface-200 dark:border-surface-700 px-2 py-1 hover:bg-surface-100 dark:hover:bg-surface-800" :title="entry.code" @click="$emit('insert', entry.code)">
            {{ entry.label }}
          </button>
        </div>
      </section>
    </div>
  </details>
</template>
