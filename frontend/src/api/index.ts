import { api, type Page } from './client'

export interface Address {
  id: string
  customer: string
  label: string
  street: string
  postal_code: string
  city: string
  country: string
  is_primary: boolean
  is_invoice_address: boolean
  is_delivery_address: boolean
}

export interface BankAccount {
  id: string
  name: string
  bank_name: string
  account_holder: string
  iban: string
  bic: string
  is_active: boolean
}

export interface Customer {
  id: string
  number: string
  // Set once a finalized invoice shows the number; it can no longer be changed.
  number_locked: boolean
  name: string
  email: string
  phone: string
  website: string
  vat_id: string
  notes: string
  buyer_reference: string
  rounding_increment_minutes: number | null
  payment_terms_days: number | null
  bank_account: string | null
  // Default for the customer's invoices.
  e_invoice_format: string
  is_active: boolean
  project_count: number
  uninvoiced_hours: number | null
  addresses: Address[]
  primary_address: Address | null
}

export interface Project {
  id: string
  number: string
  // Set once a finalized invoice shows the number; it can no longer be changed.
  number_locked: boolean
  customer: string
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
  id: string
  number: string
  customer: string | null
  customer_name: string | null
  project: string | null
  project_name: string | null
  visit: string | null
  title: string
  description: string
  due_date: string | null
  priority: string
  status: string
}

export interface Contact {
  id: string
  customer: string
  first_name: string
  last_name: string
  name: string
  role: string
  email: string
  phone: string
  is_invoice_contact: boolean
  // How mails greet them ("Erika", "Frau Muster"); empty: the full name.
  salutation_name: string
}

export interface Visit {
  id: string
  number: string
  customer: string
  customer_name: string
  project: string | null
  project_name: string | null
  date: string
  location: string
  arrival: string | null
  departure: string | null
  notes: string
}

export interface TimeEntryBreak {
  id: string
  start_datetime: string
  end_datetime: string | null
}

export interface TimeEntry {
  id: string
  customer: string | null
  customer_name: string | null
  project: string | null
  project_name: string | null
  visit: string | null
  contract: string | null
  contract_name: string | null
  start_datetime: string
  end_datetime: string | null
  normalized_start_datetime: string | null
  normalized_end_datetime: string | null
  breaks: TimeEntryBreak[]
  break_minutes: number
  duration_minutes: number
  hours: number
  is_running: boolean
  is_paused: boolean
  description: string
  report: string
  billable: boolean
  // Set by invoicing only (read-only).
  invoice: string | null
}

export interface HourlyRate {
  id: string
  customer: string | null
  customer_name: string | null
  project: string | null
  project_name: string | null
  amount: number
  valid_from: string
  valid_to: string | null
}

export interface SupportContract {
  id: string
  number: string
  // Set once a finalized invoice shows the number; it can no longer be changed.
  number_locked: boolean
  customer: string
  customer_name: string
  project: string | null
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
  template: string | null
}

export interface ContractUsage {
  period_start: string
  period_end: string
  used_hours: number
  included_hours: number
  overage_hours: number
}

export interface LineItem {
  id: string
  invoice: string
  position: number
  description: string
  quantity: number
  unit: string
  unit_price: number
  total: number
  // The time entries the line bills (read-only).
  time_entry_ids: string[]
}

export interface Payment {
  id: string
  invoice: string
  date: string
  amount: number
  note: string
}

export interface Invoice {
  id: string
  number: string
  customer: string
  customer_name: string
  project: string | null
  project_name: string | null
  contract: string | null
  contract_name: string | null
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
  // Bills time entries, so a time report (Leistungsnachweis) exists.
  has_time_entries: boolean
  // Written elsewhere and uploaded: its PDF is the original.
  is_external: boolean
  sent_at: string | null
  template: string | null
  bank_account_override: string | null
  bank_account: BankAccount | null
  contacts: Contact[]
  items: LineItem[]
  payments: Payment[]
}

export interface TextBlock {
  id: string
  name: string
  key: string
  content: string
}

export interface DocumentTemplate {
  id: string
  name: string
  created_at: string
  page_size: string
  margin_top: number
  margin_right: number
  margin_bottom: number
  margin_left: number
  header_height: number
  footer_height: number
  font_size: number
  primary_font: string
  secondary_font: string
  primary_color: string
  secondary_color: string
  tertiary_color: string
  background_color: string
  text_color: string
  body_html: string
  css: string
  header_html: string
  footer_html: string
}

export interface CompanyContact {
  id: string
  first_name: string
  last_name: string
  name: string
  role: string
  email: string
  phone: string
}

export interface CompanyImage {
  id: string
  kind: 'logo_light' | 'logo_dark' | 'icon_light' | 'icon_dark' | 'additional'
  key: string
  name: string
  image: string
  url: string
}

export interface Attachment {
  id: string
  file: string
  url: string
  name: string
  uploaded_at: string
  content_type: number
  object_id: string
}

const base = '/api/v1'

export interface User {
  id: number
  username: string
  email: string
  totp_enabled: boolean
}

export const authApi = {
  me: () => api.get<User>(`${base}/auth/me`),
  login: (username: string, password: string, otpCode: string) =>
    api.post<User>(`${base}/auth/login`, { username, password, otp_code: otpCode }),
  logout: () => api.post(`${base}/auth/logout`),
}

/** The timer's entry while it runs. */
export interface RunningEntry {
  id: string
  customer: string | null
  customer_name: string | null
  project: string | null
  project_name: string | null
  start_datetime: string
  breaks: { id: string; start_datetime: string; end_datetime: string | null }[]
  is_paused: boolean
  description: string
}

export const bankAccountsApi = {
  list: () => api.get<Page<BankAccount>>(`${base}/bank-accounts/?page_size=200`),
  create: (d: Partial<BankAccount>) => api.post<BankAccount>(`${base}/bank-accounts/`, d),
  update: (id: string, d: Partial<BankAccount>) =>
    api.put<BankAccount>(`${base}/bank-accounts/${id}/`, d),
  remove: (id: string) => api.delete(`${base}/bank-accounts/${id}/`),
}

export const customersApi = {
  list: (params = '') => api.get<Page<Customer>>(`${base}/customers/?${params}`),
  get: (id: string) => api.get<Customer>(`${base}/customers/${id}/`),
  create: (d: Partial<Customer>) => api.post<Customer>(`${base}/customers/`, d),
  update: (id: string, d: Partial<Customer>) => api.put<Customer>(`${base}/customers/${id}/`, d),
  remove: (id: string) => api.delete(`${base}/customers/${id}/`),
}

export const addressesApi = {
  list: (customerId: string) =>
    api.get<Page<Address>>(`${base}/addresses/?customer=${customerId}&page_size=500`),
  create: (d: Partial<Address>) => api.post<Address>(`${base}/addresses/`, d),
  update: (id: string, d: Partial<Address>) => api.put<Address>(`${base}/addresses/${id}/`, d),
  remove: (id: string) => api.delete(`${base}/addresses/${id}/`),
}

export const contactsApi = {
  list: (customerId: string) =>
    api.get<Page<Contact>>(`${base}/contacts/?customer=${customerId}&page_size=500`),
  create: (d: Partial<Contact>) => api.post<Contact>(`${base}/contacts/`, d),
  update: (id: string, d: Partial<Contact>) => api.put<Contact>(`${base}/contacts/${id}/`, d),
  remove: (id: string) => api.delete(`${base}/contacts/${id}/`),
}

export const projectsApi = {
  list: (params = '') => api.get<Page<Project>>(`${base}/projects/?${params}`),
  get: (id: string) => api.get<Project>(`${base}/projects/${id}/`),
  create: (d: Partial<Project>) => api.post<Project>(`${base}/projects/`, d),
  update: (id: string, d: Partial<Project>) => api.put<Project>(`${base}/projects/${id}/`, d),
  remove: (id: string) => api.delete(`${base}/projects/${id}/`),
}

export const tasksApi = {
  list: (params = '') => api.get<Page<Task>>(`${base}/tasks/?${params}`),
  create: (d: Partial<Task>) => api.post<Task>(`${base}/tasks/`, d),
  update: (id: string, d: Partial<Task>) => api.put<Task>(`${base}/tasks/${id}/`, d),
  patch: (id: string, d: Partial<Task>) => api.patch<Task>(`${base}/tasks/${id}/`, d),
  remove: (id: string) => api.delete(`${base}/tasks/${id}/`),
}

export const visitsApi = {
  list: (params = '') => api.get<Page<Visit>>(`${base}/visits/?${params}`),
  get: (id: string) => api.get<Visit>(`${base}/visits/${id}/`),
  create: (d: Partial<Visit>) => api.post<Visit>(`${base}/visits/`, d),
  update: (id: string, d: Partial<Visit>) => api.put<Visit>(`${base}/visits/${id}/`, d),
  remove: (id: string) => api.delete(`${base}/visits/${id}/`),
}

export const timeTrackingApi = {
  list: (params = '') => api.get<Page<TimeEntry>>(`${base}/time-tracking/?${params}`),
  summary: (params = '') =>
    api.get<{ count: number; total_minutes: number }>(`${base}/time-tracking/summary/?${params}`),
  create: (d: Record<string, unknown>) => api.post<TimeEntry>(`${base}/time-tracking/`, d),
  update: (id: string, d: Record<string, unknown>) =>
    api.put<TimeEntry>(`${base}/time-tracking/${id}/`, d),
  remove: (id: string) => api.delete(`${base}/time-tracking/${id}/`),
  active: () => api.get<RunningEntry | null>(`${base}/time-tracking/active/`),
  start: (d: { customer: string | null; project: string | null; description: string }) =>
    api.post<RunningEntry>(`${base}/time-tracking/start/`, d),
  stop: () => api.post<TimeEntry>(`${base}/time-tracking/stop/`),
  pause: () => api.post<RunningEntry>(`${base}/time-tracking/pause/`),
  resume: () => api.post<RunningEntry>(`${base}/time-tracking/resume/`),
}

export const ratesApi = {
  list: (params = '') => api.get<Page<HourlyRate>>(`${base}/hourly-rates/?${params}`),
  create: (d: Partial<HourlyRate>) => api.post<HourlyRate>(`${base}/hourly-rates/`, d),
  update: (id: string, d: Partial<HourlyRate>) =>
    api.put<HourlyRate>(`${base}/hourly-rates/${id}/`, d),
  remove: (id: string) => api.delete(`${base}/hourly-rates/${id}/`),
}

export const contractsApi = {
  list: (params = '') => api.get<Page<SupportContract>>(`${base}/support-contracts/?${params}`),
  get: (id: string) => api.get<SupportContract>(`${base}/support-contracts/${id}/`),
  create: (d: Partial<SupportContract>) =>
    api.post<SupportContract>(`${base}/support-contracts/`, d),
  update: (id: string, d: Partial<SupportContract>) =>
    api.put<SupportContract>(`${base}/support-contracts/${id}/`, d),
  remove: (id: string) => api.delete(`${base}/support-contracts/${id}/`),
  usage: (id: string) => api.get<ContractUsage>(`${base}/support-contracts/${id}/usage/`),
  runNow: (id: string) => api.post<Invoice>(`${base}/support-contracts/${id}/run_now/`),
}

export interface ConsolidateRequest {
  customer_id: string
  project_id?: string | null
  bank_account_id?: string | null
  contact_ids?: string[]
  date_from?: string | null
  date_to?: string | null
  entry_ids?: string[]
  group_by: string
  // Lines put together from entries (the entries and their text); replaces the grouping.
  entry_lines?: { entry_ids: string[]; description: string }[]
  e_invoice_format?: string
  extra_lines?: Partial<LineItem>[]
  // Omitted: today, issue date + payment terms, the company's rate, the assigned template.
  issue_date?: string
  due_date?: string
  vat_rate?: number
  template_id?: string | null
  notes?: string
  // Editing a draft only: its number, corrected by hand.
  number?: string
}

export interface ConsolidatePreviewLine extends Pick<
  LineItem,
  'description' | 'quantity' | 'unit' | 'unit_price' | 'total'
> {
  // Lines built from entries: their entries (grouped: key, generated text); own: null, [].
  key: string | null
  entry_ids: string[]
  default_description?: string
  // Lines from entries: their project (one) and period.
  project_name?: string | null
  date_from?: string
  date_to?: string
}

export interface ConsolidatePreview {
  lines: ConsolidatePreviewLine[]
  entry_count: number
  subtotal: string
  vat_rate: string
  vat_amount: string
  total: string
}

// A draft as the create page holds it: its entries, grouping, edited texts and own lines.
export interface InvoiceDraftState {
  group_by: string
  entries: TimeEntry[]
  texts: Record<string, string>
  own_lines: Pick<LineItem, 'description' | 'quantity' | 'unit' | 'unit_price'>[]
}

export const invoicesApi = {
  list: (params = '') => api.get<Page<Invoice>>(`${base}/invoices/?${params}`),
  get: (id: string) => api.get<Invoice>(`${base}/invoices/${id}/`),
  update: (id: string, d: Partial<Invoice>) => api.put<Invoice>(`${base}/invoices/${id}/`, d),
  patch: (id: string, d: Partial<Invoice>) => api.patch<Invoice>(`${base}/invoices/${id}/`, d),
  remove: (id: string) => api.delete(`${base}/invoices/${id}/`),
  consolidate: (d: ConsolidateRequest) => api.post<Invoice>(`${base}/invoices/consolidate/`, d),
  consolidatePreview: (d: ConsolidateRequest) =>
    api.post<ConsolidatePreview>(`${base}/invoices/consolidate_preview/`, d),
  // Editing a draft on the create page; its own entries count as open in the preview.
  draft: (id: string) => api.get<InvoiceDraftState>(`${base}/invoices/${id}/draft/`),
  saveDraft: (id: string, d: ConsolidateRequest) =>
    api.put<Invoice>(`${base}/invoices/${id}/draft/`, d),
  draftPreview: (id: string, d: ConsolidateRequest) =>
    api.post<ConsolidatePreview>(`${base}/invoices/${id}/draft_preview/`, d),
  finalize: (id: string) => api.post<Invoice>(`${base}/invoices/${id}/finalize/`),
  // `sent_on`: the day it went out (omitted: now).
  markSent: (id: string, d: { sent_on?: string } = {}) =>
    api.post<Invoice>(`${base}/invoices/${id}/mark_sent/`, d),
  cancel: (id: string) => api.post<Invoice>(`${base}/invoices/${id}/cancel/`),
  // The mail of a kind as it would go out (from the e-mail template assigned to the kind).
  // `to`: the addresses to greet (omitted: the default ones, returned as `to`).
  emailDraft: (id: string, kind: MailKind = 'invoice', to?: string[]) => {
    const params = new URLSearchParams({ kind })
    for (const address of to ?? []) params.append('to', address)
    return api.get<{ to: string[]; subject: string; html: string }>(
      `${base}/invoices/${id}/email_draft/?${params.toString()}`,
    )
  },
  sendEmail: (id: string, d: { to: string[]; subject?: string; kind?: MailKind }) =>
    api.post<Invoice>(`${base}/invoices/${id}/send_email/`, d),
  pdfUrl: (id: string) => `${base}/invoices/${id}/pdf/`,
  xmlUrl: (id: string) => `${base}/invoices/${id}/xrechnung/`,
  timeEntries: (id: string) => api.get<TimeEntry[]>(`${base}/invoices/${id}/time-entries/`),
  // An invoice written elsewhere (multipart: fields, pdf, xml, entry_ids), recorded as issued.
  importExternal: (form: FormData) =>
    api.upload<Invoice>(`${base}/invoices/import_external/`, form),
  // The mails about the invoice (newest first); one with its HTML as sent.
  mails: (id: string) => api.get<InvoiceMail[]>(`${base}/invoices/${id}/mails/`),
  mail: (id: string, mailId: string) =>
    api.get<InvoiceMail & { html: string }>(`${base}/invoices/${id}/mails/${mailId}/`),
  timeReportUrl: (id: string) => `${base}/invoices/${id}/time-report/`,
  previewUrl: (id: string) => `${base}/invoices/${id}/preview/`,
}

export const invoiceItemsApi = {
  create: (d: Partial<LineItem>) => api.post<LineItem>(`${base}/invoice-items/`, d),
  update: (id: string, d: Partial<LineItem>) =>
    api.patch<LineItem>(`${base}/invoice-items/${id}/`, d),
  remove: (id: string) => api.delete(`${base}/invoice-items/${id}/`),
}

export const paymentsApi = {
  create: (d: Partial<Payment>) => api.post<Payment>(`${base}/payments/`, d),
  remove: (id: string) => api.delete(`${base}/payments/${id}/`),
}

export const textBlocksApi = {
  list: (params = 'page_size=200') => api.get<Page<TextBlock>>(`${base}/text-blocks/?${params}`),
  create: (d: Partial<TextBlock>) => api.post<TextBlock>(`${base}/text-blocks/`, d),
  update: (id: string, d: Partial<TextBlock>) =>
    api.put<TextBlock>(`${base}/text-blocks/${id}/`, d),
  remove: (id: string) => api.delete(`${base}/text-blocks/${id}/`),
}

// A mail about an invoice as it was sent (or is waiting to be).
export interface InvoiceMail {
  id: string
  kind: MailKind
  to: string[]
  subject: string
  attachments: string[]
  status: 'queued' | 'sent'
  sent_at: string | null
  // The last failed attempt; empty once sent.
  error: string
  created_at: string
}

export type MailKind = 'invoice' | 'payment_reminder'
export const mailKinds: MailKind[] = ['invoice', 'payment_reminder']

// An e-mail as HTML. Without a base the whole mail, its {% block %} tags are blocks others
// fill; with a base only blocks, overriding the base's ({{ block.super }} keeps its content).
export interface MailTemplate {
  id: string
  name: string
  subject: string
  base: string | null
  html: string
  // Read-only: the blocks it offers, templates building on it, kinds it is assigned to.
  slot_names: string[]
  derived_count: number
  assigned_kinds: MailKind[]
  created_at: string
  updated_at: string
}

export const mailTemplatesApi = {
  list: (params = '') => api.get<Page<MailTemplate>>(`${base}/mail-templates/?${params}`),
  get: (id: string) => api.get<MailTemplate>(`${base}/mail-templates/${id}/`),
  create: (d: Partial<MailTemplate>) => api.post<MailTemplate>(`${base}/mail-templates/`, d),
  update: (id: string, d: Partial<MailTemplate>) =>
    api.put<MailTemplate>(`${base}/mail-templates/${id}/`, d),
  remove: (id: string) => api.delete(`${base}/mail-templates/${id}/`),
  duplicate: (id: string) => api.post<MailTemplate>(`${base}/mail-templates/${id}/duplicate/`),
  // Sample data; with `d`, unsaved changes (nothing is stored).
  preview: (id: string, d?: Partial<MailTemplate>) =>
    api.post<{ subject: string; html: string }>(`${base}/mail-templates/${id}/preview/`, d ?? {}),
}

export const templatesApi = {
  list: (params = '') => api.get<Page<DocumentTemplate>>(`${base}/document-templates/?${params}`),
  get: (id: string) => api.get<DocumentTemplate>(`${base}/document-templates/${id}/`),
  create: (d: Partial<DocumentTemplate>) =>
    api.post<DocumentTemplate>(`${base}/document-templates/`, d),
  update: (id: string, d: Partial<DocumentTemplate>) =>
    api.put<DocumentTemplate>(`${base}/document-templates/${id}/`, d),
  remove: (id: string) => api.delete(`${base}/document-templates/${id}/`),
  duplicate: (id: string) =>
    api.post<DocumentTemplate>(`${base}/document-templates/${id}/duplicate/`),
  previewUrl: (id: string) => `${base}/document-templates/${id}/preview/`,
  previewPdfUrl: (id: string) => `${base}/document-templates/${id}/preview-pdf/`,
  // Previews of unsaved designer changes (nothing is stored).
  previewDraft: (id: string, d: Partial<DocumentTemplate>) =>
    api.post<string>(`${base}/document-templates/${id}/preview/`, d),
  previewDraftPdf: (id: string, d: Partial<DocumentTemplate>) =>
    api.postBlob(`${base}/document-templates/${id}/preview-pdf/`, d),
  exportUrl: (id: string) => `${base}/document-templates/${id}/export/`,
  importTemplate: (data: unknown) =>
    api.post<DocumentTemplate>(`${base}/document-templates/import/`, data),
}

export const attachmentsApi = {
  contentTypes: () => api.get<Record<string, number>>(`${base}/attachments/content_types/`),
  list: (contentType: number, objectId: string) =>
    api.get<Page<Attachment>>(
      `${base}/attachments/?content_type=${contentType}&object_id=${objectId}&page_size=500`,
    ),
  upload: (contentType: number, objectId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    form.append('content_type', String(contentType))
    form.append('object_id', String(objectId))
    return api.upload<Attachment>(`${base}/attachments/`, form)
  },
  remove: (id: string) => api.delete(`${base}/attachments/${id}/`),
}

export const companyContactsApi = {
  list: () => api.get<Page<CompanyContact>>(`${base}/company-contacts/?page_size=200`),
  create: (d: Partial<CompanyContact>) => api.post<CompanyContact>(`${base}/company-contacts/`, d),
  update: (id: string, d: Partial<CompanyContact>) =>
    api.put<CompanyContact>(`${base}/company-contacts/${id}/`, d),
  remove: (id: string) => api.delete(`${base}/company-contacts/${id}/`),
}

export const companyImagesApi = {
  list: () => api.get<Page<CompanyImage>>(`${base}/company-images/?page_size=200`),
  upload: (d: { kind: string; key: string; name: string; file: File }, id?: string) => {
    const form = new FormData()
    form.append('kind', d.kind)
    form.append('key', d.key)
    form.append('name', d.name)
    form.append('image', d.file)
    return id
      ? api.uploadPut<CompanyImage>(`${base}/company-images/${id}/`, form)
      : api.upload<CompanyImage>(`${base}/company-images/`, form)
  },
  remove: (id: string) => api.delete(`${base}/company-images/${id}/`),
}

export const settingsApi = {
  get: () => api.get<Record<string, unknown>>(`${base}/settings/`),
  update: (d: Record<string, unknown>) => api.put<Record<string, unknown>>(`${base}/settings/`, d),
  updateWithLogo: (form: FormData) =>
    api.upload<Record<string, unknown>>(`${base}/settings/`, form),
  previewNumber: (d: { entity: string; format: string; scope: string[]; start: number }) =>
    api.post<{ preview: string }>(`${base}/settings/preview-number/`, d),
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
  totpDisable: (password: string) => api.post(`${base}/security/totp/disable`, { password }),
  sessions: () =>
    api.get<{ key: string; expire_date: string; current: boolean }[]>(`${base}/security/sessions`),
  revokeSession: (key: string) => api.delete(`${base}/security/sessions`, { key }),
  revokeAllSessions: () => api.delete(`${base}/security/sessions`, { all: true }),
}
