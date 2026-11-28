<script setup lang="ts">
import { useI18n } from 'vue-i18n'

defineProps<{ message?: string; icon?: string }>()
const { t } = useI18n()
</script>

<template>
  <div class="flex flex-col items-center justify-center py-12 text-surface-400 gap-2">
    <i :class="icon ?? 'iconify lucide--inbox'" style="font-size: 2rem" />
    <p class="text-sm">{{ message ?? t('common.empty') }}</p>
    <slot />
  </div>
</template>
