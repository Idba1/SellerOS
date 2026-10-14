import { createApiClient } from './client'

/** Lazy configuration: the placeholder shell does not require a running API. */
export function getApiClient() {
  const configured = import.meta.env.VITE_API_BASE_URL as string | undefined
  if (!configured?.trim()) throw new Error('VITE_API_BASE_URL is required before making API requests.')
  return createApiClient({ baseUrl: configured })
}
