import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createApiClient, ApiClientError, createRequestState } from '../src/api/client'
const baseUrl = 'http://localhost:8000/api/v1/'
const decode = (v: unknown) => { if (!v || typeof v !== 'object' || !('id' in v) || typeof v.id !== 'string') throw Error(); return v.id }
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } })
const clientFor = (response: Response) => createApiClient({ baseUrl, fetch: async () => response })
test('success, encoded query, JSON request, explicit auth headers and safe defaults', async () => {
  const client = createApiClient({ baseUrl, fetch: async (url, options) => {
    assert.equal(String(url), `${baseUrl}fixture/?search=a%26b`)
    assert.equal(options?.credentials, 'omit')
    assert.equal(options?.redirect, 'error')
    assert.equal(new Headers(options?.headers).get('Accept'), 'application/json')
    assert.equal(options?.body, JSON.stringify({ example: true }))
    return json({ id: 'synthetic' })
  } })
  assert.equal(await client.request('fixture/', { method: 'POST', body: { example: true }, query: { search: 'a&b' }, decode }), 'synthetic')
})
test('validation preserves nested errors; auth differs from permission errors', async () => {
  for (const [status, code, auth] of [[400, 'validation_error', false], [401, 'not_authenticated', true], [403, 'authentication_failed', true], [403, 'permission_denied', false]] as const) {
    const details = { nested: { quantity: ['Required.'] } }
    await assert.rejects(clientFor(json({ error: { code, details } }, status)).request('fixture/', { decode }), e => {
      assert.ok(e instanceof ApiClientError); assert.equal(e.status, status); assert.equal(e.code, code); assert.equal(e.isAuthError, auth); assert.deepEqual(e.details, details); return true
    })
  }
})
test('auth adapter is explicit and evaluated for each request', async () => {
  let token = 'synthetic-one'
  const client = createApiClient({ baseUrl, credentials: 'include', authHeaders: () => ({ Authorization: token }), fetch: async (_url, options) => {
    assert.equal(options?.credentials, 'include')
    assert.equal(new Headers(options?.headers).get('Authorization'), token)
    return json({ id: 'synthetic' })
  } })
  await client.request('fixture/', { decode })
  token = 'synthetic-two'
  await client.request('fixture/', { decode })
})
test('network and cancellation errors do not expose original exception', async () => {
  const controller = new AbortController()
  const client = createApiClient({ baseUrl, fetch: async () => { throw Error('private diagnostic') } })
  await assert.rejects(client.request('fixture/', { decode }), e => e instanceof ApiClientError && e.kind === 'network' && !e.message.includes('private'))
  controller.abort()
  await assert.rejects(client.request('fixture/', { decode, signal: controller.signal }), e => e instanceof ApiClientError && e.kind === 'aborted')
})
test('unsafe destinations rejected before sending credentials', async () => {
  let calls = 0
  const client = createApiClient({ baseUrl, fetch: async () => { calls++; return json({ id: 'x' }) } })
  for (const path of ['https://other.example/api/v1/fixture/', '../health/', '/api/v10/fixture/', 'fixture/#secret', 'fixture/%2F/']) await assert.rejects(client.request(path, { decode }))
  assert.equal(calls, 0)
  assert.throws(() => createApiClient({ baseUrl: 'http://user:password@localhost/api/v1/' }))
})
test('204 and malformed/HTML/incorrect success payloads', async () => {
  assert.equal(await clientFor(new Response(null, { status: 204 })).request('fixture/', { decode }), undefined)
  for (const response of [new Response('<html>private trace</html>', { status: 500 }), json({ error: { code: 3, details: null } }, 400), json({ id: 7 })]) {
    await assert.rejects(clientFor(response).request('fixture/', { decode }), e => e instanceof ApiClientError && e.kind === 'protocol' && JSON.stringify(e.details) === '{}')
  }
})
test('request state transitions and stale completions', async () => {
  const state = createRequestState<string>()
  assert.equal(state.getSnapshot().status, 'idle')
  let finish!: (value: string) => void
  const old = state.run(() => new Promise<string>(resolve => { finish = resolve }))
  assert.equal(state.getSnapshot().status, 'loading')
  await state.run(async () => 'new')
  finish('old'); await old
  assert.deepEqual(state.getSnapshot(), { status: 'success', data: 'new' })
  await assert.rejects(state.run(async () => { throw Error('failure') }))
  assert.equal(state.getSnapshot().status, 'error')
})
