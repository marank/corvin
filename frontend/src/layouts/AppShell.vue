<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import ProgressBar from 'primevue/progressbar'
import Select from 'primevue/select'
import AppIconButton from '../components/ui/AppIconButton.vue'
import AppLogo from '../components/ui/AppLogo.vue'
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
const sidebarNav = ref<HTMLElement | null>(null)
const indicatorStyle = ref({ top: '0px', height: '0px' })
const accountMenu = ref<InstanceType<typeof Menu>>()
// Thin progress bar while a lazy route loads, shown only if it takes noticeably long.
const navigating = ref(false)
let navigationTimer: ReturnType<typeof setTimeout> | undefined
const stopBefore = router.beforeEach(() => {
  clearTimeout(navigationTimer)
  navigationTimer = setTimeout(() => {
    navigating.value = true
  }, 120)
})
const stopAfter = router.afterEach(() => {
  clearTimeout(navigationTimer)
  navigating.value = false
})
const stopError = router.onError(() => {
  clearTimeout(navigationTimer)
  navigating.value = false
})
onBeforeUnmount(() => {
  stopBefore()
  stopAfter()
  stopError()
})
const accountItems = computed(() => [
  {
    label: t('settings.security'),
    icon: 'pi pi-shield',
    command: () => router.push('/settings/security'),
  },
  { separator: true },
  { label: t('auth.logout'), icon: 'pi pi-sign-out', command: logout },
])

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

const activeIndex = computed(() => items.value.findIndex((item) => isActive(item.to, item.exact)))

async function updateIndicator() {
  await nextTick()
  const nav = sidebarNav.value
  if (!nav) return
  const activeLink = nav.querySelector<HTMLElement>('.sidebar-active-item')
  if (activeLink) {
    indicatorStyle.value = {
      top: `${activeLink.offsetTop}px`,
      height: `${activeLink.offsetHeight}px`,
    }
  }
}

const onResize = () => void updateIndicator()
watch(activeIndex, updateIndicator, { immediate: true })
onMounted(() => {
  void formatting.load()
  window.addEventListener('resize', onResize)
})

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
  void router.push(to)
}

async function logout() {
  await auth.logout()
  await router.push('/login')
}
</script>

<template>
  <div class="flex h-full">
    <!-- Desktop sidebar (unchanged) -->
    <aside
      class="hidden lg:flex w-56 shrink-0 flex-col border-r border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900"
    >
      <div class="h-14 flex items-center px-4 border-b border-surface-200 dark:border-surface-800">
        <AppLogo />
      </div>
      <nav ref="sidebarNav" class="relative flex-1 overflow-y-auto py-2">
        <div
          class="absolute left-0 z-10 w-0.5 bg-primary transition-all duration-200 ease-out"
          :style="indicatorStyle"
        />
        <router-link
          v-for="item in items"
          :key="item.to"
          :to="item.to"
          class="relative flex items-center gap-3 px-4 py-2.5 text-sm"
          :class="
            isActive(item.to, item.exact)
              ? 'sidebar-active-item text-primary font-medium bg-primary/10'
              : 'text-surface-600 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-800'
          "
        >
          <i :class="item.icon" />
          <span>{{ item.label }}</span>
        </router-link>
      </nav>
    </aside>

    <!-- Full-screen tile menu (below lg, where the sidebar is hidden) -->
    <Teleport to="body">
      <div v-if="menuOpen" class="fixed inset-0 z-50 bg-white dark:bg-surface-950 flex flex-col">
        <div
          class="h-14 flex items-center px-4 border-b border-surface-200 dark:border-surface-800"
        >
          <AppLogo />
          <AppIconButton
            icon="pi pi-times"
            class="ms-auto"
            :label="t('common.close')"
            @click="menuOpen = false"
          />
        </div>
        <div class="flex-1 overflow-y-auto p-4 sm:p-8">
          <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 max-w-4xl mx-auto">
            <button
              v-for="item in items"
              :key="item.to"
              class="flex flex-col items-center justify-center gap-3 p-6 min-h-28 border border-surface-200 dark:border-surface-800 hover:border-primary hover:text-primary transition-colors"
              :class="
                isActive(item.to, item.exact)
                  ? 'text-primary border-primary'
                  : 'text-surface-600 dark:text-surface-300'
              "
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
      <header
        class="h-14 shrink-0 flex items-center gap-2 px-3 lg:px-5 border-b border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900"
      >
        <AppIconButton
          icon="pi pi-bars"
          class="lg:hidden"
          :label="t('common.menu')"
          @click="menuOpen = true"
        />
        <div class="flex-1" />
        <TimerWidget />
        <Select
          v-model="locale"
          :options="locales"
          option-label="label"
          option-value="value"
          :aria-label="t('common.language')"
          size="small"
        >
          <template #value="{ value }">
            <span class="inline-flex items-center gap-1.5"
              ><i class="pi pi-globe text-xs" />{{ String(value).toUpperCase() }}</span
            >
          </template>
        </Select>
        <AppIconButton
          :icon="dark ? 'pi pi-sun' : 'pi pi-moon'"
          :label="t('common.toggleTheme')"
          @click="toggleDark"
        />
        <Button
          icon="pi pi-user"
          text
          severity="secondary"
          :label="auth.user?.username"
          :aria-label="t('auth.account')"
          aria-haspopup="menu"
          class="max-sm:[&_.p-button-label]:hidden"
          @click="accountMenu?.toggle($event)"
        />
        <Menu ref="accountMenu" :model="accountItems" popup />
      </header>
      <ProgressBar v-if="navigating" mode="indeterminate" class="app-route-progress" />
      <main class="flex-1 overflow-y-auto p-4 lg:p-6">
        <router-view />
      </main>
    </div>
  </div>
</template>
