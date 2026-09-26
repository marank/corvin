import { api, type Page } from './client'

export interface Customer {
  id: number
  name: string
  street: string
  postal_code: string
  city: string
  country: string
  email: string
  phone: string
  notes: string
  buyer_reference: string
  rounding_increment_minutes: number | null
  is_active: boolean
  project_count: number
  uninvoiced_hours: number | null
}

export interface Project {
  id: number
  customer: number
  customer_name: string
  name: string
  description: string
  status: string
  budget_hours: number | null
  budget_amount: number | null
  rounding_increment_minutes: number | null
  used_hours: number
  used_amount: number
  budget_hours_percent: number | null
  budget_amount_percent: number | null
}

export interface Task {
  id: number
  project: number | null
  project_name: string | null
  visit: number | null
  title: string
  description: string
  due_date: string | null
  priority: string
  status: string
}

export interface Contact {
  id: number
  customer: number
  name: string
  role: string
  email: string
  phone: string
}

export interface Visit {
  id: number
  customer: number
  customer_name: string
  project: number | null
  project_name: string | null
  date: string
  location: string
  arrival: string | null
  departure: string | null
  notes: string
}

export interface TimeEntry {
  id: number
  project: number
  project_name: string
  customer_name: string
  visit: number | null
  contract: number | null
  contract_name: string | null
  date: string
  start_time: string
  end_time: string | null
  break_minutes: number
  duration_minutes: number
  hours: number
  is_running: boolean
  description: string
  billable: boolean
  invoice: number | null
}

export interface HourlyRate {
  id: number
  customer: number | null
  customer_name: string | null
  project: number | null
  project_name: string | null
  amount: number
  valid_from: string
  valid_to: string | null
}

export interface SupportContract {
  id: number
  customer: number
  customer_name: string
  project: number | null
  project_name: string | null
  name: string
  included_hours: number
  period: string
  fixed_price: number
  bill_overage: boolean
  overage_rate: number | null
  start_date: string
  end_date: string | null
  next_billing_date: string
  active: boolean
  template: number | null
}

export interface ContractUsage {
  period_start: string
  period_end: string
  used_hours: number
  included_hours: number
  overage_hours: number
}

export interface LineItem {
  id: number
  invoice: number
  position: number
  description: string
  quantity: number
  unit: string
  unit_price: number
  total: number
}

export interface Payment {
  id: number
  invoice: number
  date: string
  amount: number
  note: string
}

export interface Invoice {
  id: number
  number: string
  customer: number
  customer_name: string
  project: number | null
  project_name: string | null
  contract: number | null
  issue_date: string
  due_date: string | null
  status: string
  vat_rate: number
  currency: string
  e_invoice_format: string
  notes: string
  subtotal: number
  vat_amount: number
  total: number
  amount_paid: number
  remaining: number
  partially_paid: boolean
  sent_at: string | null
  template: number | null
  items: LineItem[]
  payments: Payment[]
}

export interface InvoiceTemplate {
  id: number
  name: string
  page_size: string
  margin_top: number
  margin_right: number
  margin_bottom: number
  margin_left: number
  body_html: string
  css: string
  header_html: string
  footer_html: string
  mail_subject: string
  mail_body: string
  is_default: boolean
}

export interface Attachment {
  id: number
  file: string
  url: string
  name: string
  uploaded_at: string
  content_type: number
  object_id: number
}

const base = '/api/v1'

export const customersApi = {
  list: (params = '') => api.get<Page<Customer>>(`${base}/customers/?${params}`),
  get: (id: number) => api.get<Customer>(`${base}/customers/${id}/`),
  create: (d: Partial<Customer>) => api.post<Customer>(`${base}/customers/`, d),
  update: (id: number, d: Partial<Customer>) =>
    api.put<Customer>(`${base}/customers/${id}/`, d),
  remove: (id: number) => api.delete(`${base}/customers/${id}/`),
}

export const contactsApi = {
  list: (customerId: number) =>
    api.get<Page<Contact>>(`${base}/contacts/?customer=${customerId}`),
  create: (d: Partial<Contact>) => api.post<Contact>(`${base}/contacts/`, d),
  update: (id: number, d: Partial<Contact>) =>
    api.put<Contact>(`${base}/contacts/${id}/`, d),
  remove: (id: number) => api.delete(`${base}/contacts/${id}/`),
}

export const projectsApi = {
  list: (params = '') => api.get<Page<Project>>(`${base}/projects/?${params}`),
  get: (id: number) => api.get<Project>(`${base}/projects/${id}/`),
  create: (d: Partial<Project>) => api.post<Project>(`${base}/projects/`, d),
  update: (id: number, d: Partial<Project>) =>
    api.put<Project>(`${base}/projects/${id}/`, d),
  remove: (id: number) => api.delete(`${base}/projects/${id}/`),
}

export const tasksApi = {
  list: (params = '') => api.get<Page<Task>>(`${base}/tasks/?${params}`),
  create: (d: Partial<Task>) => api.post<Task>(`${base}/tasks/`, d),
  update: (id: number, d: Partial<Task>) => api.put<Task>(`${base}/tasks/${id}/`, d),
  remove: (id: number) => api.delete(`${base}/tasks/${id}/`),
}

export const visitsApi = {
  list: (params = '') => api.get<Page<Visit>>(`${base}/visits/?${params}`),
  get: (id: number) => api.get<Visit>(`${base}/visits/${id}/`),
  create: (d: Partial<Visit>) => api.post<Visit>(`${base}/visits/`, d),
  update: (id: number, d: Partial<Visit>) =>
    api.put<Visit>(`${base}/visits/${id}/`, d),
  remove: (id: number) => api.delete(`${base}/visits/${id}/`),
}

export const timeEntriesApi = {
  list: (params = '') => api.get<Page<TimeEntry>>(`${base}/time-entries/?${params}`),
  create: (d: Record<string, unknown>) => api.post<TimeEntry>(`${base}/time-entries/`, d),
  update: (id: number, d: Record<string, unknown>) =>
    api.put<TimeEntry>(`${base}/time-entries/${id}/`, d),
  remove: (id: number) => api.delete(`${base}/time-entries/${id}/`),
}

export const ratesApi = {
  list: (params = '') => api.get<Page<HourlyRate>>(`${base}/hourly-rates/?${params}`),
  create: (d: Partial<HourlyRate>) => api.post<HourlyRate>(`${base}/hourly-rates/`, d),
  update: (id: number, d: Partial<HourlyRate>) =>
    api.put<HourlyRate>(`${base}/hourly-rates/${id}/`, d),
  remove: (id: number) => api.delete(`${base}/hourly-rates/${id}/`),
}

export const contractsApi = {
  list: (params = '') =>
    api.get<Page<SupportContract>>(`${base}/support-contracts/?${params}`),
  get: (id: number) => api.get<SupportContract>(`${base}/support-contracts/${id}/`),
  create: (d: Partial<SupportContract>) =>
    api.post<SupportContract>(`${base}/support-contracts/`, d),
  update: (id: number, d: Partial<SupportContract>) =>
    api.put<SupportContract>(`${base}/support-contracts/${id}/`, d),
  remove: (id: number) => api.delete(`${base}/support-contracts/${id}/`),
  usage: (id: number) =>
    api.get<ContractUsage>(`${base}/support-contracts/${id}/usage/`),
  runNow: (id: number) =>
    api.post<Invoice>(`${base}/support-contracts/${id}/run_now/`),
}

export const invoicesApi = {
  list: (params = '') => api.get<Page<Invoice>>(`${base}/invoices/?${params}`),
  get: (id: number) => api.get<Invoice>(`${base}/invoices/${id}/`),
  update: (id: number, d: Partial<Invoice>) =>
    api.put<Invoice>(`${base}/invoices/${id}/`, d),
  remove: (id: number) => api.delete(`${base}/invoices/${id}/`),
  consolidate: (d: {
    customer_id: number
    project_id?: number | null
    date_from?: string | null
    date_to?: string | null
    group_by: string
    e_invoice_format?: string
  }) => api.post<Invoice>(`${base}/invoices/consolidate/`, d),
  finalize: (id: number) => api.post<Invoice>(`${base}/invoices/${id}/finalize/`),
  markSent: (id: number) => api.post<Invoice>(`${base}/invoices/${id}/mark_sent/`),
  cancel: (id: number) => api.post<Invoice>(`${base}/invoices/${id}/cancel/`),
  sendEmail: (id: number, d: { to: string; subject?: string; body?: string }) =>
    api.post<Invoice>(`${base}/invoices/${id}/send_email/`, d),
  pdfUrl: (id: number) => `${base}/invoices/${id}/pdf/`,
  xmlUrl: (id: number) => `${base}/invoices/${id}/xrechnung/`,
  previewUrl: (id: number) => `${base}/invoices/${id}/preview/`,
}

export const paymentsApi = {
  create: (d: Partial<Payment>) => api.post<Payment>(`${base}/payments/`, d),
  remove: (id: number) => api.delete(`${base}/payments/${id}/`),
}

export const templatesApi = {
  list: () => api.get<Page<InvoiceTemplate>>(`${base}/invoice-templates/`),
  get: (id: number) => api.get<InvoiceTemplate>(`${base}/invoice-templates/${id}/`),
  create: (d: Partial<InvoiceTemplate>) =>
    api.post<InvoiceTemplate>(`${base}/invoice-templates/`, d),
  update: (id: number, d: Partial<InvoiceTemplate>) =>
    api.put<InvoiceTemplate>(`${base}/invoice-templates/${id}/`, d),
  remove: (id: number) => api.delete(`${base}/invoice-templates/${id}/`),
  previewUrl: (id: number) => `${base}/invoice-templates/${id}/preview/`,
}

export const attachmentsApi = {
  contentTypes: () =>
    api.get<Record<string, number>>(`${base}/attachments/content_types/`),
  list: (contentType: number, objectId: number) =>
    api.get<Page<Attachment>>(
      `${base}/attachments/?content_type=${contentType}&object_id=${objectId}`,
    ),
  upload: (contentType: number, objectId: number, file: File) => {
    const form = new FormData()
    form.append('file', file)
    form.append('content_type', String(contentType))
    form.append('object_id', String(objectId))
    return api.upload<Attachment>(`${base}/attachments/`, form)
  },
  remove: (id: number) => api.delete(`${base}/attachments/${id}/`),
}

export const settingsApi = {
  get: () => api.get<Record<string, unknown>>(`${base}/settings/`),
  update: (d: Record<string, unknown>) =>
    api.put<Record<string, unknown>>(`${base}/settings/`, d),
  updateWithLogo: (form: FormData) => api.upload<Record<string, unknown>>(`${base}/settings/`, form),
}

export const statsApi = {
  dashboard: () => api.get<Record<string, unknown>>(`${base}/stats/dashboard`),
}

export const securityApi = {
  changePassword: (old_password: string, new_password: string) =>
    api.post(`${base}/auth/password/change`, { old_password, new_password }),
  totpSetup: () => api.post<{ config_url: string }>(`${base}/security/totp/setup`),
  totpConfirm: (code: string) =>
    api.post<{ backup_codes: string[] }>(`${base}/security/totp/confirm`, { code }),
  totpDisable: (password: string) =>
    api.post(`${base}/security/totp/disable`, { password }),
  sessions: () =>
    api.get<{ key: string; expire_date: string; current: boolean }[]>(
      `${base}/security/sessions`,
    ),
  revokeSession: (key: string) =>
    api.delete(`${base}/security/sessions`, { key }),
  revokeAllSessions: () =>
    api.delete(`${base}/security/sessions`, { all: true }),
}
