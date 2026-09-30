<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import type { TimeEntry } from '../api'
import { useTimerStore } from '../stores/timer'
import { useSettingsStore } from '../stores/settings'
import AppIconButton from './ui/AppIconButton.vue'
import AppModal from './ui/AppModal.vue'
import TimeEntryForm from './TimeEntryForm.vue'
import { useI18n } from 'vue-i18n'

const timer = useTimerStore()
const settings = useSettingsStore()
const { t } = useI18n()
const stoppedEntry = ref<TimeEntry | null>(null)
const askModal = ref<InstanceType<typeof AppModal>>()
const entryModal = ref<InstanceType<typeof AppModal>>()

onMounted(async () => {
  await settings.load()
  await timer.refresh()
})

async function stop() {
  const entry = await timer.stop()
  if (!entry) return
  stoppedEntry.value = entry
  if (settings.openStoppedTimeEntry === 'yes') entryModal.value?.open()
  else if (settings.openStoppedTimeEntry === 'ask') askModal.value?.open()
}

function answerOpenEntry(open: boolean) {
  askModal.value?.close()
  if (open) entryModal.value?.open()
}

function entrySaved() {
  entryModal.value?.close()
  stoppedEntry.value = null
  timer.version++
}
</script>

<template>
  <div v-if="timer.running || settings.alwaysShowTimerWidget" class="flex items-center gap-2 border border-primary px-2 py-1">
    <template v-if="timer.running?.is_paused">
      <span class="flex gap-0.5 animate-breathe">
        <span class="w-1 h-3 bg-yellow-500" />
        <span class="w-1 h-3 bg-yellow-500" />
      </span>
    </template>
    <span v-else-if="timer.running" class="w-0 h-0 border-t-[6px] border-t-transparent border-b-[6px] border-b-transparent border-l-[10px] border-l-green-500 animate-breathe" />
    <span v-else class="w-0 h-0 border-t-[6px] border-t-transparent border-b-[6px] border-b-transparent border-l-[10px] border-l-surface-400" />
    <span class="text-sm font-mono">{{ timer.elapsedText }}<span v-if="timer.running?.is_paused" class="text-surface-500"> ({{ timer.breakElapsedText }})</span></span>
    <span v-if="timer.running?.description" class="hidden md:inline text-xs text-surface-500 truncate max-w-40">{{ timer.running.description }}</span>
    <template v-if="timer.running">
      <AppIconButton v-if="timer.running.is_paused" icon="pi pi-play" :aria-label="t('time.resumeTimer')" @click="timer.resume()" />
      <AppIconButton v-else icon="pi pi-pause" :aria-label="t('time.pauseTimer')" @click="timer.pause()" />
      <AppIconButton icon="pi pi-stop" :aria-label="t('time.stopTimer')" @click="stop" />
    </template>
    <AppIconButton v-else icon="pi pi-play" :aria-label="t('time.startTimer')" @click="timer.start()" />
  </div>

  <AppModal ref="askModal" :title="t('time.openStoppedEntryTitle')" size="sm" :show-footer="false">
    <p>{{ t('time.openStoppedEntryPrompt') }}</p>
    <div class="flex justify-end gap-2 mt-6">
      <Button :label="t('common.no')" severity="secondary" text class="min-w-20" @click="answerOpenEntry(false)" />
      <Button :label="t('common.yes')" class="min-w-20" @click="answerOpenEntry(true)" />
    </div>
  </AppModal>

  <AppModal ref="entryModal" :title="t('time.editEntry')" size="lg" :show-footer="false" @closed="stoppedEntry = null">
    <TimeEntryForm v-if="stoppedEntry" :entry="stoppedEntry" @saved="entrySaved" @cancel="entryModal?.close()" />
  </AppModal>
</template>
