<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import QRCode from 'qrcode'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppFormField from '../../components/ui/AppFormField.vue'
import AppModal from '../../components/ui/AppModal.vue'
import AppDateTimeDisplay from '../../components/ui/AppDateTimeDisplay.vue'
import { securityApi } from '../../api'
import { useAuthStore } from '../../stores/auth'
import { useNotify } from '../../composables/useNotify'
import { useConfirm } from 'primevue/useconfirm'

const { t } = useI18n()
const notify = useNotify()
const confirm = useConfirm()
const auth = useAuthStore()

const oldPw = ref('')
const newPw = ref('')
const totpModal = ref<InstanceType<typeof AppModal>>()
const disableModal = ref<InstanceType<typeof AppModal>>()
const qrDataUrl = ref('')
const totpCode = ref('')
const disablePassword = ref('')
const backupCodes = ref<string[]>([])
const sessions = ref<{ key: string; expire_date: string; current: boolean }[]>([])

onMounted(async () => {
  sessions.value = await securityApi.sessions()
})

async function changePassword() {
  try {
    await securityApi.changePassword(oldPw.value, newPw.value)
    oldPw.value = newPw.value = ''
    notify.ok(t('settings.passwordChanged'))
  } catch (e) {
    notify.error(e)
  }
}

async function startTotp() {
  try {
    const { config_url } = await securityApi.totpSetup()
    qrDataUrl.value = await QRCode.toDataURL(config_url, { width: 220, margin: 0 })
    totpCode.value = ''
    backupCodes.value = []
    totpModal.value?.open()
  } catch (e) {
    notify.error(e)
  }
}

async function confirmTotp() {
  try {
    const res = await securityApi.totpConfirm(totpCode.value)
    backupCodes.value = res.backup_codes
    if (auth.user) auth.user.totp_enabled = true
  } catch (e) {
    notify.error(e)
  }
}

async function disableTotp() {
  try {
    await securityApi.totpDisable(disablePassword.value)
    disableModal.value?.close()
    if (auth.user) auth.user.totp_enabled = false
    notify.ok(t('settings.totpDisabled'))
  } catch (e) {
    notify.error(e)
  }
}

function revokeOthers() {
  confirm.require({
    header: t('settings.revokeOthers'),
    message: t('settings.revokeOthersConfirm'),
    icon: 'pi pi-sign-out',
    rejectLabel: t('common.cancel'),
    rejectProps: { text: true },
    acceptLabel: t('settings.revokeOthers'),
    accept: async () => {
      try {
        await securityApi.revokeAllSessions()
        sessions.value = await securityApi.sessions()
        notify.ok(t('settings.revokedOthers'))
      } catch (e) {
        notify.error(e)
      }
    },
  })
}
</script>

<template>
  <div>
    <AppPageHeader back-to="/settings" :back-label="t('nav.settings')" :title="t('settings.security')" />

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl">
      <section class="app-card p-4">
        <h2 class="font-semibold mb-3">{{ t('settings.changePassword') }}</h2>
        <div class="flex flex-col gap-3">
          <AppFormField :label="t('settings.oldPassword')"><Password v-model="oldPw" :feedback="false" class="w-full" input-class="w-full" /></AppFormField>
          <AppFormField :label="t('settings.newPassword')"><Password v-model="newPw" class="w-full" input-class="w-full" /></AppFormField>
          <Button :label="t('common.save')" class="self-start" :disabled="!oldPw || !newPw" @click="changePassword" />
        </div>
      </section>

      <section class="app-card p-4">
        <h2 class="font-semibold mb-3">{{ t('settings.totp') }}</h2>
        <p class="text-sm text-surface-500 mb-3">
          {{ auth.user?.totp_enabled ? t('settings.totpEnabled') : t('settings.totpDisabled') }}
        </p>
        <Button v-if="!auth.user?.totp_enabled" :label="t('settings.totpSetup')" @click="startTotp" />
        <Button v-else :label="t('settings.totpDisable')" severity="danger" text @click="disableModal?.open()" />
      </section>

      <section class="app-card p-4 md:col-span-2">
        <div class="flex items-center justify-between mb-3">
          <h2 class="font-semibold">{{ t('settings.sessions') }}</h2>
          <Button :label="t('settings.revokeOthers')" size="small" text @click="revokeOthers" />
        </div>
        <ul class="divide-y divide-surface-200 dark:divide-surface-800 text-sm">
          <li v-for="s in sessions" :key="s.key" class="py-2 flex justify-between">
            <span class="font-mono truncate max-w-72">{{ s.key }}</span>
            <span class="flex items-center gap-2 text-surface-500">
              <Tag v-if="s.current" :value="t('settings.currentSession')" severity="success" />
              {{ t('settings.expires') }} <AppDateTimeDisplay :value="s.expire_date" type="datetime" />
            </span>
          </li>
        </ul>
      </section>
    </div>

    <AppModal ref="totpModal" :title="t('settings.totp')">
      <div v-if="!backupCodes.length" class="flex flex-col items-center gap-4">
        <img v-if="qrDataUrl" :src="qrDataUrl" :alt="t('settings.totpScan')" />
        <p class="text-sm text-surface-500">{{ t('settings.totpScan') }}</p>
        <AppFormField :label="t('settings.totpConfirm')" class="w-full">
          <InputText v-model="totpCode" class="w-full" autocomplete="one-time-code" inputmode="numeric" @keydown.enter="totpCode && confirmTotp()" />
        </AppFormField>
      </div>
      <div v-else>
        <p class="text-sm mb-3">{{ t('settings.backupCodes') }}</p>
        <div class="grid grid-cols-2 gap-1 font-mono text-sm">
          <code v-for="c in backupCodes" :key="c">{{ c }}</code>
        </div>
      </div>
      <template #footer>
        <template v-if="!backupCodes.length">
          <Button :label="t('common.cancel')" text @click="totpModal?.close()" />
          <Button :label="t('common.confirm')" :disabled="!totpCode" @click="confirmTotp" />
        </template>
        <Button v-else :label="t('common.done')" @click="totpModal?.close()" />
      </template>
    </AppModal>

    <AppModal ref="disableModal" :title="t('settings.totpDisableTitle')" :confirm-label="t('settings.totpDisable')" @confirm="disableTotp">
      <AppFormField :label="t('auth.password')"><Password v-model="disablePassword" :feedback="false" class="w-full" input-class="w-full" /></AppFormField>
    </AppModal>
  </div>
</template>
