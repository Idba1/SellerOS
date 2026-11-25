import type { PaginatedResponse } from '../api/types'

export type StockUnit = {
  id: string
  product_id: string
  product_name: string
  variant_id: string | null
  variant_name: string | null
  quantity_on_hand: number
  low_stock_threshold: number | null
  is_low_stock: boolean
  updated_at: string
}

export type InventoryMovement = {
  id: string
  stock_unit_id: string
  movement_type: string
  quantity_delta: number
  reason: string | null
  created_by_id: string
  reversal_of_id: string | null
  occurred_at: string
}

function isStockUnit(value: unknown): value is StockUnit {
  return value !== null && typeof value === 'object'
    && 'id' in value && typeof value.id === 'string'
    && 'product_id' in value && typeof value.product_id === 'string'
    && 'product_name' in value && typeof value.product_name === 'string'
    && 'variant_id' in value && (typeof value.variant_id === 'string' || value.variant_id === null)
    && 'variant_name' in value && (typeof value.variant_name === 'string' || value.variant_name === null)
    && 'quantity_on_hand' in value && typeof value.quantity_on_hand === 'number'
    && 'low_stock_threshold' in value && (typeof value.low_stock_threshold === 'number' || value.low_stock_threshold === null)
    && 'is_low_stock' in value && typeof value.is_low_stock === 'boolean'
    && 'updated_at' in value && typeof value.updated_at === 'string'
}

export function decodeStockUnit(value: unknown): StockUnit {
  if (!isStockUnit(value)) throw new Error('Invalid inventory stock-unit response.')
  return value
}

function isMovement(value: unknown): value is InventoryMovement {
  return value !== null && typeof value === 'object'
    && 'id' in value && typeof value.id === 'string'
    && 'stock_unit_id' in value && typeof value.stock_unit_id === 'string'
    && 'movement_type' in value && typeof value.movement_type === 'string'
    && 'quantity_delta' in value && typeof value.quantity_delta === 'number'
    && 'reason' in value && (typeof value.reason === 'string' || value.reason === null)
    && 'created_by_id' in value && typeof value.created_by_id === 'string'
    && 'reversal_of_id' in value && (typeof value.reversal_of_id === 'string' || value.reversal_of_id === null)
    && 'occurred_at' in value && typeof value.occurred_at === 'string'
}

function decodePage<T>(value: unknown, isItem: (item: unknown) => item is T, label: string): PaginatedResponse<T> {
  if (value === null || typeof value !== 'object' || !('count' in value) || typeof value.count !== 'number'
    || !('next' in value) || (typeof value.next !== 'string' && value.next !== null)
    || !('previous' in value) || (typeof value.previous !== 'string' && value.previous !== null)
    || !('results' in value) || !Array.isArray(value.results) || !value.results.every(isItem)) {
    throw new Error(`Invalid ${label} response.`)
  }
  return value as PaginatedResponse<T>
}

export function decodeStockUnitPage(value: unknown) { return decodePage(value, isStockUnit, 'inventory list') }
export function decodeMovementPage(value: unknown) { return decodePage(value, isMovement, 'inventory movement list') }
export function decodeMovement(value: unknown): InventoryMovement { if (!isMovement(value)) throw new Error('Invalid inventory adjustment response.'); return value }
