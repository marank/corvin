/// <reference types="vitest/config" />
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    dedupe: ['@codemirror/state', '@codemirror/view'],
  },
  optimizeDeps: {
    include: [
      'codemirror',
      '@codemirror/state',
      '@codemirror/view',
      '@codemirror/lang-html',
      '@codemirror/lang-css',
    ],
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Django CSRF checks Origin; make proxied requests look same-origin.
        headers: { origin: 'http://localhost:8000' },
      },
      '/django-admin': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        headers: { origin: 'http://localhost:8000' },
      },
      '/django-static': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.ts'],
    setupFiles: ['src/__tests__/setup.ts'],
    // One time zone and one default locale (PrimeVue's number inputs format with it), so the
    // results don't depend on the machine.
    env: { TZ: 'Europe/Berlin', LC_ALL: 'en_US.UTF-8' },
    coverage: {
      provider: 'v8',
      reporter: ['text-summary'],
      include: ['src/**'],
      exclude: [
        'src/main.ts', // bootstrapping
        'src/**/*.d.ts', // types only, incl. the generated src/api/schema.d.ts
        'src/i18n/locales/**', // translation JSON
        'src/**/*.test.ts',
        'src/__tests__/**',
      ],
      // The house default; views are tested through the UI against a faked backend (src/__tests__/helpers).
      thresholds: { lines: 90, statements: 90, functions: 85, branches: 85 },
    },
  },
})
