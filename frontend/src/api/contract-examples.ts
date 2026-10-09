import type { ApiError, PaginatedResponse } from './types'

// Synthetic contract fixtures, not implemented product fields or UI data.
export const pageExample = {
  count: 1, next: null, previous: null, results: [{ id: 'example' }],
} satisfies PaginatedResponse<{ id: string }>

export const validationExample = {
  error: { code: 'validation_error', details: { quantity: ['Use a positive quantity.'] } },
} satisfies ApiError

export const permissionExample = {
  error: { code: 'permission_denied', details: { detail: 'Permission denied.' } },
} satisfies ApiError

export const notFoundExample = {
  error: { code: 'not_found', details: { detail: 'Not found.' } },
} satisfies ApiError
