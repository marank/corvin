<script setup lang="ts">
import { useI18n } from 'vue-i18n'

// Mark: raven head from basic shapes (branding/corvin-mark.svg), wordmark in Space Grotesk.
withDefaults(defineProps<{ size?: 'md' | 'lg' }>(), { size: 'md' })
const { t } = useI18n()
</script>

<template>
  <span class="inline-flex items-center" :class="size === 'lg' ? 'gap-3' : 'gap-2'">
    <svg
      viewBox="4 4 56 56"
      class="w-auto"
      :class="size === 'lg' ? 'h-8' : 'h-5'"
      aria-hidden="true"
    >
      <path d="M32 4L60 32H26V4.646Z" class="fill-cyan-400 dark:fill-cyan-300" />
      <path d="M32 30H4.071A28 28 0 0 0 32 60Z" class="fill-blue-500 dark:fill-blue-400" />
      <path
        d="M32 32H4A28 28 0 0 1 32 4ZM23.8 20.4a3.4 3.4 0 1 0-6.8 0a3.4 3.4 0 1 0 6.8 0Z"
        fill-rule="evenodd"
        class="fill-purple-500 dark:fill-purple-400"
      />
    </svg>
    <span
      class="font-brand font-semibold leading-none"
      :class="size === 'lg' ? 'text-3xl' : 'text-xl'"
    >
      {{ t('app.title') }}
    </span>
  </span>
</template>
