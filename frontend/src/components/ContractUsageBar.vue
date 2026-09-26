<script setup lang="ts">
import ProgressBar from 'primevue/progressbar'
import AppNumberDisplay from './ui/AppNumberDisplay.vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ContractUsage } from '../api'

const props = defineProps<{ usage: ContractUsage }>()
const { t } = useI18n()

const pct = computed(() =>
  props.usage.included_hours > 0
    ? Math.min(100, (props.usage.used_hours / props.usage.included_hours) * 100)
    : 100,
)
const over = computed(() => props.usage.used_hours > props.usage.included_hours)
</script>

<template>
  <div>
    <div class="flex justify-between text-sm mb-1">
      <span>{{ t('contracts.used') }}: <AppNumberDisplay :value="usage.used_hours" :minimum-fraction-digits="2" />h</span>
      <span>{{ t('contracts.included') }}: <AppNumberDisplay :value="usage.included_hours" />h</span>
    </div>
    <ProgressBar :value="pct" :show-value="false" :pt="{ value: { class: over ? 'bg-red-500' : '' } }" />
    <p v-if="over" class="text-sm text-red-500 mt-1">
      {{ t('contracts.overage') }}: <AppNumberDisplay :value="usage.overage_hours" :minimum-fraction-digits="2" />h
    </p>
  </div>
</template>
