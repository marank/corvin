import { vi } from 'vitest'
import type { Page } from '../../api/client'

/** One request as the app sent it (path without the /api/v1 prefix). */
export interface ApiCall {
  method: string
  path: string
  query: URLSearchParams
  body: unknown
  headers: Record<string, string>
}

/** A response with a status other than 200. */
export class Reply {
  readonly status: number
  readonly body: unknown
  constructor(status: number, body: unknown = null) {
    this.status = status
    this.body = body
  }
}

export const reply = (status: number, body: unknown = null) => new Reply(status, body)

/** A fixed response body or Reply, an Error to fail the request, or a function of the call. */
type Handler = ((call: ApiCall) => unknown) | object | string | number | boolean | null

interface Route {
  method: string
  path: string | RegExp
  handler: Handler
}

export function page<T>(results: T[], count = results.length): Page<T> {
  return { count, next: null, previous: null, results }
}

/** A promise the test resolves by hand, to look at the page while a request is pending. */
export function deferred<T = unknown>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((r) => {
    resolve = r
  })
  return { promise, resolve }
}

const PREFIX = '/api/v1'

function parseBody(body: BodyInit | null | undefined): unknown {
  if (body == null) return undefined
  if (typeof body === 'string') return JSON.parse(body) as unknown
  return body
}

async function toResponse(result: unknown): Promise<Response> {
  const { status, body } = result instanceof Reply ? result : new Reply(200, result)
  if (status === 204) return new Response(null, { status })
  // jsdom's Blob is not the one fetch's Response knows: hand over its bytes.
  if (body instanceof Blob) return new Response(await body.arrayBuffer(), { status })
  if (typeof body === 'string')
    return new Response(body, { status, headers: { 'content-type': 'text/html' } })
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

/**
 * Replaces fetch with a fake backend: register responses per method and path (without the
 * /api/v1 prefix), then assert on `calls`. The newest matching route wins, so a test can
 * override the defaults of its suite. Unregistered requests get a 404 and land in `unhandled`.
 */
export function mockApi() {
  const routes: Route[] = []
  const calls: ApiCall[] = []
  const unhandled: string[] = []

  const fetchMock = vi.fn(async (input: string, init: RequestInit = {}) => {
    const url = new URL(input, 'http://localhost')
    const method = (init.method ?? 'GET').toUpperCase()
    const path = url.pathname.startsWith(PREFIX) ? url.pathname.slice(PREFIX.length) : url.pathname
    const call: ApiCall = {
      method,
      path,
      query: url.searchParams,
      body: parseBody(init.body),
      headers: { ...(init.headers as Record<string, string> | undefined) },
    }
    calls.push(call)
    const route = [...routes]
      .reverse()
      .find(
        (r) =>
          r.method === method && (typeof r.path === 'string' ? r.path === path : r.path.test(path)),
      )
    if (!route) {
      unhandled.push(`${method} ${path}`)
      return toResponse(reply(404, { detail: 'Not found.' }))
    }
    const result: unknown =
      typeof route.handler === 'function'
        ? await (route.handler as (call: ApiCall) => unknown)(call)
        : route.handler
    if (result instanceof Error) throw result
    return toResponse(result)
  })
  vi.stubGlobal('fetch', fetchMock)

  const mock = {
    calls,
    unhandled,
    on(method: string, path: string | RegExp, handler: Handler) {
      routes.push({ method, path, handler })
      return mock
    },
    get: (path: string | RegExp, handler: Handler) => mock.on('GET', path, handler),
    post: (path: string | RegExp, handler: Handler) => mock.on('POST', path, handler),
    put: (path: string | RegExp, handler: Handler) => mock.on('PUT', path, handler),
    patch: (path: string | RegExp, handler: Handler) => mock.on('PATCH', path, handler),
    delete: (path: string | RegExp, handler: Handler = reply(204)) =>
      mock.on('DELETE', path, handler),
    /** The requests to one method and path, oldest first. */
    requests(method: string, path: string | RegExp) {
      return calls.filter(
        (c) =>
          c.method === method && (typeof path === 'string' ? c.path === path : path.test(c.path)),
      )
    },
    /** The body of the last request to one method and path. */
    lastBody(method: string, path: string | RegExp): unknown {
      const matching = mock.requests(method, path)
      if (!matching.length) throw new Error(`no ${method} ${String(path)} was sent`)
      return matching[matching.length - 1]!.body
    },
  }
  return mock
}

export type ApiMock = ReturnType<typeof mockApi>
