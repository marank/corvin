import { reactive } from 'vue'

// Field errors from the last failed API call, shown inline by AppFormField
// (`field` prop). Only one form is edited at a time, so one shared map is enough.
export const formErrors = reactive<Record<string, string>>({})
const mountedFields = reactive(new Map<string, number>())

export function registerField(field: string) {
  mountedFields.set(field, (mountedFields.get(field) ?? 0) + 1)
}

export function unregisterField(field: string) {
  const n = (mountedFields.get(field) ?? 1) - 1
  if (n > 0) mountedFields.set(field, n)
  else mountedFields.delete(field)
}

export function isFieldShown(field: string) {
  return mountedFields.has(field)
}

export function clearFormErrors() {
  for (const key of Object.keys(formErrors)) delete formErrors[key]
}

export function errorText(value: unknown): string {
  if (Array.isArray(value)) return value.map(errorText).filter(Boolean).join(', ')
  if (value && typeof value === 'object')
    return Object.values(value).map(errorText).filter(Boolean).join(', ')
  if (typeof value === 'string') return value
  // The rest of a JSON error body: numbers and booleans; null gives no text.
  return typeof value === 'number' || typeof value === 'boolean' ? String(value) : ''
}

export function setFormErrors(data: Record<string, unknown>) {
  clearFormErrors()
  for (const [key, value] of Object.entries(data)) formErrors[key] = errorText(value)
}
