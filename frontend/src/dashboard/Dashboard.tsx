import { useState } from 'react'
import { Badge, Card } from '../ui/primitives'
import { demoOverview } from './demo'

const number = new Intl.NumberFormat('en', { maximumFractionDigits: 2 })
type View = 'sample' | 'unavailable' | 'loading' | 'empty' | 'error'
export function Dashboard() {
  const [view, setView] = useState<View>('sample')
  const [days, setDays] = useState<3 | 7>(7)
  const data = demoOverview(days)
  const maximum = Math.max(100, ...data.series.map(point => point.amount))
  const ticks = [0, maximum / 2, maximum]
  return <>
    <div className="page-heading"><div><p className="eyebrow">YOUR BUSINESS AT A GLANCE</p><h1>Dashboard</h1><p className="page-description">Connect your records. Understand sales. Plan your next move.</p></div><Badge tone="accent">Synthetic demo</Badge></div>
    <div className="demo-notice"><div><strong>Presentation preview — not real seller performance</strong><p>No dashboard API exists yet. Sample figures use fictional monetary units, fixed dates and synthetic records. No forecasts or AI results are shown.</p></div><label>Preview state<select className="input" value={view} onChange={event => setView(event.target.value as View)}><option value="sample">Sample data</option><option value="unavailable">Live data unavailable</option><option value="loading">Loading preview</option><option value="empty">Empty preview</option><option value="error">Error preview</option></select></label></div>
    {view !== 'sample' ? <Card className="dashboard-state" aria-live="polite" aria-busy={view === 'loading'}>
      <h2>{view === 'loading' ? 'Loading preview' : view === 'empty' ? 'No records in this preview' : view === 'error' ? 'Unable to load — simulated error' : 'Live dashboard is not connected'}</h2>
      <p>{view === 'loading' ? 'This is a static loading-state demonstration; no request is running.' : view === 'empty' ? 'Metrics remain unavailable until records exist. Missing data is not treated as zero revenue.' : view === 'error' ? 'This state demonstrates a safe error message, not a failed backend request.' : 'A metric response contract and authorized endpoint are required before live data can be shown.'}</p>
      <button className="button" onClick={() => setView('sample')}>Show synthetic sample</button>
    </Card> : <>
      <div className="kpi-grid">
        {[
          ['Sample revenue', number.format(data.revenue), 'Fictional units · delivered demo orders'],
          ['Sample orders', String(data.orders.length), `All statuses · selected ${days} days`],
          ['Sample average order value', number.format(data.average), 'Fictional units · delivered demo orders'],
          ['Products requiring attention', String(data.attention.length), 'At or below demo stock thresholds'],
        ].map(([label, value, note]) => <Card className="kpi-card" key={label}><h2>{label}</h2><p className="kpi-value">{value}</p><p className="kpi-note">{note}</p></Card>)}
      </div>
      <Card className="sales-card" aria-labelledby="sales-title">
        <div className="section-heading"><div><h2 id="sales-title">Sample revenue overview</h2><p>Delivered demo orders · fictional units</p></div><label>Demo period<select className="input" value={days} onChange={event => setDays(Number(event.target.value) as 3 | 7)}><option value={7}>8–14 Oct 2026</option><option value={3}>12–14 Oct 2026</option></select></label></div>
        <div className="chart-wrap"><svg className="revenue-chart" viewBox="0 0 760 240" role="img" aria-labelledby="chart-title chart-description"><title id="chart-title">Synthetic daily revenue</title><desc id="chart-description">{data.series.map(point => `${point.date}: ${point.amount} fictional units`).join('; ')}</desc>
          {ticks.map(value => <g key={value}><line x1="60" x2="740" y1={190 - value / maximum * 150} y2={190 - value / maximum * 150} stroke="#e2e7ef" /><text x="48" y={194 - value / maximum * 150} textAnchor="end">{number.format(value)}</text></g>)}
          {data.series.map((point, index) => { const width = 680 / data.series.length; const x = 60 + index * width; const height = point.amount / maximum * 150; return <g key={point.date}><rect x={x + width * .25} y={190 - height} width={width * .5} height={height} rx="4" fill="#2458bd" /><text x={x + width / 2} y="218" textAnchor="middle">Oct {Number(point.date.slice(-2))}</text></g> })}
        </svg></div>
        <details className="chart-data"><summary>View chart values as a table</summary><table><caption>Synthetic revenue by date, in fictional units</caption><thead><tr><th scope="col">Date</th><th scope="col">Revenue</th></tr></thead><tbody>{data.series.map(point => <tr key={point.date}><th scope="row">{point.date}</th><td>{number.format(point.amount)}</td></tr>)}</tbody></table></details>
      </Card>
      <div className="dashboard-bottom">
        <Card aria-labelledby="orders-title"><div className="section-heading"><div><h2 id="orders-title">Recent demo orders</h2><p>Synthetic records · selected period</p></div><a className="text-link" href="/orders">Order workspace →</a></div><div className="table-wrap"><table><caption className="sr-only">Recent synthetic orders</caption><thead><tr><th scope="col">Order / date</th><th scope="col">Product</th><th scope="col">Amount*</th><th scope="col">Status</th></tr></thead><tbody>{data.orders.map(order => <tr key={order.id}><th scope="row">{order.id}<small>{order.date}</small></th><td>{order.item}</td><td>{number.format(order.amount)}</td><td><Badge tone={order.status === 'Delivered' ? 'accent' : 'neutral'}>{order.status}</Badge></td></tr>)}</tbody></table></div><p className="table-note">*Fictional units. Amount is not necessarily recognized revenue.</p></Card>
        <Card aria-labelledby="inventory-title"><h2 id="inventory-title">Demo inventory attention</h2><p className="page-description">Illustrative seller-set thresholds</p><ul className="stock-list">{data.attention.map(product => <li key={product.name}><div><strong>{product.name}</strong><small>Demo threshold: {product.threshold}</small></div><Badge>{product.stock} remaining</Badge></li>)}</ul><a className="text-link" href="/inventory">Inventory workspace →</a></Card>
      </div>
      <p className="dashboard-disclosure">These presentation calculations are not approved production financial formulas. Returns, discounts, costs and profit are not modeled in this fixture.</p>
    </>}
  </>
}
