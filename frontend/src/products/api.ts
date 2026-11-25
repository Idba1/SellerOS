import type { PaginatedResponse } from '../api/types'

export type Product = {
  id: string
  name: string
  category: string | null
  selling_price: string
  unit_cost: string | null
  has_variants: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export type ProductDetail = Product & {
  variants: Array<{
    id: string
    product_id: string
    name: string
    is_active: boolean
    created_at: string
    updated_at: string
  }>
}

export type ProductVariant = ProductDetail['variants'][number]

export type ProductPayload = Pick<Product, 'name' | 'category' | 'selling_price' | 'unit_cost' | 'has_variants' | 'is_active'>

function isProduct(value: unknown): value is Product {
  return value !== null && typeof value === 'object'
    && 'id' in value && typeof value.id === 'string'
    && 'name' in value && typeof value.name === 'string'
    && 'category' in value && (typeof value.category === 'string' || value.category === null)
    && 'selling_price' in value && typeof value.selling_price === 'string'
    && 'unit_cost' in value && (typeof value.unit_cost === 'string' || value.unit_cost === null)
    && 'has_variants' in value && typeof value.has_variants === 'boolean'
    && 'is_active' in value && typeof value.is_active === 'boolean'
    && 'created_at' in value && typeof value.created_at === 'string'
    && 'updated_at' in value && typeof value.updated_at === 'string'
}

export function decodeProduct(value: unknown): Product {
  if (!isProduct(value)) throw new Error('Invalid product response.')
  return value
}

export function decodeProductDetail(value: unknown): ProductDetail {
  if (!isProduct(value) || !('variants' in value) || !Array.isArray(value.variants)
    || !value.variants.every(variant => variant !== null && typeof variant === 'object'
      && 'id' in variant && typeof variant.id === 'string'
      && 'product_id' in variant && typeof variant.product_id === 'string'
      && 'name' in variant && typeof variant.name === 'string'
      && 'is_active' in variant && typeof variant.is_active === 'boolean'
      && 'created_at' in variant && typeof variant.created_at === 'string'
      && 'updated_at' in variant && typeof variant.updated_at === 'string')) {
    throw new Error('Invalid product detail response.')
  }
  return value as ProductDetail
}

export function decodeProductVariant(value: unknown): ProductVariant {
  if (value === null || typeof value !== 'object'
    || !('id' in value) || typeof value.id !== 'string'
    || !('product_id' in value) || typeof value.product_id !== 'string'
    || !('name' in value) || typeof value.name !== 'string'
    || !('is_active' in value) || typeof value.is_active !== 'boolean'
    || !('created_at' in value) || typeof value.created_at !== 'string'
    || !('updated_at' in value) || typeof value.updated_at !== 'string') throw new Error('Invalid product variant response.')
  return value as ProductVariant
}

export function decodeProductPage(value: unknown): PaginatedResponse<Product> {
  if (value === null || typeof value !== 'object' || !('count' in value) || typeof value.count !== 'number'
    || !('next' in value) || (typeof value.next !== 'string' && value.next !== null)
    || !('previous' in value) || (typeof value.previous !== 'string' && value.previous !== null)
    || !('results' in value) || !Array.isArray(value.results) || !value.results.every(isProduct)) {
    throw new Error('Invalid products list response.')
  }
  return value as PaginatedResponse<Product>
}
