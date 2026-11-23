import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, vi } from 'vitest'
import { clearFormErrors } from '../composables/formErrors'
import { NOW } from './helpers/time'
import { setViewport } from './helpers/viewport'

// Every test runs at NOW. Only Date is faked, so promises and PrimeVue's own timeouts keep running; tests that need to
// step intervals switch to full fake timers themselves.

// jsdom has no ResizeObserver (InvoicePreviewFrame fits its page to the frame width with one).
globalThis.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

enableAutoUnmount(afterEach)

beforeEach(() => {
  // Teleported leftovers (toasts, overlays) of the previous test; its app is unmounted by now.
  document.body.innerHTML = ''
  vi.useFakeTimers({ toFake: ['Date'], now: NOW })
  setViewport('desktop')
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  clearFormErrors()
  localStorage.clear()
})
