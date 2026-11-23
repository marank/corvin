<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import Message from 'primevue/message'
import AppLogo from '../components/ui/AppLogo.vue'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const otpCode = ref('')
const needsOtp = ref(false)
const error = ref('')
const loading = ref(false)

async function submit() {
  loading.value = true
  error.value = ''
  try {
    await auth.login(username.value, password.value, otpCode.value)
    router.push((route.query.next as string) ?? '/')
  } catch (e: any) {
    if ((e?.data as { requires_otp?: boolean })?.requires_otp) {
      needsOtp.value = true
      if (otpCode.value) error.value = t('auth.otpFailed')
    } else {
      error.value = t('auth.loginFailed')
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page min-h-full flex flex-col items-center justify-center gap-6 p-4">
    <form class="w-full max-w-sm flex flex-col gap-4 app-card shadow-sm" @submit.prevent="submit">
      <div class="h-1 login-accent" aria-hidden="true" />
      <div class="flex flex-col gap-4 px-6 pb-6 pt-3">
        <div class="flex flex-col items-center gap-2 py-2">
          <h1><AppLogo size="lg" /></h1>
          <p class="text-sm text-surface-500 text-center text-balance">{{ t('auth.tagline') }}</p>
        </div>
        <Message v-if="error" severity="error" size="small">{{ error }}</Message>
        <div class="flex flex-col gap-1">
          <label for="login-username" class="text-sm font-medium">{{ t('auth.username') }}</label>
          <InputText id="login-username" v-model="username" required autocomplete="username" autofocus />
        </div>
        <div class="flex flex-col gap-1">
          <label for="login-password" class="text-sm font-medium">{{ t('auth.password') }}</label>
          <Password v-model="password" input-id="login-password" required :feedback="false" toggle-mask autocomplete="current-password" class="w-full" input-class="w-full" />
        </div>
        <div v-if="needsOtp" class="flex flex-col gap-1">
          <label for="login-otp" class="text-sm font-medium">{{ t('auth.otpCode') }}</label>
          <InputText id="login-otp" v-model="otpCode" autocomplete="one-time-code" inputmode="numeric" autofocus />
          <small class="text-surface-500">{{ t('auth.otpHint') }}</small>
        </div>
        <Button type="submit" :label="t('auth.login')" :loading="loading" class="mt-2" />
      </div>
    </form>
  </div>
</template>

<!-- Not scoped: Vue drops `:global(.dark) .login-page` in scoped styles, so the dark backdrop never applied. -->
<style>
/* Brand colors as a soft backdrop and an accent line on the card. */
.login-page {
  background:
    radial-gradient(40rem 24rem at 15% 10%, color-mix(in srgb, #22d3ee 14%, transparent), transparent 70%),
    radial-gradient(40rem 24rem at 85% 90%, color-mix(in srgb, #a855f7 14%, transparent), transparent 70%),
    var(--p-surface-50);
}
.dark .login-page {
  background:
    radial-gradient(40rem 24rem at 15% 10%, color-mix(in srgb, #22d3ee 10%, transparent), transparent 70%),
    radial-gradient(40rem 24rem at 85% 90%, color-mix(in srgb, #a855f7 10%, transparent), transparent 70%),
    var(--p-surface-950);
}
.login-accent {
  background: linear-gradient(90deg, #22d3ee, #3b82f6, #a855f7);
}
</style>
