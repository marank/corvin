<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'
import Select from 'primevue/select'
import { useAuthStore } from '../stores/auth'
import { setLocale, i18n } from '../i18n'
import TimerWidget from '../components/TimerWidget.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const navOpen = ref(false)
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

async function logout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="flex h-full">
    <!-- Desktop sidebar -->
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

    <!-- Mobile drawer -->
    <Drawer v-model:visible="navOpen" position="left" class="w-64">
      <nav class="py-2">
        <router-link
          v-for="item in items"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-4 py-3 text-sm"
          :class="isActive(item.to, item.exact) ? 'text-primary font-medium' : 'text-surface-600 dark:text-surface-300'"
          @click="navOpen = false"
        >
          <i :class="item.icon" />
          <span>{{ item.label }}</span>
        </router-link>
      </nav>
    </Drawer>

    <div class="flex-1 flex flex-col min-w-0">
      <!-- Topbar -->
      <header class="h-14 shrink-0 flex items-center gap-2 px-3 lg:px-5 border-b border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900">
        <Button icon="pi pi-bars" text class="lg:hidden" @click="navOpen = true" aria-label="menu" />
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
