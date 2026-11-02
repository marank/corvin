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
      'codemirror', '@codemirror/state', '@codemirror/view',
      '@codemirror/lang-html', '@codemirror/lang-css',
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
    },
  },
})
