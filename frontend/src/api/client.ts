import { API_PREFIX, type ErrorDetails } from './types'

export type FailureKind = 'http' | 'network' | 'aborted' | 'protocol'
export class ApiClientError extends Error {
  constructor(public readonly kind: FailureKind, public readonly status: number | null, public readonly code: string, public readonly details: ErrorDetails) {
    super(kind === 'network' ? 'Unable to reach the service.' : kind === 'aborted' ? 'Request cancelled.' : 'The request could not be completed.')
    this.name = 'ApiClientError'
  }
  get isAuthError() {
    return this.status === 401 || ((this.status === 403) && ['not_authenticated', 'authentication_failed'].includes(this.code))
  }
}
function isDetails(value: unknown): value is ErrorDetails {
  return typeof value === 'string' || (Array.isArray(value) ? value.every(isDetails) : value !== null && typeof value === 'object' && Object.values(value).every(isDetails))
}
export interface RequestOptions<T> {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  query?: Record<string, string | number | boolean | undefined>
  body?: unknown
  signal?: AbortSignal
  decode: (value: unknown) => T
}
export interface ClientOptions {
  baseUrl: string
  fetch?: typeof fetch
  // AUTH tasks must explicitly choose credentials/headers; default sends no credentials.
  credentials?: RequestCredentials
  authHeaders?: () => Record<string, string>
}
export function createApiClient(options: ClientOptions) {
  const base = new URL(options.baseUrl)
  if (!['http:', 'https:'].includes(base.protocol) || base.username || base.password || base.search || base.hash || base.pathname !== API_PREFIX) {
    throw new Error('API base URL must be an HTTP(S) URL ending in /api/v1/, without credentials, query or fragment.')
  }
  const transport = options.fetch ?? globalThis.fetch
  function resolve(path: string) {
    const url = new URL(path, base)
    if (url.origin !== base.origin || !url.pathname.startsWith(API_PREFIX) || url.username || url.password || url.hash || !url.pathname.endsWith('/') || /%2f|%5c/i.test(url.pathname)) {
      throw new Error('Request URL must stay within the configured API origin and /api/v1/ prefix, with a trailing slash.')
    }
    return url
  }
  return {
    async request<T>(path: string, request: RequestOptions<T>): Promise<T | undefined> {
      const url = resolve(path)
      for (const [key, value] of Object.entries(request.query ?? {})) {
        if (value !== undefined) url.searchParams.set(key, String(value))
      }
      const method = request.method ?? 'GET'
      if (method === 'GET' && request.body !== undefined) throw new Error('GET requests cannot have a body.')
      const headers = new Headers(options.authHeaders?.())
      headers.set('Accept', 'application/json')
      if (request.body !== undefined) headers.set('Content-Type', 'application/json')
      const body = request.body === undefined ? undefined : JSON.stringify(request.body)
      let response: Response
      try {
        response = await transport(url, { method, headers, body, signal: request.signal, credentials: options.credentials ?? 'omit', redirect: 'error' })
      } catch {
        throw new ApiClientError(request.signal?.aborted ? 'aborted' : 'network', null, request.signal?.aborted ? 'request_aborted' : 'network_error', {})
      }
      if (response.status === 204) return undefined
      let payload: unknown
      try {
        if (!response.headers.get('Content-Type')?.toLowerCase().includes('application/json')) throw new Error()
        payload = await response.json()
      } catch {
        if (request.signal?.aborted) throw new ApiClientError('aborted', response.status, 'request_aborted', {})
        throw new ApiClientError('protocol', response.status, 'invalid_response', {})
      }
      if (!response.ok) {
        if (payload && typeof payload === 'object' && 'error' in payload) {
          const error = payload.error
          if (error && typeof error === 'object' && 'code' in error && typeof error.code === 'string' && 'details' in error && isDetails(error.details)) {
            throw new ApiClientError('http', response.status, error.code, error.details)
          }
        }
        throw new ApiClientError('protocol', response.status, 'invalid_response', {})
      }
      try { return request.decode(payload) } catch { throw new ApiClientError('protocol', response.status, 'invalid_response', {}) }
    },
  }
}

export type RequestState<T> =
  | { status: 'idle' | 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: unknown }

/** Own one instance per screen operation; stale completions cannot replace newer state. */
export function createRequestState<T>() {
  let state: RequestState<T> = { status: 'idle' }
  let version = 0
  const listeners = new Set<() => void>()
  const publish = (next: RequestState<T>) => { state = next; listeners.forEach(listener => listener()) }
  return {
    getSnapshot: () => state,
    subscribe: (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } },
    async run(operation: () => Promise<T>) {
      const current = ++version
      publish({ status: 'loading' })
      try {
        const data = await operation()
        if (current === version) publish({ status: 'success', data })
        return data
      } catch (error) {
        if (current === version) publish({ status: 'error', error })
        throw error
      }
    },
  }
}
