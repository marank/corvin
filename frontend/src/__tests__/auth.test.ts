import { flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'
import LoginView from '../views/LoginView.vue'
import SettingsSecurityView from '../views/settings/SettingsSecurityView.vue'
import { useAuthStore } from '../stores/auth'
import { mockApi, reply } from './helpers/api'
import {
  answerConfirm,
  click,
  confirmText,
  dialog,
  isDialogOpen,
  screen,
  toasts,
  type,
} from './helpers/dom'
import { render, t } from './helpers/render'

// No canvas in jsdom; the QR code's picture is not what these tests are about.
vi.mock('qrcode', () => ({
  default: { toDataURL: () => Promise.resolve('data:image/png;base64,QR') },
}))

const user = { id: 1, username: 'matthias', email: 'm@corvin.example', totp_enabled: false }

describe('LoginView', () => {
  const field = (id: string) => document.getElementById(id) as HTMLInputElement
  async function logIn(otp?: string) {
    await type(field('login-username'), 'matthias')
    await type(field('login-password'), 'secret')
    if (otp !== undefined) await type(field('login-otp'), otp)
    screen.root.querySelector('form')!.dispatchEvent(new Event('submit', { cancelable: true }))
    await flushPromises()
  }
  const open = (url = '/login') => render(LoginView, { path: '/login', url })

  it('logs in and continues to the page that asked for it', async () => {
    const api = mockApi()
    api.post('/auth/login', user)
    const { router, pinia } = await open('/login?next=/invoices/inv-1')
    await logIn()
    expect(api.lastBody('POST', '/auth/login')).toEqual({
      username: 'matthias',
      password: 'secret',
      otp_code: '',
    })
    expect(useAuthStore(pinia).user?.username).toBe('matthias')
    expect(router.currentRoute.value.fullPath).toBe('/invoices/inv-1')
  })

  it('goes to the dashboard without a next page', async () => {
    const api = mockApi()
    api.post('/auth/login', user)
    const { router } = await open()
    await logIn()
    expect(router.currentRoute.value.fullPath).toBe('/')
  })

  it('says so when the password is wrong', async () => {
    const api = mockApi()
    api.post('/auth/login', reply(400, { detail: 'Invalid credentials.' }))
    const { router } = await open()
    await logIn()
    expect(screen.text()).toContain(t('auth.loginFailed'))
    expect(router.currentRoute.value.path).toBe('/login')
    expect(document.getElementById('login-otp')).toBeNull()
  })

  it('asks for the second factor, then logs in with it', async () => {
    const api = mockApi()
    api.post('/auth/login', (call) =>
      (call.body as { otp_code: string }).otp_code === '123456'
        ? user
        : reply(400, { requires_otp: true }),
    )
    const { router } = await open()
    await logIn()
    // The first answer is no error, just the next step.
    expect(screen.text()).not.toContain(t('auth.loginFailed'))
    expect(screen.text()).toContain(t('auth.otpHint'))

    await logIn('000000')
    expect(screen.text()).toContain(t('auth.otpFailed'))

    await logIn('123456')
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('shows a network failure as a failed login', async () => {
    const api = mockApi()
    api.post('/auth/login', new TypeError('Failed to fetch'))
    await open()
    await logIn()
    expect(screen.text()).toContain(t('auth.loginFailed'))
  })
})

describe('router', () => {
  async function freshRouter() {
    vi.resetModules()
    setActivePinia(createPinia())
    const { default: router } = await import('../router')
    return router
  }

  it('sends anonymous visitors to the login, remembering where they wanted to go', async () => {
    const api = mockApi()
    api.get('/auth/me', reply(403, { detail: 'Not authenticated.' }))
    const router = await freshRouter()
    await router.push('/invoices/inv-1?tab=payments')
    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.next).toBe('/invoices/inv-1?tab=payments')
    // Checked once, not on every navigation.
    await router.push('/customers')
    expect(api.requests('GET', '/auth/me')).toHaveLength(1)
  })

  it('lets logged-in users in, and away from the login page', async () => {
    const api = mockApi()
    api.get('/auth/me', user)
    const router = await freshRouter()
    await router.push('/customers')
    expect(router.currentRoute.value.name).toBe('customers')
    await router.push('/login')
    expect(router.currentRoute.value.name).toBe('dashboard')
    await router.push('/no/such/page')
    expect(router.currentRoute.value.name).toBe('dashboard')
  })

  it('opens each page at its URL', async () => {
    mockApi().get('/auth/me', user)
    const router = await freshRouter()
    const pages: Record<string, string> = {
      '/': 'DashboardView',
      '/customers': 'CustomerListView',
      '/customers/c1': 'CustomerDetailView',
      '/projects': 'ProjectListView',
      '/projects/p1': 'ProjectDetailView',
      '/tasks': 'TasksView',
      '/time': 'TimeTrackingView',
      '/visits': 'VisitListView',
      '/visits/v1': 'VisitDetailView',
      '/contracts': 'ContractListView',
      '/contracts/k1': 'ContractDetailView',
      '/invoices': 'InvoiceListView',
      '/invoices/new': 'InvoiceCreateView',
      '/invoices/i1': 'InvoiceDetailView',
      '/templates': 'TemplateListView',
      '/templates/t1': 'InvoiceDesignerView',
      '/settings': 'SettingsProfileView',
      '/settings/security': 'SettingsSecurityView',
    }
    for (const [url, view] of Object.entries(pages)) {
      await router.push(url)
      const matched = router.currentRoute.value.matched
      const component = matched[matched.length - 1]!.components!.default as { __name?: string }
      expect(component.__name, url).toBe(view)
    }
  })

  it("drops the left page's form errors", async () => {
    mockApi().get('/auth/me', user)
    const router = await freshRouter()
    // The router's own instance of the module, after resetModules.
    const { formErrors, setFormErrors } = await import('../composables/formErrors')
    await router.push('/customers')
    setFormErrors({ name: 'Required.' })
    await router.push('/projects')
    expect({ ...formErrors }).toEqual({})
  })

  it('logs out', async () => {
    const api = mockApi()
    api.post('/auth/logout', reply(204))
    setActivePinia(createPinia())
    const auth = useAuthStore()
    auth.user = user
    await auth.logout()
    expect(auth.user).toBeNull()
    expect(api.requests('POST', '/auth/logout')).toHaveLength(1)
  })
})

describe('SettingsSecurityView', () => {
  const sessions = [
    { key: 'abc123', expire_date: '2026-12-07T10:00:00+01:00', current: true },
    { key: 'def456', expire_date: '2026-12-01T08:00:00+01:00', current: false },
  ]

  async function open(totp = false) {
    const api = mockApi()
    api.get('/security/sessions', sessions)
    const view = await render(SettingsSecurityView, { path: '/settings/security' })
    useAuthStore(view.pinia).user = { ...user, totp_enabled: totp }
    await flushPromises()
    return { api, ...view }
  }
  const passwordInput = (label: string) => screen.field(label).querySelector('input')!

  it('lists the sessions and marks this one', async () => {
    await open()
    expect(screen.text()).toContain(`abc123${t('settings.currentSession')}`)
    expect(screen.text()).toContain('07.12.2026 10:00')
  })

  it('changes the password', async () => {
    const { api } = await open()
    api.post('/auth/password/change', reply(204))
    expect(screen.button(t('common.save')).hasAttribute('disabled')).toBe(true)
    await type(passwordInput(t('settings.oldPassword')), 'old')
    await type(passwordInput(t('settings.newPassword')), 'n3w-Passw0rd')
    await click(screen.button(t('common.save')))
    expect(api.lastBody('POST', '/auth/password/change')).toEqual({
      old_password: 'old',
      new_password: 'n3w-Passw0rd',
    })
    expect(toasts()).toContain(t('settings.passwordChanged'))
    expect(passwordInput(t('settings.oldPassword')).value).toBe('')
  })

  it('shows why the new password was refused', async () => {
    const { api } = await open()
    api.post('/auth/password/change', reply(400, ['This password is too common.']))
    await type(passwordInput(t('settings.oldPassword')), 'old')
    await type(passwordInput(t('settings.newPassword')), 'password')
    await click(screen.button(t('common.save')))
    expect(toasts()).toEqual([`${t('common.error')}This password is too common.`])
  })

  it('sets up two-factor authentication and shows the backup codes once', async () => {
    const { api, pinia } = await open()
    api.post('/security/totp/setup', { config_url: 'otpauth://totp/corvin' })
    api.post('/security/totp/confirm', { backup_codes: ['1111-2222', '3333-4444'] })
    await click(screen.button(t('settings.totpSetup')))
    const modal = dialog(t('settings.totp'))
    expect(modal.root.querySelector('img')!.getAttribute('src')).toBe('data:image/png;base64,QR')
    expect(modal.button(t('common.confirm')).hasAttribute('disabled')).toBe(true)
    await type(modal.input(t('settings.totpConfirm')), '123456')
    await click(modal.button(t('common.confirm')))
    expect(api.lastBody('POST', '/security/totp/confirm')).toEqual({ code: '123456' })
    expect(dialog(t('settings.totp')).text()).toContain('1111-2222')
    expect(useAuthStore(pinia).user?.totp_enabled).toBe(true)
    await click(dialog(t('settings.totp')).button(t('common.done')))
    expect(screen.text()).toContain(t('settings.totpEnabled'))
  })

  it('keeps the code step open when the code is wrong', async () => {
    const { api } = await open()
    api.post('/security/totp/setup', { config_url: 'otpauth://totp/corvin' })
    api.post('/security/totp/confirm', reply(400, { code: ['Invalid code.'] }))
    await click(screen.button(t('settings.totpSetup')))
    await type(dialog(t('settings.totp')).input(t('settings.totpConfirm')), '000000')
    await click(dialog(t('settings.totp')).button(t('common.confirm')))
    expect(toasts().join()).toContain('Invalid code.')
    expect(dialog(t('settings.totp')).text()).toContain(t('settings.totpScan'))
  })

  it('turns two-factor authentication off with the password and forgets it', async () => {
    const { api, pinia } = await open(true)
    api.post('/security/totp/disable', reply(204))
    await click(screen.button(t('settings.totpDisable')))
    let modal = dialog(t('settings.totpDisableTitle'))
    await type(modal.field(t('auth.password')).querySelector('input')!, 'secret')
    await click(modal.button(t('settings.totpDisable')))
    expect(api.lastBody('POST', '/security/totp/disable')).toEqual({ password: 'secret' })
    expect(isDialogOpen(t('settings.totpDisableTitle'))).toBe(false)
    expect(useAuthStore(pinia).user?.totp_enabled).toBe(false)
    expect(toasts()).toContain(t('settings.totpDisabled'))

    useAuthStore(pinia).user!.totp_enabled = true
    await flushPromises()
    await click(screen.button(t('settings.totpDisable')))
    modal = dialog(t('settings.totpDisableTitle'))
    expect(modal.field(t('auth.password')).querySelector('input')!.value).toBe('')
  })

  it('signs out the other sessions after confirmation', async () => {
    const { api } = await open()
    api.delete('/security/sessions', reply(204))
    await click(screen.button(t('settings.revokeOthers')))
    expect(confirmText()).toContain(t('settings.revokeOthersConfirm'))
    api.get('/security/sessions', [sessions[0]])
    await answerConfirm(t('settings.revokeOthers'))
    expect(api.lastBody('DELETE', '/security/sessions')).toEqual({ all: true })
    expect(screen.text()).not.toContain('def456')
    expect(toasts()).toContain(t('settings.revokedOthers'))
  })
})
