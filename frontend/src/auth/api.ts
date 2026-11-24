import { getApiClient } from '../api/config'
import type { ErrorDetails } from '../api/types'
import type { AuthSession } from './session'

type AuthPayload = {
  account: { id: string; email: string }
  token: string
}

function decodeAuthPayload(value: unknown): AuthPayload {
  if (!value || typeof value !== 'object' || !('account' in value) || !('token' in value)) {
    throw new Error('Invalid authentication response.')
  }
  const account = value.account
  if (!account || typeof account !== 'object' || !('id' in account) || !('email' in account)
    || typeof account.id !== 'string' || typeof account.email !== 'string'
    || typeof value.token !== 'string' || value.token.length === 0) {
    throw new Error('Invalid authentication response.')
  }
  return { account: { id: account.id, email: account.email }, token: value.token }
}

async function authenticate(path: 'auth/login/' | 'auth/register/', email: string, password: string): Promise<AuthSession> {
  const response = await getApiClient().request(path, {
    method: 'POST',
    body: { email, password },
    decode: decodeAuthPayload,
  })
  if (!response) throw new Error('Authentication response was empty.')
  return response
}

export function login(email: string, password: string): Promise<AuthSession> {
  return authenticate('auth/login/', email, password)
}

export function register(email: string, password: string): Promise<AuthSession> {
  return authenticate('auth/register/', email, password)
}

function firstMessage(details: ErrorDetails): string | null {
  if (typeof details === 'string') return details
  if (Array.isArray(details)) return details.map(firstMessage).find((message): message is string => Boolean(message)) ?? null
  return Object.values(details).map(firstMessage).find((message): message is string => Boolean(message)) ?? null
}

export function messageFromAuthError(error: unknown): string {
  if (error && typeof error === 'object' && 'isAuthError' in error && error.isAuthError) {
    return 'Email or password is incorrect.'
  }
  if (error && typeof error === 'object' && 'details' in error) {
    const message = firstMessage(error.details as ErrorDetails)
    if (message) return message
  }
  if (error && typeof error === 'object' && 'kind' in error && error.kind === 'network') {
    return 'SellerOS could not reach the service. Check your connection and try again.'
  }
  return 'Sign-in is unavailable right now. Please try again later.'
}
