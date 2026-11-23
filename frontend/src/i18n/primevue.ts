import { toRaw, watch, type App } from 'vue'
import type { PrimeVueLocaleOptions } from 'primevue/config'
import { i18n } from './index'

// PrimeVue's built-in texts (date picker, paginator, aria labels) per app locale.
// Keys not listed fall back to PrimeVue's English defaults.
export const primeVueLocales: Record<string, Record<string, unknown>> = {
  de: {
    firstDayOfWeek: 1,
    dayNames: ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'],
    dayNamesShort: ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'],
    dayNamesMin: ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'],
    monthNames: [
      'Januar',
      'Februar',
      'März',
      'April',
      'Mai',
      'Juni',
      'Juli',
      'August',
      'September',
      'Oktober',
      'November',
      'Dezember',
    ],
    monthNamesShort: [
      'Jan',
      'Feb',
      'Mär',
      'Apr',
      'Mai',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Okt',
      'Nov',
      'Dez',
    ],
    today: 'Heute',
    clear: 'Leeren',
    weekHeader: 'KW',
    chooseDate: 'Datum wählen',
    chooseTime: 'Uhrzeit wählen',
    chooseMonth: 'Monat wählen',
    chooseYear: 'Jahr wählen',
    accept: 'Ja',
    reject: 'Nein',
    choose: 'Auswählen',
    cancel: 'Abbrechen',
    completed: 'Fertig',
    pending: 'Ausstehend',
    emptyMessage: 'Keine Optionen',
    emptyFilterMessage: 'Keine Ergebnisse',
    emptySearchMessage: 'Keine Ergebnisse',
    searchMessage: '{0} Ergebnisse',
    selectionMessage: '{0} ausgewählt',
    emptySelectionMessage: 'Nichts ausgewählt',
    aria: {
      close: 'Schließen',
      previous: 'Zurück',
      next: 'Weiter',
      navigation: 'Navigation',
      prevPageLabel: 'Vorherige Seite',
      nextPageLabel: 'Nächste Seite',
      firstPageLabel: 'Erste Seite',
      lastPageLabel: 'Letzte Seite',
      pageLabel: 'Seite {page}',
      rowsPerPageLabel: 'Zeilen pro Seite',
      prevMonth: 'Vorheriger Monat',
      nextMonth: 'Nächster Monat',
      prevYear: 'Vorheriges Jahr',
      nextYear: 'Nächstes Jahr',
      prevDecade: 'Vorheriges Jahrzehnt',
      nextDecade: 'Nächstes Jahrzehnt',
      prevHour: 'Vorherige Stunde',
      nextHour: 'Nächste Stunde',
      prevMinute: 'Vorherige Minute',
      nextMinute: 'Nächste Minute',
      showMonthPicker: 'Monatsauswahl',
      showYearPicker: 'Jahresauswahl',
      selectAll: 'Alle auswählen',
      unselectAll: 'Alle abwählen',
      selectRow: 'Zeile auswählen',
      unselectRow: 'Zeile abwählen',
      showPassword: 'Passwort anzeigen',
      hidePassword: 'Passwort verbergen',
    },
  },
  en: {
    firstDayOfWeek: 1,
  },
}

/** Keeps PrimeVue's own texts (calendar, paginator, aria) in the app language. Call after app.use(PrimeVue). */
export function syncPrimeVueLocale(app: App) {
  const primeConfig = app.config.globalProperties.$primevue.config
  const primeDefaults: Partial<PrimeVueLocaleOptions> =
    structuredClone(toRaw(primeConfig.locale)) ?? {}
  watch(
    i18n.global.locale,
    (locale) => {
      const overrides = primeVueLocales[locale] ?? {}
      primeConfig.locale = {
        ...primeDefaults,
        ...overrides,
        aria: { ...primeDefaults.aria, ...(overrides.aria as object) },
      } as typeof primeConfig.locale
    },
    { immediate: true },
  )
}
