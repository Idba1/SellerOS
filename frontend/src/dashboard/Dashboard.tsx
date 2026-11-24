import { useState } from 'react'
import { getApiClient } from '../api/config'
import type { DashboardSummary } from '../api/types'
import { Badge, Card } from '../ui/primitives'

const money = new Intl.NumberFormat('en-BD', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function decodeDashboard(value: unknown): DashboardSummary {
  if (!value || typeof value !== 'object' || !('period' in value) || !('sales' in value) || !('profit' in value) || !('products' in value) || !('inventory' in value)) throw new Error('Invalid dashboard response.')
  return value as DashboardSummary
}

export function Dashboard() {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [data, setData] = useState<DashboardSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const invalid = Boolean(startDate && endDate && startDate > endDate)
  async function load() {
    if (!startDate || !endDate || invalid) return
    setLoading(true); setError(null)
    try { setData(await getApiClient().request('analytics/dashboard/', { query: { start_date: startDate, end_date: endDate }, decode: decodeDashboard }) ?? null) }
    catch { setData(null); setError('Dashboard data is unavailable. Sign in and confirm backend API configuration, then try again.') }
    finally { setLoading(false) }
  }
  return <>
    <div className="page-heading"><div><p className="eyebrow">YOUR BUSINESS AT A GLANCE</p><h1>Dashboard</h1><p className="page-description">Verified sales, profit, product and stock summaries for a selected period.</p></div><Badge tone="accent">Live API</Badge></div>
    <Card className="dashboard-controls"><div><h2>Choose a reporting period</h2><p>Store-local inclusive dates. No default range is applied.</p></div><label>From<input className="input" type="date" value={startDate} onChange={e => setStartDate(e.target.value)} /></label><label>To<input className="input" type="date" value={endDate} onChange={e => setEndDate(e.target.value)} aria-invalid={invalid || undefined} /></label><button className="button" onClick={load} disabled={!startDate || !endDate || invalid || loading}>{loading ? 'Loading…' : 'Load dashboard'}</button></Card>
    {invalid && <p className="date-error" role="alert">From date must be on or before To date.</p>}
    {error && <Card className="dashboard-state" role="alert"><h2>Unable to load dashboard</h2><p>{error}</p></Card>}
    {loading && <Card className="dashboard-state" aria-busy="true"><h2>Loading dashboard</h2><p>Retrieving authorized store records.</p></Card>}
    {!loading && !error && !data && <Card className="dashboard-state"><h2>Select a period</h2><p>Metrics appear only after an authorized API response.</p></Card>}
    {data && <><div className="kpi-grid"><Kpi label="Delivered net sales" value={`BDT ${money.format(Number(data.sales.totals.delivered_net_sales_before_reversals))}`} note="Base delivered sales; not retained sales." /><Kpi label="Delivered orders" value={String(data.sales.totals.delivered_order_count)} note="Original delivery evidence only." /><Kpi label="Estimated profit" value={data.profit.estimated_operational_profit === null ? 'Unavailable' : `BDT ${money.format(Number(data.profit.estimated_operational_profit))}`} note={data.profit.completeness_status} /><Kpi label="Low-stock attention" value={String(data.inventory.low_stock_count)} note={`${data.inventory.configured_threshold_count} configured thresholds.`} /></div><Card><div className="section-heading"><div><h2>Product sales</h2><p>Delivered quantity and gross sales; not a profit ranking.</p></div><Badge>{data.period.store_timezone}</Badge></div>{data.products.products.length === 0 ? <p>No eligible product sales in this period.</p> : <div className="table-wrap" tabIndex={0}><table><caption className="sr-only">Product sales for selected period</caption><thead><tr><th>Product ID</th><th>Units</th><th>Delivered gross sales</th></tr></thead><tbody>{data.products.products.map(product => <tr key={product.product_id}><td>{product.product_id}</td><td>{product.delivered_units}</td><td>BDT {money.format(Number(product.delivered_gross_sales))}</td></tr>)}</tbody></table></div>}</Card><Card className="dashboard-disclosure"><h2>Calculation boundary</h2><p>Profit is an estimated operational metric from recorded snapshots and expenses. Tax, gateway fees, cash collection and unrecorded costs are excluded. Daily chart data is unavailable because no approved time-series endpoint exists.</p></Card></>}
  </>
}

function Kpi({ label, value, note }: { label: string; value: string; note: string }) {
  return <Card className="kpi-card"><h2>{label}</h2><p className="kpi-value">{value}</p><p>{note}</p></Card>
}
