import { ApiClientError } from '../api/client'
import { getApiClient } from '../api/config'
import type { ErrorDetails } from '../api/types'

export type StoreProfile = {
  id: string
  name: string
  timezone: string
  currency_code: 'BDT'
}

function decodeStoreProfile(value: unknown): StoreProfile {
  if (!value || typeof value !== 'object'
    || !('id' in value) || typeof value.id !== 'string'
    || !('name' in value) || typeof value.name !== 'string'
    || !('timezone' in value) || typeof value.timezone !== 'string'
    || !('currency_code' in value) || value.currency_code !== 'BDT') {
    throw new Error('Invalid store profile response.')
  }
  return { id: value.id, name: value.name, timezone: value.timezone, currency_code: value.currency_code }
}

export function getCurrentStore(): Promise<StoreProfile | undefined> {
  return getApiClient().request('stores/current/', { decode: decodeStoreProfile })
}

export function createStore(input: { name: string; timezone: string }): Promise<StoreProfile | undefined> {
  return getApiClient().request('stores/current/', { method: 'POST', body: input, decode: decodeStoreProfile })
}

export function isMissingStore(error: unknown): boolean {
  return error instanceof ApiClientError && error.status === 404 && error.code === 'not_found'
}

function firstMessage(details: ErrorDetails): string | null {
  if (typeof details === 'string') return details
  if (Array.isArray(details)) return details.map(firstMessage).find((message): message is string => Boolean(message)) ?? null
  return Object.values(details).map(firstMessage).find((message): message is string => Boolean(message)) ?? null
}

export function messageFromStoreError(error: unknown): string {
  if (error instanceof ApiClientError) {
    const message = firstMessage(error.details)
    if (message) return message
    if (error.kind === 'network') return 'SellerOS could not reach the service. Check your connection and try again.'
  }
  if (error instanceof Error && error.message.includes('VITE_API_BASE_URL')) {
    return 'Store setup is unavailable until the frontend API URL is configured.'
  }
  return 'SellerOS could not load the store profile. Please try again.'
}
