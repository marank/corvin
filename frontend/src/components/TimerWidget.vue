<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useTimerStore } from '../stores/timer'
import AppIconButton from './ui/AppIconButton.vue'
import { useI18n } from 'vue-i18n'

const timer = useTimerStore()
const { t } = useI18n()

onMounted(() => timer.refresh())

const text = computed(() => {
  const s = Math.floor(timer.elapsed / 1000)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
})
</script>

<template>
  <div v-if="timer.running" class="flex items-center gap-2 border border-primary px-2 py-1">
    <span class="w-2 h-2 bg-red-500 animate-pulse" />
    <span class="text-sm font-mono">{{ text }}</span>
    <span class="hidden md:inline text-xs text-surface-500 truncate max-w-40">{{ timer.running.description }}</span>
    <AppIconButton icon="pi pi-stop" :aria-label="t('time.stopTimer')" @click="timer.stop()" />
  </div>
</template>
