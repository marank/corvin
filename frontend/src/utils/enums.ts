import type { components } from '../api/schema'

type Schemas = components['schemas']

/**
 * Every value of a generated API enum, in the order given. The values are written as the keys of
 * a record, so the type check fails when the backend adds a value that is missing here (or drops
 * one still listed): allValues<Schemas['PriorityEnum']>()({ low: true, medium: true, high: true }).
 */
export const allValues =
  <T extends string>() =>
  (values: Record<T, true>): T[] =>
    Object.keys(values) as T[]

export const currencyDisplayValues = allValues<Schemas['CurrencyDisplayEnum']>()({
  symbol: true,
  code: true,
})
export const currencyPositionValues = allValues<Schemas['CurrencyPositionEnum']>()({
  before: true,
  after: true,
})
export const eInvoiceFormatValues = allValues<Schemas['EInvoiceFormatEnum']>()({
  none: true,
  zugferd: true,
  xrechnung: true,
})
export const numberedEntityValues = allValues<Schemas['EntityEnum']>()({
  customer: true,
  project: true,
  invoice: true,
  contract: true,
  visit: true,
  task: true,
})
export const invoiceStatusValues = allValues<Schemas['InvoiceStatusEnum']>()({
  draft: true,
  issued: true,
  sent: true,
  paid: true,
  cancelled: true,
})
export const companyImageKindValues = allValues<Schemas['KindEnum']>()({
  logo_light: true,
  logo_dark: true,
  icon_light: true,
  icon_dark: true,
  additional: true,
})
export const openStoppedTimeEntryValues = allValues<Schemas['OpenStoppedTimeEntryEnum']>()({
  ask: true,
  yes: true,
  no: true,
})
export const pageSizeValues = allValues<Schemas['PageSizeEnum']>()({
  A3: true,
  A4: true,
  A5: true,
  LETTER: true,
  LEGAL: true,
  TABLOID: true,
})
export const contractPeriodValues = allValues<Schemas['PeriodEnum']>()({
  monthly: true,
  quarterly: true,
  yearly: true,
})
export const priorityValues = allValues<Schemas['PriorityEnum']>()({
  low: true,
  medium: true,
  high: true,
})
export const projectStatusValues = allValues<Schemas['ProjectStatusEnum']>()({
  active: true,
  on_hold: true,
  done: true,
})
export const numberScopeValues = allValues<Schemas['ScopeEnum']>()({
  year: true,
  customer: true,
  project: true,
})
export const taskStatusValues = allValues<Schemas['TaskStatusEnum']>()({
  open: true,
  in_progress: true,
  done: true,
})
export const timeRoundingDirectionValues = allValues<Schemas['TimeRoundingDirectionEnum']>()({
  nearest: true,
  backwards: true,
  forwards: true,
})
export const lineItemUnitValues = allValues<Schemas['UnitEnum']>()({
  hours: true,
  flat: true,
  piece: true,
})
