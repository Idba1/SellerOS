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

export interface DashboardSummary {
  period: { start_date: string; end_date: string; store_timezone: string }
  sales: { totals: { delivered_order_count: number; delivered_net_sales_before_reversals: string } }
  products: { products: Array<{ product_id: string; delivered_units: number; delivered_gross_sales: string }> }
  profit: { net_revenue: string; estimated_operational_profit: string | null; completeness_status: string }
  inventory: { low_stock_count: number; configured_threshold_count: number }
}
