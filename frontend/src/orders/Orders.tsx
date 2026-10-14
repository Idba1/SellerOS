import { useState } from 'react'
import { Badge, Card } from '../ui/primitives'
import { demoOrders } from './demo'

const number = new Intl.NumberFormat('en', { maximumFractionDigits: 2 })
const dateFormat = new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' })
const formatDate = (date: string) => dateFormat.format(new Date(`${date}T00:00:00Z`))
type View = 'sample' | 'loading' | 'empty' | 'error' | 'unavailable'
export function Orders() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [view, setView] = useState<View>('sample')
  const invalidRange = Boolean(from && to && from > to)
  const filtered = demoOrders.filter(order => !invalidRange && `${order.id} ${order.customer}`.toLowerCase().includes(search.trim().toLowerCase()) && (status === 'all' || order.status === status) && (!from || order.date >= from) && (!to || order.date <= to))
  const reset = () => { setSearch(''); setStatus('all'); setFrom(''); setTo('') }
  return <>
    <div className="page-heading"><div><p className="eyebrow">ORDER WORKSPACE</p><h1>Orders</h1><p className="page-description">Review order records and fulfillment progress in one place.</p></div><Badge tone="accent">Synthetic demo</Badge></div>
    <div className="demo-notice"><div><strong>Read-only presentation — no live orders connected</strong><p>Fictional orders and customer labels only. Amounts use demo units; no payment, refund or stock effects are modeled. Nothing is saved.</p></div><label>Preview state<select className="input" aria-label="Preview state" value={view} onChange={event => setView(event.target.value as View)}><option value="sample">Sample data</option><option value="unavailable">Live data unavailable</option><option value="loading">Loading preview</option><option value="empty">Empty preview</option><option value="error">Error preview</option></select></label></div>
    {view !== 'sample' ? <Card className="dashboard-state" aria-live="polite" aria-busy={view === 'loading'}><h2>{view === 'loading' ? 'Loading orders preview' : view === 'empty' ? 'No orders in this preview' : view === 'error' ? 'Unable to load — simulated error' : 'Live orders are not connected'}</h2><p>{view === 'loading' ? 'Static loading demonstration; no request is running.' : view === 'empty' ? 'Order counts are unavailable until records exist.' : view === 'error' ? 'This is a safe error-state demonstration, not a failed backend request.' : 'An approved order response contract and authorized endpoints are required.'}</p><button className="button" onClick={() => setView('sample')}>Show synthetic sample</button></Card> : <>
      <div className="order-summary">{[
        ['Demo orders', demoOrders.length],
        ['Processing', demoOrders.filter(order => order.status === 'Processing').length],
        ['Shipped', demoOrders.filter(order => order.status === 'Shipped').length],
        ['Delivered', demoOrders.filter(order => order.status === 'Delivered').length],
      ].map(([label, count]) => <Card key={label}><h2>{label}</h2><p className="order-count">{count}</p><p className="table-note">Entire synthetic sample · not filtered</p></Card>)}</div>
      <Card aria-labelledby="orders-list-title"><div className="section-heading"><div><h2 id="orders-list-title">Demo order records</h2><p aria-live="polite">{invalidRange ? 'Check the date range to view results' : `Showing ${filtered.length} of ${demoOrders.length} synthetic orders`}</p></div><Badge>Read-only</Badge></div>
        <div className="order-filters"><label>Search demo orders<input className="input" type="search" placeholder="Order reference or demo customer" value={search} onChange={event => setSearch(event.target.value)} /></label><label>Fulfillment status<select className="input" aria-label="Fulfillment status" value={status} onChange={event => setStatus(event.target.value)}><option value="all">All sample statuses</option>{[...new Set(demoOrders.map(order => order.status))].map(value => <option key={value}>{value}</option>)}</select></label><label>From date<input className="input" type="date" value={from} onChange={event => setFrom(event.target.value)} aria-invalid={invalidRange || undefined} aria-describedby="date-range-note" /></label><label>To date<input className="input" type="date" value={to} onChange={event => setTo(event.target.value)} aria-invalid={invalidRange || undefined} aria-describedby="date-range-note" /></label><button className="button order-reset" onClick={reset}>Clear filters</button></div>
        <p id="date-range-note" className={invalidRange ? 'date-error' : 'table-note'} role={invalidRange ? 'alert' : undefined}>{invalidRange ? 'From date must be on or before To date.' : 'Date limits are inclusive and apply to the demo order date, not delivery/payment date.'}</p>
        {invalidRange ? null : filtered.length === 0 ? <div className="order-empty" role="status"><h3>No matching demo orders</h3><p>Try another search or clear filters. No records have been changed.</p></div> : <div className="table-wrap"><table className="order-table"><caption className="sr-only">Synthetic orders; amounts in fictional units, payment status unavailable</caption><thead><tr><th scope="col">Order / date</th><th scope="col">Demo customer</th><th scope="col">Demo total</th><th scope="col">Fulfillment</th><th scope="col">Details</th></tr></thead><tbody>{filtered.map(order => <tr key={order.id}><th scope="row">{order.id}<small>{formatDate(order.date)}</small></th><td>{order.customer}</td><td>{number.format(order.amount)} units</td><td><Badge tone={order.status === 'Delivered' ? 'accent' : 'neutral'}>{order.status}</Badge></td><td><details className="order-details"><summary aria-label={`View demo details for ${order.id}`}>View details</summary><dl><dt>Product</dt><dd>{order.product}</dd><dt>Quantity</dt><dd>{order.quantity}</dd><dt>Demo total</dt><dd>{number.format(order.amount)} fictional units</dd><dt>Payment information</dt><dd>Not included in this fixture</dd></dl><p>Read-only record. No transitions or revenue recognition are performed.</p></details></td></tr>)}</tbody></table></div>}
        <p className="table-note">Status labels are a subset of the approved planning labels. Displaying a label does not implement the order state machine.</p>
      </Card>
    </>}
    <Card className="order-boundaries" aria-labelledby="order-boundaries-title"><h2 id="order-boundaries-title">Review now, manage when connected</h2><p>Search, status/date filters and read-only details operate locally on synthetic records. There are no status-change, cancellation, refund or payment actions.</p><p><strong>[DECISION REQUIRED]</strong> Production order schema, payment representation, currency/rounding, date semantics and unresolved PLAN-03 transitions/refund rules remain pending. Live access requires authenticated, store-scoped backend support through the existing shared API client.</p></Card>
  </>
}
