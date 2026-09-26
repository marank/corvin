<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
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
      if (otpCode.value) error.value = t('auth.loginFailed')
    } else {
      error.value = t('auth.loginFailed')
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-full flex items-center justify-center p-4">
    <form class="w-full max-w-sm flex flex-col gap-4 border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-6" @submit.prevent="submit">
      <h1 class="text-xl font-semibold">{{ t('app.title') }}</h1>
      <InputText v-model="username" :placeholder="t('auth.username')" required autocomplete="username" />
      <Password v-model="password" :placeholder="t('auth.password')" required :feedback="false" toggle-mask autocomplete="current-password" class="w-full" input-class="w-full" />
      <InputText v-if="needsOtp" v-model="otpCode" :placeholder="t('auth.otpCode')" autocomplete="one-time-code" />
      <p v-if="error" class="text-sm text-red-500">{{ error }}</p>
      <Button type="submit" :label="t('auth.login')" :loading="loading" />
    </form>
  </div>
</template>
