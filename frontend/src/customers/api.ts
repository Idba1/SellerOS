import type { PaginatedResponse } from '../api/types'

export type Customer = {
  id: string
  display_name: string
  phone: string | null
  email: string | null
  created_at: string
  updated_at: string
}

export type CustomerHistory = {
  purchase_count: number
  last_purchase_at: string | null
  total_spend: string
}

export type CustomerPayload = Pick<Customer, 'display_name' | 'phone' | 'email'>

function isCustomer(value: unknown): value is Customer {
  return value !== null && typeof value === 'object'
    && 'id' in value && typeof value.id === 'string'
    && 'display_name' in value && typeof value.display_name === 'string'
    && 'phone' in value && (typeof value.phone === 'string' || value.phone === null)
    && 'email' in value && (typeof value.email === 'string' || value.email === null)
    && 'created_at' in value && typeof value.created_at === 'string'
    && 'updated_at' in value && typeof value.updated_at === 'string'
}

export function decodeCustomer(value: unknown): Customer { if (!isCustomer(value)) throw new Error('Invalid customer response.'); return value }
export function decodeCustomerPage(value: unknown): PaginatedResponse<Customer> {
  if (value === null || typeof value !== 'object' || !('count' in value) || typeof value.count !== 'number'
    || !('next' in value) || (typeof value.next !== 'string' && value.next !== null)
    || !('previous' in value) || (typeof value.previous !== 'string' && value.previous !== null)
    || !('results' in value) || !Array.isArray(value.results) || !value.results.every(isCustomer)) throw new Error('Invalid customer list response.')
  return value as PaginatedResponse<Customer>
}
export function decodeCustomerHistory(value: unknown): CustomerHistory {
  if (value === null || typeof value !== 'object' || !('purchase_count' in value) || typeof value.purchase_count !== 'number'
    || !('last_purchase_at' in value) || (typeof value.last_purchase_at !== 'string' && value.last_purchase_at !== null)
    || !('total_spend' in value) || typeof value.total_spend !== 'string') throw new Error('Invalid customer purchase history response.')
  return value as CustomerHistory
}
