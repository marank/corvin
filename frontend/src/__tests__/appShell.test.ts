import { afterEach, describe, expect, it } from 'vitest'
import AppShell from '../layouts/AppShell.vue'
import { i18n, setLocale } from '../i18n'
import { useAuthStore } from '../stores/auth'
import { useFormattingStore } from '../stores/formatting'
import { mockApi, reply } from './helpers/api'
import { choose, click, screen } from './helpers/dom'
import { render, t } from './helpers/render'

function backend() {
  const api = mockApi()
  api.get('/settings/', { date_format: 'YYYY-MM-DD', currency_position: 'before' })
  api.get('/time-tracking/active/', null)
  api.post('/auth/logout', reply(204))
  return api
}

async function open(url = '/') {
  const view = await render(AppShell, { path: '/:rest(.*)*', url })
  useAuthStore(view.pinia).user = { id: 1, username: 'matthias', email: '', totp_enabled: false }
  return view
}

describe('AppShell', () => {
  afterEach(() => {
    setLocale('de')
    document.documentElement.classList.remove('dark')
  })

  it('loads the formatting settings for the whole app', async () => {
    backend()
    const { pinia } = await open()
    expect(useFormattingStore(pinia).dateFormat).toBe('YYYY-MM-DD')
    expect(useFormattingStore(pinia).currencyPosition).toBe('before')
  })

  it('links every section in the sidebar', async () => {
    backend()
    await open()
    for (const [label, href] of [
      [t('nav.dashboard'), '/'],
      [t('nav.timetracking'), '/time'],
      [t('nav.invoices'), '/invoices'],
      [t('nav.settings'), '/settings'],
    ])
      expect(screen.button(label!).getAttribute('href')).toBe(href)
  })

  it('opens the full-screen menu on small screens and navigates from it', async () => {
    backend()
    const { router } = await open()
    await click(screen.button(t('common.menu')))
    const tiles = screen.buttons(t('nav.invoices')).filter((el) => el.tagName === 'BUTTON')
    await click(tiles[0]!)
    expect(router.currentRoute.value.path).toBe('/invoices')
    expect(screen.hasButton(t('common.close'))).toBe(false)
  })

  it('closes the menu again', async () => {
    backend()
    await open()
    await click(screen.button(t('common.menu')))
    await click(screen.button(t('common.close')))
    expect(screen.hasButton(t('common.close'))).toBe(false)
  })

  it('switches to dark mode and remembers it', async () => {
    backend()
    await open()
    await click(screen.button(t('common.toggleTheme')))
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('dark')).toBe('1')
    await click(screen.button(t('common.toggleTheme')))
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(localStorage.getItem('dark')).toBe('0')
  })

  it('switches the language and remembers it', async () => {
    backend()
    await open()
    await choose(screen.select(t('common.language')), 'English')
    expect(i18n.global.locale.value).toBe('en')
    expect(localStorage.getItem('locale')).toBe('en')
    expect(document.documentElement.lang).toBe('en')
    expect(screen.hasButton('Invoices')).toBe(true)
  })

  it('logs out from the account menu', async () => {
    const api = backend()
    const { router, pinia } = await open('/customers')
    await click(screen.button(t('auth.account')))
    await click(screen.button(t('auth.logout')))
    expect(api.requests('POST', '/auth/logout')).toHaveLength(1)
    expect(useAuthStore(pinia).user).toBeNull()
    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('opens the security settings from the account menu', async () => {
    backend()
    const { router } = await open()
    await click(screen.button(t('auth.account')))
    await click(screen.button(t('settings.security')))
    expect(router.currentRoute.value.path).toBe('/settings/security')
  })
})
