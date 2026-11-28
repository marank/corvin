<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import type { TimeEntry } from '../api'
import { useTimerStore } from '../stores/timer'
import { useSettingsStore } from '../stores/settings'
import AppIconButton from './ui/AppIconButton.vue'
import AppModal from './ui/AppModal.vue'
import TimeEntryForm from './TimeEntryForm.vue'
import TimerStartDialog from './TimerStartDialog.vue'
import { useNotify } from '../composables/useNotify'
import { useI18n } from 'vue-i18n'

const timer = useTimerStore()
const settings = useSettingsStore()
const { t } = useI18n()
const notify = useNotify()
const stoppedEntry = ref<TimeEntry | null>(null)
const askModal = ref<InstanceType<typeof AppModal>>()
const entryModal = ref<InstanceType<typeof AppModal>>()
const entryForm = ref<InstanceType<typeof TimeEntryForm>>()
const startDialog = ref<InstanceType<typeof TimerStartDialog>>()

onMounted(async () => {
  await settings.load()
  await timer.refresh()
})

async function run(action: () => Promise<unknown>) {
  try {
    await action()
  } catch (e) {
    notify.error(e)
  }
}

// Starting and stopping can be triggered from any page (timer store); the
// dialogs live here so the flow is the same everywhere.
watch(
  () => timer.startRequests,
  () => startDialog.value?.open(),
)
watch(
  () => timer.lastStopped,
  (entry) => {
    if (!entry) return
    stoppedEntry.value = entry
    timer.lastStopped = null
    if (settings.openStoppedTimeEntry === 'yes') entryModal.value?.open()
    else if (settings.openStoppedTimeEntry === 'ask') askModal.value?.open()
  },
)

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
  <div
    v-if="timer.running || settings.alwaysShowTimerWidget"
    class="flex items-center gap-2 border border-primary px-2 py-1"
  >
    <template v-if="timer.running?.is_paused">
      <span class="flex gap-0.5 animate-breathe">
        <span class="w-1 h-3 bg-yellow-500" />
        <span class="w-1 h-3 bg-yellow-500" />
      </span>
    </template>
    <span
      v-else-if="timer.running"
      class="w-0 h-0 border-t-[6px] border-t-transparent border-b-[6px] border-b-transparent border-l-[10px] border-l-green-500 animate-breathe"
    />
    <span
      v-else
      class="w-0 h-0 border-t-[6px] border-t-transparent border-b-[6px] border-b-transparent border-l-[10px] border-l-surface-400"
    />
    <span class="text-sm font-mono"
      >{{ timer.elapsedText
      }}<span v-if="timer.running?.is_paused" class="text-surface-500">
        ({{ timer.breakElapsedText }})</span
      ></span
    >
    <span
      v-if="timer.running?.description || timer.running?.project_name"
      class="hidden md:inline text-xs text-surface-500 truncate max-w-40"
      >{{ timer.running.description || timer.running.project_name }}</span
    >
    <template v-if="timer.running">
      <AppIconButton
        v-if="timer.running.is_paused"
        icon="iconify lucide--play"
        :label="t('time.resumeTimer')"
        @click="run(timer.resume)"
      />
      <AppIconButton
        v-else
        icon="iconify lucide--pause"
        :label="t('time.pauseTimer')"
        @click="run(timer.pause)"
      />
      <AppIconButton
        icon="iconify lucide--square"
        :label="t('time.stopTimer')"
        @click="run(timer.stop)"
      />
    </template>
    <AppIconButton
      v-else
      icon="iconify lucide--play"
      :label="t('time.startTimer')"
      @click="timer.requestStart()"
    />
  </div>

  <TimerStartDialog ref="startDialog" />

  <AppModal ref="askModal" :title="t('time.openStoppedEntryTitle')" size="sm">
    <p>{{ t('time.openStoppedEntryPrompt') }}</p>
    <template #footer>
      <Button :label="t('common.no')" text class="min-w-20" @click="answerOpenEntry(false)" />
      <Button :label="t('common.yes')" class="min-w-20" @click="answerOpenEntry(true)" />
    </template>
  </AppModal>

  <AppModal
    ref="entryModal"
    :form="entryForm?.state"
    :loading="entryForm?.saving"
    :title="t('time.editEntry')"
    size="lg"
    @confirm="entryForm?.save()"
    @closed="stoppedEntry = null"
  >
    <TimeEntryForm v-if="stoppedEntry" ref="entryForm" :entry="stoppedEntry" @saved="entrySaved" />
  </AppModal>
</template>
