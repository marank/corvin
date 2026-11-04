<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import AppEmptyState from './AppEmptyState.vue'

// Placeholder for a detail page while it loads, or when loading failed (deleted,
// wrong link, server error), with a way back to the list.
defineProps<{ failed: boolean; backTo: string; backLabel: string }>()
const { t } = useI18n()
</script>

<template>
  <AppEmptyState v-if="failed" icon="pi pi-exclamation-circle" :message="t('common.loadFailed')">
    <router-link :to="backTo"><Button :label="backLabel" icon="pi pi-arrow-left" text size="small" /></router-link>
  </AppEmptyState>
  <div v-else class="flex justify-center py-16"><ProgressSpinner class="size-8!" stroke-width="4" /></div>
</template>
