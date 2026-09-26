<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Select from 'primevue/select'
import { useAuthStore } from '../stores/auth'
import { useFormattingStore } from '../stores/formatting'
import { setLocale, i18n } from '../i18n'
import TimerWidget from '../components/TimerWidget.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const formatting = useFormattingStore()
const menuOpen = ref(false)
const dark = ref(document.documentElement.classList.contains('dark'))

const items = computed(() => [
  { to: '/', icon: 'pi pi-chart-bar', label: t('nav.dashboard'), exact: true },
  { to: '/customers', icon: 'pi pi-users', label: t('nav.customers') },
  { to: '/projects', icon: 'pi pi-briefcase', label: t('nav.projects') },
  { to: '/tasks', icon: 'pi pi-check-square', label: t('nav.tasks') },
  { to: '/time', icon: 'pi pi-clock', label: t('nav.timetracking') },
  { to: '/visits', icon: 'pi pi-map-marker', label: t('nav.visits') },
  { to: '/contracts', icon: 'pi pi-file', label: t('nav.contracts') },
  { to: '/invoices', icon: 'pi pi-money-bill', label: t('nav.invoices') },
  { to: '/templates', icon: 'pi pi-palette', label: t('nav.templates') },
  { to: '/settings', icon: 'pi pi-cog', label: t('nav.settings') },
])

const locales = [
  { label: 'Deutsch', value: 'de' },
  { label: 'English', value: 'en' },
]
onMounted(() => formatting.load())

const locale = computed({
  get: () => i18n.global.locale.value,
  set: (v: string) => setLocale(v),
})

function toggleDark() {
  dark.value = !dark.value
  document.documentElement.classList.toggle('dark', dark.value)
  localStorage.setItem('dark', dark.value ? '1' : '0')
}

function isActive(to: string, exact?: boolean) {
  return exact ? route.path === to : route.path.startsWith(to)
}

function navigate(to: string) {
  menuOpen.value = false
  router.push(to)
}

async function logout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="flex h-full">
    <!-- Desktop sidebar (unchanged) -->
    <aside class="hidden lg:flex w-56 shrink-0 flex-col border-r border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900">
      <div class="h-14 flex items-center px-4 border-b border-surface-200 dark:border-surface-800 font-semibold">
        {{ t('app.title') }}
      </div>
      <nav class="flex-1 overflow-y-auto py-2">
        <router-link
          v-for="item in items"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-4 py-2.5 text-sm border-l-2"
          :class="isActive(item.to, item.exact)
            ? 'border-primary text-primary font-medium bg-blue-50 dark:bg-surface-800'
            : 'border-transparent text-surface-600 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-800'"
        >
          <i :class="item.icon" />
          <span>{{ item.label }}</span>
        </router-link>
      </nav>
    </aside>

    <!-- Full-screen tile menu (all viewports) -->
    <Teleport to="body">
      <div
        v-if="menuOpen"
        class="fixed inset-0 z-50 bg-white dark:bg-surface-950 flex flex-col"
      >
        <div class="h-14 flex items-center px-4 border-b border-surface-200 dark:border-surface-800">
          <span class="font-semibold">{{ t('app.title') }}</span>
          <Button icon="pi pi-times" text class="ms-auto" aria-label="close" @click="menuOpen = false" />
        </div>
        <div class="flex-1 overflow-y-auto p-4 sm:p-8">
          <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 max-w-4xl mx-auto">
            <button
              v-for="item in items"
              :key="item.to"
              class="flex flex-col items-center justify-center gap-3 p-6 min-h-28 border border-surface-200 dark:border-surface-800 hover:border-primary hover:text-primary transition-colors"
              :class="isActive(item.to, item.exact) ? 'text-primary border-primary' : 'text-surface-600 dark:text-surface-300'"
              @click="navigate(item.to)"
            >
              <i :class="item.icon" style="font-size: 1.75rem" />
              <span class="text-sm font-medium">{{ item.label }}</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <div class="flex-1 flex flex-col min-w-0">
      <!-- Topbar -->
      <header class="h-14 shrink-0 flex items-center gap-2 px-3 lg:px-5 border-b border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900">
        <Button icon="pi pi-bars" text @click="menuOpen = true" aria-label="menu" />
        <div class="flex-1" />
        <TimerWidget />
        <Select
          v-model="locale"
          :options="locales"
          option-label="label"
          option-value="value"
          class="w-28"
          size="small"
        />
        <Button :icon="dark ? 'pi pi-sun' : 'pi pi-moon'" text @click="toggleDark" aria-label="theme" />
        <Button icon="pi pi-sign-out" text :label="t('auth.logout')" class="hidden sm:inline-flex" @click="logout" />
        <Button icon="pi pi-sign-out" text class="sm:hidden" @click="logout" aria-label="logout" />
      </header>
      <main class="flex-1 overflow-y-auto p-4 lg:p-6">
        <router-view />
      </main>
    </div>
  </div>
</template>
