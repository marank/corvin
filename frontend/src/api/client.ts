function getCsrfToken(): string {
  const match = document.cookie.match(/csrftoken=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : ''
}

export class ApiError extends Error {
  status: number
  data: unknown
  constructor(status: number, data: unknown) {
    super(`HTTP ${status}`)
    this.status = status
    this.data = data
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(path, {
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken(),
      ...(options.headers ?? {}),
    },
    ...options,
  })
  if (res.status === 204) return undefined as T
  const contentType = res.headers.get('content-type') ?? ''
  const data = contentType.includes('json') ? await res.json() : await res.text()
  if (!res.ok) throw new ApiError(res.status, data)
  return data as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body ?? {}) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: 'DELETE',
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  upload: <T>(path: string, form: FormData) =>
    request<T>(path, {
      method: 'POST',
      body: form,
      headers: { 'X-CSRFToken': getCsrfToken() },
    }),
}

export interface Page<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
