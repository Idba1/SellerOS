import { useState, type FormEvent, type ReactNode } from 'react'
import { ApiClientError } from '../api/client'
import { getApiClient } from '../api/config'
import type { DashboardSummary } from '../api/types'
import { getAuthSession } from '../auth/session'
import { Badge, Card } from '../ui/primitives'

const money = new Intl.NumberFormat('en-BD', { style: 'currency', currency: 'BDT', minimumFractionDigits: 2, maximumFractionDigits: 2 })

function decodeDashboard(value: unknown): DashboardSummary {
  if (!value || typeof value !== 'object' || !('period' in value) || !('sales' in value) || !('profit' in value) || !('products' in value) || !('inventory' in value)) throw new Error('Invalid dashboard response.')
  return value as DashboardSummary
}

function errorMessage(error: unknown) {
  if (error instanceof ApiClientError && error.kind === 'network') return 'SellerOS could not reach the service. Check your connection and try again.'
  if (error instanceof Error && error.message.includes('VITE_API_BASE_URL')) return 'Dashboard data is unavailable until the frontend API URL is configured.'
  if (error instanceof ApiClientError && error.status === 404) return 'Finish store setup before loading dashboard data.'
  return 'SellerOS could not load this dashboard period. Please try again.'
}

export function Dashboard() {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [data, setData] = useState<DashboardSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const hasSession = Boolean(getAuthSession())
  const invalid = Boolean(startDate && endDate && startDate > endDate)

  async function fetchDashboard() {
    if (!startDate || !endDate || invalid || !hasSession) return
    setLoading(true); setError(null); setData(null)
    try {
      setData(await getApiClient().request('analytics/dashboard/', { query: { start_date: startDate, end_date: endDate }, decode: decodeDashboard }) ?? null)
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  function load(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void fetchDashboard()
  }

  function retry() { void fetchDashboard() }

  return <>
    <div className="dashboard-hero"><div><p className="eyebrow">SELLER OVERVIEW</p><h1>Dashboard</h1><p className="page-description">Review verified sales, profit and stock signals for a selected store period.</p></div><Badge tone="accent">Live store data</Badge></div>
    {!hasSession ? <DashboardState title="Sign in to view your dashboard" description="Dashboard figures are available only to an authenticated SellerOS account." action={<a className="button" href="/login">Go to sign in</a>} /> : <>
      <form className="card dashboard-controls dashboard-period-form" onSubmit={load} noValidate><div><p className="eyebrow">REPORTING PERIOD</p><h2>Choose a reporting period</h2><p>Dates are interpreted using the current store’s time zone.</p></div><label>From<input className="input" type="date" value={startDate} onChange={event => setStartDate(event.target.value)} required /></label><label>To<input className="input" type="date" value={endDate} onChange={event => setEndDate(event.target.value)} aria-invalid={invalid || undefined} required /></label><button className="button" type="submit" disabled={loading || !startDate || !endDate || invalid}>{loading ? 'Loading…' : 'Load overview'}</button></form>
      {invalid ? <p className="date-error" role="alert">From date must be on or before To date.</p> : null}
      {loading ? <DashboardState title="Loading your overview" description="Retrieving authorized sales, profit and inventory records." loading /> : null}
      {error ? <DashboardState title="Unable to load dashboard data" description={error} action={<button className="button" onClick={retry}>Retry</button>} /> : null}
      {!loading && !error && !data ? <DashboardState title="Select a reporting period" description="Dashboard figures will appear after you choose a start and end date." /> : null}
      {data ? <DashboardData data={data} /> : null}
    </>}
  </>
}

function DashboardState({ title, description, action, loading = false }: { title: string; description: string; action?: ReactNode; loading?: boolean }) {
  return <Card className="dashboard-state" aria-busy={loading || undefined}><div className={loading ? 'dashboard-spinner' : 'dashboard-state-icon'} aria-hidden="true">{loading ? '' : '○'}</div><h2>{title}</h2><p>{description}</p>{action ? <div className="dashboard-state-action">{action}</div> : null}</Card>
}

function DashboardData({ data }: { data: DashboardSummary }) {
  const sales = data.sales.totals
  const incompleteProfit = data.profit.estimated_operational_profit === null
  const noSales = sales.delivered_order_count === 0
  return <>
    <div className="dashboard-period-label"><span>Showing</span><strong>{data.period.start_date}</strong><span>to</span><strong>{data.period.end_date}</strong><Badge>{data.period.store_timezone}</Badge></div>
    {noSales ? <Card className="dashboard-empty-period"><div><p className="eyebrow">NO ELIGIBLE SALES</p><h2>No delivered orders found for this period</h2><p>The response contains no eligible delivery events. This does not prove the period’s data coverage is complete.</p></div></Card> : <>
      <section className="dashboard-kpis" aria-label="Dashboard metrics"><Kpi label="Delivered net sales" value={money.format(Number(sales.delivered_net_sales_before_reversals))} note="Before reversal adjustments" /><Kpi label="Delivered orders" value={String(sales.delivered_order_count)} note="Original delivery evidence" /><Kpi label="Estimated profit" value={incompleteProfit ? 'Incomplete' : money.format(Number(data.profit.estimated_operational_profit))} note={incompleteProfit ? 'Some recorded costs are missing' : data.profit.completeness_status} tone={incompleteProfit ? 'warning' : undefined} /><Kpi label="Low-stock watch" value={String(data.inventory.low_stock_count)} note={`${data.inventory.configured_threshold_count} thresholds configured`} /></section>
      {incompleteProfit ? <div className="dashboard-warning" role="status"><strong>Some transactions have missing cost information.</strong><span>Estimated profit may be incomplete until all recorded costs are available.</span></div> : null}
      <section className="dashboard-content-grid"><Card className="dashboard-products"><div className="section-heading"><div><p className="eyebrow">PRODUCT PERFORMANCE</p><h2>Delivered product sales</h2><p>Quantity and gross sales from eligible delivery events.</p></div><Badge>{data.products.products.length} products</Badge></div><div className="table-wrap" tabIndex={0}><table><caption className="sr-only">Delivered product sales for the selected period</caption><thead><tr><th>Product ID</th><th>Units</th><th>Delivered gross sales</th></tr></thead><tbody>{data.products.products.map(product => <tr key={product.product_id}><td className="dashboard-product-id">{product.product_id}</td><td>{product.delivered_units}</td><td>{money.format(Number(product.delivered_gross_sales))}</td></tr>)}</tbody></table></div></Card><div className="dashboard-side-stack"><Card className="dashboard-unavailable"><p className="eyebrow">REVENUE TREND</p><h2>Trend unavailable</h2><p>A daily or weekly time-series endpoint is not available yet, so SellerOS does not draw an estimated chart.</p><a className="text-link" href="/analytics">View analytics <span aria-hidden="true">→</span></a></Card><Card className="dashboard-stock-summary"><p className="eyebrow">INVENTORY</p><h2>Stock attention</h2><p><strong>{data.inventory.low_stock_count}</strong> products are at or below their configured threshold.</p><a className="text-link" href="/inventory">Review inventory <span aria-hidden="true">→</span></a></Card></div></section>
    </>}
  </>
}

function Kpi({ label, value, note, tone }: { label: string; value: string; note: string; tone?: 'warning' }) {
  return <Card className={`dashboard-kpi${tone ? ` dashboard-kpi-${tone}` : ''}`}><p>{label}</p><strong>{value}</strong><span>{note}</span></Card>
}
