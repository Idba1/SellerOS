import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { ApiClientError } from '../api/client'
import { getApiClient } from '../api/config'
import { getAuthSession } from '../auth/session'
import { decodeCustomerPage, type Customer } from '../customers/api'
import { Badge, Card } from '../ui/primitives'

type Assignment = {
  segment: string
  rule_version: string
  as_of: string
  store_timezone: string
  values: { recorded_purchase_count: number; last_recorded_purchase_at: string | null; recency_days: number | null; trailing_365_day_spend_bdt: string }
  explanation: string
}

const money = new Intl.NumberFormat('en-BD', { style: 'currency', currency: 'BDT', minimumFractionDigits: 2, maximumFractionDigits: 2 })

function decodeAssignment(value: unknown): Assignment {
  if (value === null || typeof value !== 'object' || !('segment' in value) || typeof value.segment !== 'string' || !('rule_version' in value) || typeof value.rule_version !== 'string' || !('as_of' in value) || typeof value.as_of !== 'string' || !('store_timezone' in value) || typeof value.store_timezone !== 'string' || !('values' in value) || value.values === null || typeof value.values !== 'object' || !('explanation' in value) || typeof value.explanation !== 'string') throw new Error('Invalid segmentation response.')
  return value as Assignment
}

function message(error: unknown) {
  if (error instanceof ApiClientError && error.isAuthError) return 'Your session is no longer authorized. Sign in again to continue.'
  if (error instanceof ApiClientError && error.status === 404) return 'This customer is not available in your authorized store.'
  if (error instanceof ApiClientError && error.kind === 'network') return 'SellerOS could not reach the service. Check your connection and try again.'
  if (error instanceof Error && error.message.includes('VITE_API_BASE_URL')) return 'Segmentation is unavailable until the frontend API URL is configured.'
  return 'SellerOS could not calculate this customer segment. Please try again.'
}

function currentUtcInput() {
  return new Date().toISOString().slice(0, 16)
}

export function Segments() {
  const signedIn = Boolean(getAuthSession())
  const [customers, setCustomers] = useState<Customer[]>([])
  const [customerId, setCustomerId] = useState('')
  const [asOf, setAsOf] = useState(currentUtcInput)
  const [assignment, setAssignment] = useState<Assignment | null>(null)
  const [loadingCustomers, setLoadingCustomers] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!signedIn) return
    let active = true
    setLoadingCustomers(true)
    getApiClient().request('customers/', { query: { page_size: 100 }, decode: decodeCustomerPage })
      .then(page => { if (active) { setCustomers(page?.results ?? []); setCustomerId(current => current || page?.results[0]?.id || '') } })
      .catch(requestError => { if (active) setError(message(requestError)) })
      .finally(() => { if (active) setLoadingCustomers(false) })
    return () => { active = false }
  }, [signedIn])

  async function calculate() {
    if (!customerId || !asOf) return
    setLoading(true); setError(null); setAssignment(null)
    try {
      const response = await getApiClient().request(`customers/${customerId}/segment/`, { query: { as_of: `${asOf}:00Z` }, decode: decodeAssignment })
      setAssignment(response ?? null)
    } catch (requestError) { setError(message(requestError)) } finally { setLoading(false) }
  }

  return <>
    <div className="segments-hero"><div><p className="eyebrow">CUSTOMER INTELLIGENCE</p><h1>Customer segmentation</h1><p className="page-description">Review a transparent purchase-behaviour group for one authorized customer at a time.</p></div><Badge tone="accent">Rule-based</Badge></div>
    {!signedIn ? <State title="Sign in to review segments" description="Customer segmentation is available only to an authenticated SellerOS account." /> : <>
      <Card className="segments-policy"><div><p className="eyebrow">EVIDENCE-BOUND ASSIGNMENT</p><h2>Use recorded delivered-order facts</h2><p>The service returns one versioned rule outcome for the chosen customer and time. It does not predict future customer value or make automated decisions.</p></div><a className="text-link" href="/customers">Review customer records <span aria-hidden="true">→</span></a></Card>
      <form className="card segments-controls" onSubmit={(event: FormEvent<HTMLFormElement>) => { event.preventDefault(); void calculate() }}>
        <label>Customer<select className="input" value={customerId} onChange={event => setCustomerId(event.target.value)} disabled={loadingCustomers || customers.length === 0} required><option value="">{loadingCustomers ? 'Loading customers…' : 'Choose a customer'}</option>{customers.map(customer => <option key={customer.id} value={customer.id}>{customer.display_name}</option>)}</select></label>
        <label>As of (UTC)<input className="input" type="datetime-local" value={asOf} onChange={event => setAsOf(event.target.value)} required /></label>
        <button className="button" disabled={!customerId || !asOf || loading || loadingCustomers}>{loading ? 'Calculating…' : 'Calculate segment'}</button>
      </form>
      {error ? <State title="Unable to load segmentation" description={error} action={<button className="button" onClick={() => void calculate()}>Retry</button>} /> : null}
      {!error && !loading && !loadingCustomers && customers.length === 0 ? <State title="No customer records yet" description="Add an authorized customer record before calculating a behaviour segment." action={<a className="button" href="/customers">Open customers</a>} /> : null}
      {loading ? <State title="Calculating segment" description="Checking eligible recorded-order facts for this customer." /> : null}
      {!loading && !error && !assignment && customers.length > 0 ? <State title="Choose a customer and time" description="The result will include the segment, source values, and an explanation of the rule used." /> : null}
      {assignment ? <AssignmentView assignment={assignment} /> : null}
    </>}
  </>
}

function AssignmentView({ assignment }: { assignment: Assignment }) {
  const values = assignment.values
  const lastPurchase = values.last_recorded_purchase_at ? new Intl.DateTimeFormat('en-BD', { dateStyle: 'medium', timeZone: assignment.store_timezone }).format(new Date(values.last_recorded_purchase_at)) : 'No eligible purchase'
  return <section className="segments-result" aria-live="polite"><Card className="segments-result-head"><div><p className="eyebrow">CURRENT ASSIGNMENT</p><h2>{label(assignment.segment)}</h2><p>{assignment.explanation}</p></div><Badge tone="accent">{assignment.rule_version}</Badge></Card><div className="segments-values"><Metric label="Recorded purchases" value={String(values.recorded_purchase_count)} /><Metric label="Last eligible purchase" value={lastPurchase} /><Metric label="Recency" value={values.recency_days === null ? 'Unavailable' : `${values.recency_days} days`} /><Metric label="Trailing 365-day spend" value={money.format(Number(values.trailing_365_day_spend_bdt))} /></div><Card className="segments-evidence"><p className="eyebrow">CALCULATION CONTEXT</p><p>The assignment is calculated as of <strong>{new Intl.DateTimeFormat('en-BD', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' }).format(new Date(assignment.as_of))} UTC</strong>. Store timezone: <strong>{assignment.store_timezone}</strong>.</p><p>Only eligible purchase history in the authorized store is considered. The source values above are returned by the server with this assignment.</p></Card></section>
}

function label(value: string) { return value.split('_').map(part => part.charAt(0) + part.slice(1).toLowerCase()).join(' ') }
function Metric({ label, value }: { label: string; value: string }) { return <Card className="segments-metric"><p>{label}</p><strong>{value}</strong></Card> }
function State({ title, description, action }: { title: string; description: string; action?: ReactNode }) { return <Card className="products-state"><span className="products-state-mark" aria-hidden="true">□</span><h2>{title}</h2><p>{description}</p>{action ? <div>{action}</div> : null}</Card> }
