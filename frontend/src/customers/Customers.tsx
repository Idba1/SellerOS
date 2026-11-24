import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { ApiClientError } from '../api/client'
import { getApiClient } from '../api/config'
import { getAuthSession } from '../auth/session'
import { Badge, Card } from '../ui/primitives'
import { decodeCustomer, decodeCustomerHistory, decodeCustomerPage, type Customer, type CustomerHistory, type CustomerPayload } from './api'

const PAGE_SIZE = 20
const money = new Intl.NumberFormat('en-BD', { style: 'currency', currency: 'BDT', minimumFractionDigits: 2, maximumFractionDigits: 2 })
const shortDate = new Intl.DateTimeFormat('en-BD', { dateStyle: 'medium' })

function errorMessage(error: unknown, task: 'customers' | 'details' | 'save') {
  if (error instanceof ApiClientError && error.isAuthError) return 'Your session is no longer authorized. Sign in again to continue.'
  if (error instanceof ApiClientError && error.status === 404) return 'Finish store setup before accessing customer records.'
  if (error instanceof ApiClientError && error.kind === 'network') return 'SellerOS could not reach the service. Check your connection and try again.'
  if (error instanceof Error && error.message.includes('VITE_API_BASE_URL')) return 'Customer data is unavailable until the frontend API URL is configured.'
  return task === 'save' ? 'SellerOS could not save this customer. Review the fields and try again.' : `SellerOS could not load customer ${task}. Please try again.`
}
function contactLabel(customer: Customer) { return customer.email || customer.phone || 'No contact recorded' }

export function Customers() {
  const hasSession = Boolean(getAuthSession())
  const [page, setPage] = useState(1)
  const [customers, setCustomers] = useState<Customer[]>([])
  const [total, setTotal] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Customer | null>(null)
  const [history, setHistory] = useState<CustomerHistory | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [formMode, setFormMode] = useState<'create' | 'edit' | null>(null)

  async function loadCustomers(nextPage: number) {
    if (!hasSession) return
    setLoading(true); setError(null); setSelected(null); setHistory(null); setDetailError(null)
    try {
      const response = await getApiClient().request('customers/', { query: { page: nextPage, page_size: PAGE_SIZE }, decode: decodeCustomerPage })
      setCustomers(response?.results ?? []); setTotal(response?.count ?? 0)
    } catch (requestError) { setCustomers([]); setTotal(null); setError(errorMessage(requestError, 'customers')) }
    finally { setLoading(false) }
  }
  useEffect(() => { void loadCustomers(1) }, [])

  async function inspectCustomer(customerId: string) {
    setDetailLoading(true); setDetailError(null); setSelected(null); setHistory(null)
    try {
      const api = getApiClient()
      const [customer, purchaseHistory] = await Promise.all([
        api.request(`customers/${customerId}/`, { decode: decodeCustomer }),
        api.request(`customers/${customerId}/purchase-history/`, { decode: decodeCustomerHistory }),
      ])
      setSelected(customer ?? null); setHistory(purchaseHistory ?? null)
    } catch (requestError) { setDetailError(errorMessage(requestError, 'details')) }
    finally { setDetailLoading(false) }
  }
  function changePage(nextPage: number) { setPage(nextPage); void loadCustomers(nextPage) }

  return <>
    <div className="customers-hero"><div><p className="eyebrow">CUSTOMER RECORDS</p><h1>Customers</h1><p className="page-description">Maintain store-scoped customer details and review recorded purchase history.</p></div><div className="customers-hero-actions"><Badge tone="accent">Live customers</Badge>{hasSession ? <button className="button" onClick={() => setFormMode('create')}>Add customer</button> : null}</div></div>
    {!hasSession ? <CustomersState title="Sign in to view customers" description="Customer records are available only to an authenticated SellerOS account." action={<a className="button" href="/login">Go to sign in</a>} /> : <>
      {formMode ? <CustomerForm mode={formMode} customer={formMode === 'edit' ? selected : null} onCancel={() => setFormMode(null)} onSaved={(saved) => { setFormMode(null); void loadCustomers(page); void inspectCustomer(saved.id) }} /> : null}
      {loading ? <CustomersState title="Loading customers" description="Retrieving authorized customer records." loading /> : null}
      {error ? <CustomersState title="Unable to load customers" description={error} action={<button className="button" onClick={() => void loadCustomers(page)}>Retry</button>} /> : null}
      {!loading && !error && total === 0 ? <CustomersState title="No customer records yet" description="Add a customer when you need a store-owned profile for an order or follow-up." action={<button className="button" onClick={() => setFormMode('create')}>Add customer</button>} /> : null}
      {!loading && !error && total !== null && total > 0 ? <section className="customers-layout"><Card className="customers-table-card"><div className="section-heading"><div><p className="eyebrow">CUSTOMER DIRECTORY</p><h2>{total} {total === 1 ? 'customer' : 'customers'}</h2><p>Page {page} of {Math.ceil(total / PAGE_SIZE)}. The API does not provide search or segmentation filters.</p></div><Badge>Store scoped</Badge></div><div className="table-wrap" tabIndex={0}><table className="customers-table"><caption className="sr-only">Customers in the authorized SellerOS store</caption><thead><tr><th scope="col">Customer</th><th scope="col">Primary contact</th><th scope="col">Phone</th><th scope="col">Added</th><th scope="col"><span className="sr-only">Actions</span></th></tr></thead><tbody>{customers.map(customer => <tr key={customer.id}><th scope="row"><span className="product-name">{customer.display_name}</span><small>{customer.id}</small></th><td>{contactLabel(customer)}</td><td>{customer.phone || '—'}</td><td>{shortDate.format(new Date(customer.created_at))}</td><td><button className="table-action" onClick={() => void inspectCustomer(customer.id)}>Review</button></td></tr>)}</tbody></table></div><div className="products-pagination"><span>Page {page}</span><div><button className="button button-secondary" disabled={loading || page === 1} onClick={() => changePage(page - 1)}>Previous</button><button className="button button-secondary" disabled={loading || customers.length < PAGE_SIZE} onClick={() => changePage(page + 1)}>Next</button></div></div></Card><CustomerPanel customer={selected} history={history} loading={detailLoading} error={detailError} onEdit={() => setFormMode('edit')} /></section> : null}
      <Card className="customer-contract-note"><p className="eyebrow">PRIVACY & DATA SCOPE</p><p>This directory displays only seller-entered contact details and order-derived purchase facts for the current authorized store. It does not infer customer traits, segment customers, or expose another store’s data.</p></Card>
    </>}
  </>
}

function CustomerPanel({ customer, history, loading, error, onEdit }: { customer: Customer | null; history: CustomerHistory | null; loading: boolean; error: string | null; onEdit: () => void }) {
  if (loading) return <aside className="customer-panel"><Card className="product-detail-state"><span className="dashboard-spinner" aria-hidden="true" /><h2>Loading customer details</h2></Card></aside>
  if (!customer) return <aside className="customer-panel"><Card className="product-detail-state"><p className="eyebrow">CUSTOMER DETAILS</p><h2>{error ? 'Details unavailable' : 'Select a customer'}</h2><p>{error || 'Choose Review to inspect the customer profile and derived purchase history.'}</p></Card></aside>
  return <aside className="customer-panel"><Card><div className="section-heading"><div><p className="eyebrow">CUSTOMER DETAILS</p><h2>{customer.display_name}</h2></div><button className="table-action" onClick={onEdit}>Edit</button></div><dl className="customer-facts"><div><dt>Email</dt><dd>{customer.email || 'Not recorded'}</dd></div><div><dt>Phone</dt><dd>{customer.phone || 'Not recorded'}</dd></div></dl><div className="customer-history"><h3>Purchase history</h3>{history ? <dl><div><dt>Eligible purchases</dt><dd>{history.purchase_count}</dd></div><div><dt>Total spend</dt><dd>{money.format(Number(history.total_spend))}</dd></div><div><dt>Last purchase</dt><dd>{history.last_purchase_at ? shortDate.format(new Date(history.last_purchase_at)) : 'No eligible purchase recorded'}</dd></div></dl> : <p>Purchase-history data is unavailable.</p>}<p className="customer-history-note">These are derived from eligible recorded orders and are not editable customer profile fields.</p></div></Card></aside>
}

function CustomerForm({ mode, customer, onCancel, onSaved }: { mode: 'create' | 'edit'; customer: Customer | null; onCancel: () => void; onSaved: (customer: Customer) => void }) {
  const [name, setName] = useState(customer?.display_name ?? ''); const [email, setEmail] = useState(customer?.email ?? ''); const [phone, setPhone] = useState(customer?.phone ?? '')
  const [error, setError] = useState<string | null>(null); const [submitting, setSubmitting] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSubmitting(true); setError(null)
    const body: CustomerPayload = { display_name: name.trim(), email: email.trim() || null, phone: phone.trim() || null }
    try {
      const saved = await getApiClient().request(mode === 'create' ? 'customers/' : `customers/${customer?.id}/`, { method: mode === 'create' ? 'POST' : 'PATCH', body, decode: decodeCustomer })
      if (saved) onSaved(saved)
    } catch (requestError) { setError(errorMessage(requestError, 'save')) }
    finally { setSubmitting(false) }
  }
  return <Card className="customer-form" aria-labelledby="customer-form-title"><div className="section-heading"><div><p className="eyebrow">{mode === 'create' ? 'NEW CUSTOMER' : 'EDIT CUSTOMER'}</p><h2 id="customer-form-title">{mode === 'create' ? 'Add customer' : 'Update customer'}</h2><p>Only profile fields supported by the customer API are included.</p></div><button className="table-action" onClick={onCancel}>Close</button></div>{error ? <p className="product-form-error" role="alert">{error}</p> : null}<form onSubmit={submit}><label>Customer name<input className="input" value={name} onChange={event => setName(event.target.value)} required maxLength={160} /></label><label>Email <span>(optional)</span><input className="input" type="email" value={email} onChange={event => setEmail(event.target.value)} maxLength={254} /></label><label>Phone <span>(optional)</span><input className="input" value={phone} onChange={event => setPhone(event.target.value)} maxLength={32} /></label><div className="customer-form-actions"><button className="button button-secondary" type="button" onClick={onCancel} disabled={submitting}>Cancel</button><button className="button" type="submit" disabled={submitting}>{submitting ? 'Saving…' : mode === 'create' ? 'Add customer' : 'Save changes'}</button></div></form></Card>
}

function CustomersState({ title, description, action, loading = false }: { title: string; description: string; action?: ReactNode; loading?: boolean }) {
  return <Card className="products-state" aria-busy={loading || undefined}>{loading ? <span className="dashboard-spinner" aria-hidden="true" /> : <span className="products-state-mark" aria-hidden="true">□</span>}<h2>{title}</h2><p>{description}</p>{action ? <div>{action}</div> : null}</Card>
}
