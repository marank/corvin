import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import App from './App.vue'
import router from './router'
import { i18n, setLocale } from './i18n'
import { FlatPreset } from './theme/preset'
import './style.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(i18n)
app.use(ToastService)
app.use(ConfirmationService)
app.use(PrimeVue, {
  theme: {
    preset: FlatPreset,
    options: {
      darkModeSelector: '.dark',
    },
  },
})

if (localStorage.getItem('dark') === '1') {
  document.documentElement.classList.add('dark')
}
setLocale(localStorage.getItem('locale') ?? 'de')

app.mount('#app')
