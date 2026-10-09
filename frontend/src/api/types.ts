/** BACKEND-05 semantic types; runtime response validation is a later client task. */
export const API_PREFIX = '/api/v1/' as const

export type ErrorDetails = string | ErrorDetails[] | { [field: string]: ErrorDetails }

export interface ApiError {
  error: {
    code: string
    details: ErrorDetails
  }
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface PaginationQuery {
  page?: number
  page_size?: number
}
