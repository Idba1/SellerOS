import { useState } from 'react'
import { Badge, Card } from '../ui/primitives'
import { demoDates, demoOrders } from '../dashboard/demo'

const number = new Intl.NumberFormat('en', { maximumFractionDigits: 2 })
type View = 'sample' | 'loading' | 'empty' | 'error' | 'unavailable'
export function Analytics() {
  const [from, setFrom] = useState(demoDates[0])
  const [to, setTo] = useState(demoDates[demoDates.length - 1])
  const [view, setView] = useState<View>('sample')
  const invalid = Boolean(from && to && from > to)
  const dates = demoDates.filter(date => (!from || date >= from) && (!to || date <= to))
  const records = demoOrders.filter(order => dates.includes(order.date))
  const delivered = records.filter(order => order.status === 'Delivered')
  const total = delivered.reduce((sum, order) => sum + order.amount, 0)
  const series = dates.map(date => ({ date, amount: delivered.filter(order => order.date === date).reduce((sum, order) => sum + order.amount, 0) }))
  const maximum = Math.max(100, ...series.map(point => point.amount))
  const reset = () => { setFrom(demoDates[0]); setTo(demoDates[demoDates.length - 1]) }
  return <>
    <div className="page-heading"><div><p className="eyebrow">BUSINESS ANALYTICS</p><h1>Analytics</h1><p className="page-description">Review recorded sales patterns with clear context and limitations.</p></div><Badge tone="accent">Synthetic demo</Badge></div>
    <div className="demo-notice"><div><strong>Presentation preview — not measured seller performance</strong><p>Uses the dashboard's synthetic orders for 8–14 October 2026. Values are fictional units; no analytics API is connected. No AI explanation or prediction is generated.</p></div><label>Preview state<select aria-label="Preview state" className="input" value={view} onChange={event => setView(event.target.value as View)}><option value="sample">Sample data</option><option value="unavailable">Live data unavailable</option><option value="loading">Loading preview</option><option value="empty">Empty preview</option><option value="error">Error preview</option></select></label></div>
    {view !== 'sample' ? <Card className="dashboard-state" aria-live="polite" aria-busy={view === 'loading'}><h2>{view === 'loading' ? 'Loading analytics preview' : view === 'empty' ? 'No analytics records in this preview' : view === 'error' ? 'Unable to load — simulated error' : 'Live analytics is unavailable'}</h2><p>{view === 'loading' ? 'Static state demonstration; no request is running.' : view === 'error' ? 'Demonstration only; no backend request failed.' : 'Verified metrics, an authorized endpoint and a response schema are required. Unavailable metrics are not zero.'}</p><button className="button" onClick={() => setView('sample')}>Show synthetic sample</button></Card> : <>
      <Card className="analytics-controls"><div className="section-heading"><div><h2>Choose a demo date range</h2><p>Inclusive order dates · fixture coverage: 8–14 Oct 2026</p></div><div className="analytics-filters"><label>From date<input className="input" type="date" value={from} onChange={event => setFrom(event.target.value)} aria-invalid={invalid || undefined} aria-describedby="analytics-range-note" /></label><label>To date<input className="input" type="date" value={to} onChange={event => setTo(event.target.value)} aria-invalid={invalid || undefined} aria-describedby="analytics-range-note" /></label><button className="button" onClick={reset}>Reset range</button></div></div><p id="analytics-range-note" className={invalid ? 'date-error' : 'table-note'} role={invalid ? 'alert' : undefined}>{invalid ? 'From date must be on or before To date.' : 'This is a fixed demo window, not complete sales history. Ranges outside coverage have no data.'}</p></Card>
      {invalid ? null : records.length === 0 ? <Card className="dashboard-state" role="status"><h2>No demo records in this range</h2><p>Choose dates within the fixture coverage. Missing history is not proof of zero revenue.</p></Card> : <>
        <div className="analytics-metrics">{[
          ['Sample revenue', number.format(total), 'Delivered demo amounts · fictional units'],
          ['Delivered demo orders', String(delivered.length), 'Selected synthetic order dates'],
          ['Sample average order value', delivered.length ? number.format(total / delivered.length) : 'Unavailable', 'Delivered demo amounts only'],
        ].map(([label, value, note]) => <Card key={label}><h2>{label}</h2><p className="analytics-value">{value}</p><p className="table-note">{note}</p></Card>)}</div>
        <Card aria-labelledby="analytics-chart-title"><div className="section-heading"><div><h2 id="analytics-chart-title">Daily sample revenue</h2><p>Delivered records only · fictional units</p></div><Badge>Descriptive preview</Badge></div><div className="chart-wrap" tabIndex={0} role="region" aria-label="Scrollable daily sample revenue chart"><svg className="revenue-chart" viewBox="0 0 760 240" role="img" aria-labelledby="analytics-svg-title analytics-svg-desc"><title id="analytics-svg-title">Synthetic revenue by day</title><desc id="analytics-svg-desc">{series.map(point => `${point.date}: ${point.amount} fictional units`).join('; ')}</desc>{[0, maximum / 2, maximum].map(value => <g key={value}><line x1="60" x2="740" y1={190 - value / maximum * 150} y2={190 - value / maximum * 150} stroke="#e2e7ef" /><text x="48" y={194 - value / maximum * 150} textAnchor="end">{number.format(value)}</text></g>)}{series.map((point, index) => { const width = 680 / series.length; const height = point.amount / maximum * 150; return <g key={point.date}><rect x={60 + index * width + width * .25} y={190 - height} width={width * .5} height={height} rx="4" fill="#2458bd" /><text x={60 + index * width + width / 2} y="218" textAnchor="middle">Oct {Number(point.date.slice(-2))}</text></g> })}</svg></div>
          <details className="chart-data"><summary>View chart values as a table</summary><table><caption>Synthetic daily values; zero means no delivered fixture amount for that date</caption><thead><tr><th scope="col">Date</th><th scope="col">Fictional units</th></tr></thead><tbody>{series.map(point => <tr key={point.date}><th scope="row">{point.date}</th><td>{number.format(point.amount)}</td></tr>)}</tbody></table></details>
        </Card>
      </>}
    </>}
    <Card className="analytics-limitations" aria-labelledby="analytics-limitations-title"><h2 id="analytics-limitations-title">Available evidence, honest boundaries</h2><p>These fixture calculations demonstrate presentation only. They do not implement production revenue recognition, returns, expense allocation, profit or accuracy evaluation.</p><div className="analytics-unavailable">{['Profit and margin', 'Demand forecasts', 'AI business recommendations', 'Customer segmentation', 'What-if estimates'].map(label => <div key={label}><strong>{label}</strong><Badge>Unavailable</Badge></div>)}</div><p><strong>[DECISION REQUIRED]</strong> Production financial definitions, date/currency rules, segmentation thresholds, forecast sufficiency/evaluation and scenario assumptions remain governed by the open planning decisions. No causal claims or numeric AI results are shown.</p></Card>
  </>
}
