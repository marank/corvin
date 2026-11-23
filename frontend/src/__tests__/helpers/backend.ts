import type { Invoice, Project, Task, TimeEntry } from '../../api'
import { page, type ApiMock } from './api'
import { customer, project } from './fixtures'

/** The pickers (CustomerSelect, ProjectSelect) and the formatting settings most pages load. */
export function pickers(api: ApiMock) {
  api.get('/customers/', page([customer(), customer({ id: 'cus-2', name: 'Beta AG' })]))
  api.get('/projects/', page([project()]))
  api.get('/settings/', {})
  return api
}

/** What RelatedOverview loads for a customer or project. */
export function overview(
  api: ApiMock,
  data: {
    uninvoiced?: number
    total?: number
    entries?: TimeEntry[]
    invoices?: Invoice[]
    tasks?: Task[]
    projects?: Project[]
  } = {},
) {
  api.get('/time-tracking/summary/', (call) => ({
    count: 0,
    total_minutes: call.query.has('invoice__isnull') ? (data.uninvoiced ?? 0) : (data.total ?? 0),
  }))
  api.get('/time-tracking/', page(data.entries ?? []))
  api.get('/invoices/', page(data.invoices ?? []))
  api.get('/tasks/', page(data.tasks ?? []))
  api.get('/projects/', page(data.projects ?? []))
  return api
}

/** AttachmentList without attachments. */
export function noAttachments(api: ApiMock) {
  api.get('/attachments/content_types/', {
    customer: 1,
    project: 2,
    invoice: 3,
    visit: 4,
    contract: 5,
  })
  api.get('/attachments/', page([]))
  return api
}
