import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia, type Pinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ConfirmationService from 'primevue/confirmationservice'
import ConfirmDialog from 'primevue/confirmdialog'
import Toast from 'primevue/toast'
import ToastService from 'primevue/toastservice'
import { defineComponent, h, type Component } from 'vue'
import { createMemoryHistory, createRouter, RouterView, type Router } from 'vue-router'
import { i18n } from '../../i18n'
import { syncPrimeVueLocale } from '../../i18n/primevue'
import { setViewport } from './viewport'

export const t = i18n.global.t

export interface RenderOptions {
  /** Route pattern the component is mounted at, e.g. '/invoices/:id'. */
  path?: string
  /** URL opened first, e.g. '/invoices/inv-1?tab=payments'. Defaults to `path`. */
  url?: string
  props?: Record<string, unknown>
  viewport?: 'desktop' | 'mobile'
  pinia?: Pinia
  /** Components replaced for the test, e.g. a chart jsdom cannot draw. */
  stubs?: Record<string, Component>
}

const Elsewhere = defineComponent({
  setup: () => () => h('div', { 'data-testid': 'elsewhere' }),
})

// What App.vue provides around every page: toasts, the confirm dialog and the router view.
const Shell = defineComponent({
  setup: () => () => [h(Toast), h(ConfirmDialog), h(RouterView)],
})

/**
 * Mounts a view or component the way the app runs it: router (memory history), Pinia, i18n,
 * PrimeVue with toasts and confirmations. Any other URL renders an empty placeholder, so
 * navigation can be asserted with `router.currentRoute`.
 */
export async function render(component: Component, options: RenderOptions = {}) {
  setViewport(options.viewport ?? 'desktop')
  const path = options.path ?? '/'
  const router: Router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path, component, props: () => options.props ?? {} },
      { path: '/:pathMatch(.*)*', component: Elsewhere },
    ],
  })
  await router.push(options.url ?? path)
  await router.isReady()
  const pinia = options.pinia ?? createPinia()
  setActivePinia(pinia)
  const wrapper = mount(Shell, {
    attachTo: document.body,
    global: {
      stubs: options.stubs,
      plugins: [
        router,
        pinia,
        i18n,
        [PrimeVue, { theme: 'none' }],
        ToastService,
        ConfirmationService,
        { install: syncPrimeVueLocale },
      ],
    },
  })
  await settle()
  return { wrapper, router, pinia }
}

/** Lets pending requests, watchers and re-renders finish. */
export async function settle() {
  for (let i = 0; i < 5; i++) await flushPromises()
}
