import { createI18n } from 'vue-i18n'
import de from './locales/de.json'
import en from './locales/en.json'

export const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem('locale') ?? 'de',
  fallbackLocale: 'en',
  messages: { de, en },
})

export function setLocale(locale: string) {
  i18n.global.locale.value = locale as 'de' | 'en'
  localStorage.setItem('locale', locale)
  document.documentElement.lang = locale
}
