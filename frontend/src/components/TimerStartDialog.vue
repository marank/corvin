<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import AppModal from './ui/AppModal.vue'
import AppFormField from './ui/AppFormField.vue'
import CustomerSelect from './CustomerSelect.vue'
import ProjectSelect from './ProjectSelect.vue'
import type { Project } from '../api'
import { useTimerStore } from '../stores/timer'
import { useNotify } from '../composables/useNotify'

const { t } = useI18n()
const timer = useTimerStore()
const notify = useNotify()
const modal = ref<InstanceType<typeof AppModal>>()
const form = ref({
  customer: null as string | null,
  project: null as string | null,
  description: '',
})
const starting = ref(false)

function open() {
  // Keep customer and project from the last start; most timers continue the same work.
  form.value.description = ''
  modal.value?.open()
}

// Picking a project first fills in its customer, which the start endpoint requires.
function onProjectSelect(project: Project | null) {
  if (project && !form.value.customer) form.value.customer = project.customer
}

async function start() {
  starting.value = true
  try {
    await timer.start(form.value.customer, form.value.project, form.value.description.trim())
    modal.value?.close()
  } catch (e) {
    notify.error(e)
  } finally {
    starting.value = false
  }
}

defineExpose({ open })
</script>

<template>
  <AppModal
    ref="modal"
    :form="form"
    :title="t('time.startTimer')"
    :confirm-label="t('time.startNow')"
    :loading="starting"
    @confirm="start"
  >
    <form class="flex flex-col gap-4" @submit.prevent="start">
      <AppFormField field="description" :label="t('time.description')">
        <!-- eslint-disable-next-line vuejs-accessibility/no-autofocus -- the dialog opens to start a timer; its first field gets the focus. -->
        <InputText v-model="form.description" class="w-full" autofocus />
      </AppFormField>
      <AppFormField field="customer" :label="t('projects.customer')">
        <CustomerSelect v-model="form.customer" />
      </AppFormField>
      <AppFormField field="project" :label="t('projects.project')">
        <ProjectSelect
          v-model="form.project"
          :customer-id="form.customer"
          @select="onProjectSelect"
        />
      </AppFormField>
      <p class="text-xs text-surface-500">{{ t('time.startHint') }}</p>
    </form>
  </AppModal>
</template>
