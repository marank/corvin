<script setup lang="ts">
import { onMounted } from 'vue'
import { useTimerStore } from '../stores/timer'
import AppIconButton from './ui/AppIconButton.vue'
import { useI18n } from 'vue-i18n'

const timer = useTimerStore()
const { t } = useI18n()

onMounted(() => timer.refresh())
</script>

<template>
  <div v-if="timer.running" class="flex items-center gap-2 border border-primary px-2 py-1">
    <template v-if="timer.running.is_paused">
      <span class="flex gap-0.5 animate-breathe">
        <span class="w-1 h-3 bg-yellow-500" />
        <span class="w-1 h-3 bg-yellow-500" />
      </span>
    </template>
    <span v-else class="w-0 h-0 border-t-[6px] border-t-transparent border-b-[6px] border-b-transparent border-l-[10px] border-l-green-500 animate-breathe" />
    <span class="text-sm font-mono">{{ timer.elapsedText }}<span v-if="timer.running.is_paused" class="text-surface-500"> ({{ timer.breakElapsedText }})</span></span>
    <span v-if="timer.running.description" class="hidden md:inline text-xs text-surface-500 truncate max-w-40">{{ timer.running.description }}</span>
    <AppIconButton v-if="timer.running.is_paused" icon="pi pi-play" :aria-label="t('time.resumeTimer')" @click="timer.resume()" />
    <AppIconButton v-else icon="pi pi-pause" :aria-label="t('time.pauseTimer')" @click="timer.pause()" />
    <AppIconButton icon="pi pi-stop" :aria-label="t('time.stopTimer')" @click="timer.stop()" />
  </div>
</template>
