import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { ApiClientError } from '../api/client'
import { getApiClient } from '../api/config'
import { getAuthSession } from '../auth/session'
import { Badge, Card } from '../ui/primitives'
import { decodeMovement, decodeMovementPage, decodeStockUnit, decodeStockUnitPage, type InventoryMovement, type StockUnit } from './api'

const PAGE_SIZE = 20
const shortDate = new Intl.DateTimeFormat('en-BD', { dateStyle: 'medium', timeStyle: 'short' })

function errorMessage(error: unknown, task: 'inventory' | 'movements' | 'adjustment') {
  if (error instanceof ApiClientError && error.isAuthError) return 'Your session is no longer authorized. Sign in again to continue.'
  if (error instanceof ApiClientError && error.status === 404) return 'Finish store setup before accessing inventory records.'
  if (error instanceof ApiClientError && error.kind === 'network') return 'SellerOS could not reach the service. Check your connection and try again.'
  if (error instanceof Error && error.message.includes('VITE_API_BASE_URL')) return 'Inventory data is unavailable until the frontend API URL is configured.'
  return task === 'adjustment' ? 'SellerOS could not record this adjustment. Review the quantity and reason, then try again.' : `SellerOS could not load inventory ${task}. Please try again.`
}
function stockLabel(unit: StockUnit) { return unit.is_low_stock ? 'Low stock' : unit.low_stock_threshold === null ? 'No threshold' : 'In stock' }
function displayVariant(unit: StockUnit) { return unit.variant_name || '—' }

export function Inventory() {
  const hasSession = Boolean(getAuthSession())
  const [page, setPage] = useState(1)
  const [units, setUnits] = useState<StockUnit[]>([])
  const [total, setTotal] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<StockUnit | null>(null)
  const [movements, setMovements] = useState<InventoryMovement[]>([])
  const [movementLoading, setMovementLoading] = useState(false)
  const [movementError, setMovementError] = useState<string | null>(null)
  const [showAdjustment, setShowAdjustment] = useState(false)
  const [showOpening, setShowOpening] = useState(false)
  const [showSettings, setShowSettings] = useState(false)

  async function loadInventory(nextPage: number) {
    if (!hasSession) return
    setLoading(true); setError(null); setSelected(null); setMovements([]); setMovementError(null)
    try {
      const response = await getApiClient().request('inventory/', { query: { page: nextPage, page_size: PAGE_SIZE }, decode: decodeStockUnitPage })
      setUnits(response?.results ?? []); setTotal(response?.count ?? 0)
    } catch (requestError) {
      setUnits([]); setTotal(null); setError(errorMessage(requestError, 'inventory'))
    } finally { setLoading(false) }
  }
  useEffect(() => { void loadInventory(1) }, [])

  async function inspectUnit(unit: StockUnit) {
    setSelected(unit); setShowAdjustment(false); setShowOpening(false); setShowSettings(false); setMovementLoading(true); setMovementError(null); setMovements([])
    try {
      const response = await getApiClient().request(`inventory/${unit.id}/movements/`, { query: { page: 1, page_size: PAGE_SIZE }, decode: decodeMovementPage })
      setMovements(response?.results ?? [])
    } catch (requestError) { setMovementError(errorMessage(requestError, 'movements')) }
    finally { setMovementLoading(false) }
  }
  function changePage(nextPage: number) { setPage(nextPage); void loadInventory(nextPage) }

  return <>
    <div className="inventory-hero"><div><p className="eyebrow">OPERATIONS</p><h1>Inventory</h1><p className="page-description">Review current stock balances and record authorised manual adjustments.</p></div><Badge tone="accent">Live inventory</Badge></div>
    {!hasSession ? <InventoryState title="Sign in to view inventory" description="Stock balances and movement history are available only to an authenticated SellerOS account." action={<a className="button" href="/login">Go to sign in</a>} /> : <>
      {loading ? <InventoryState title="Loading inventory" description="Retrieving authorized stock balances." loading /> : null}
      {error ? <InventoryState title="Unable to load inventory" description={error} action={<button className="button" onClick={() => void loadInventory(page)}>Retry</button>} /> : null}
      {!loading && !error && total === 0 ? <InventoryState title="No stock units yet" description="Inventory will appear after stock-unit records exist for this store." /> : null}
      {!loading && !error && total !== null && total > 0 ? <section className="inventory-layout"><Card className="inventory-table-card"><div className="section-heading"><div><p className="eyebrow">STOCK BALANCES</p><h2>{total} {total === 1 ? 'stock unit' : 'stock units'}</h2><p>Page {page} of {Math.ceil(total / PAGE_SIZE)}. Low-stock counts are not inferred across pages.</p></div><Badge>{units.filter(unit => unit.is_low_stock).length} low on this page</Badge></div><div className="table-wrap" tabIndex={0}><table className="inventory-table"><caption className="sr-only">Current authorized inventory stock balances</caption><thead><tr><th scope="col">Product</th><th scope="col">Variant</th><th scope="col">On hand</th><th scope="col">Threshold</th><th scope="col">Status</th><th scope="col">Updated</th><th scope="col"><span className="sr-only">Actions</span></th></tr></thead><tbody>{units.map(unit => <tr key={unit.id}><th scope="row"><span className="product-name">{unit.product_name}</span><small>{unit.id}</small></th><td>{displayVariant(unit)}</td><td><strong>{unit.quantity_on_hand}</strong> units</td><td>{unit.low_stock_threshold === null ? 'Not configured' : `${unit.low_stock_threshold} units`}</td><td><span className={`inventory-status ${unit.is_low_stock ? 'inventory-status-low' : 'inventory-status-normal'}`}>{stockLabel(unit)}</span></td><td>{shortDate.format(new Date(unit.updated_at))}</td><td><button className="table-action" onClick={() => void inspectUnit(unit)}>Review</button></td></tr>)}</tbody></table></div><div className="products-pagination"><span>Page {page}</span><div><button className="button button-secondary" disabled={loading || page === 1} onClick={() => changePage(page - 1)}>Previous</button><button className="button button-secondary" disabled={loading || units.length < PAGE_SIZE} onClick={() => changePage(page + 1)}>Next</button></div></div></Card><InventoryPanel unit={selected} movements={movements} loading={movementLoading} error={movementError} showAdjustment={showAdjustment} showOpening={showOpening} showSettings={showSettings} onAdjust={() => { setShowAdjustment(true); setShowOpening(false); setShowSettings(false) }} onOpen={() => { setShowOpening(true); setShowAdjustment(false); setShowSettings(false) }} onConfigure={() => { setShowSettings(true); setShowAdjustment(false); setShowOpening(false) }} onCloseForms={() => { setShowAdjustment(false); setShowOpening(false); setShowSettings(false) }} onUpdated={() => { setShowAdjustment(false); setShowOpening(false); setShowSettings(false); void loadInventory(page) }} /></section> : null}
      <Card className="inventory-contract-note"><p className="eyebrow">INVENTORY SCOPE</p><p>Quantities are recorded balances. This page does not create opening balances, change low-stock thresholds, edit product records, or update quantity directly. Manual changes always require a signed quantity and a reason.</p><a className="text-link" href="/products">Open products <span aria-hidden="true">→</span></a></Card>
    </>}
  </>
}

function InventoryPanel({ unit, movements, loading, error, showAdjustment, showOpening, showSettings, onAdjust, onOpen, onConfigure, onCloseForms, onUpdated }: { unit: StockUnit | null; movements: InventoryMovement[]; loading: boolean; error: string | null; showAdjustment: boolean; showOpening: boolean; showSettings: boolean; onAdjust: () => void; onOpen: () => void; onConfigure: () => void; onCloseForms: () => void; onUpdated: () => void }) {
  if (loading) return <aside className="inventory-panel"><Card className="product-detail-state"><span className="dashboard-spinner" aria-hidden="true" /><h2>Loading movement history</h2></Card></aside>
  if (!unit) return <aside className="inventory-panel"><Card className="product-detail-state"><p className="eyebrow">STOCK DETAILS</p><h2>Select a stock unit</h2><p>Choose Review to inspect the authorized movement history.</p></Card></aside>
  return <aside className="inventory-panel"><Card><div className="section-heading"><div><p className="eyebrow">STOCK DETAILS</p><h2>{unit.product_name}</h2><p>{displayVariant(unit)}</p></div><div><button className="table-action" onClick={onConfigure}>Threshold</button><button className="table-action" onClick={onAdjust}>Adjust</button></div></div><dl className="inventory-facts"><div><dt>Quantity on hand</dt><dd>{unit.quantity_on_hand} units</dd></div><div><dt>Low-stock threshold</dt><dd>{unit.low_stock_threshold === null ? 'Not configured' : `${unit.low_stock_threshold} units`}</dd></div></dl>{unit.quantity_on_hand === 0 && movements.length === 0 && !showAdjustment && !showSettings ? <button className="button button-secondary" onClick={onOpen}>Record opening balance</button> : null}{showAdjustment ? <AdjustmentForm unit={unit} onCancel={onCloseForms} onAdjusted={onUpdated} /> : null}{showOpening ? <OpeningBalanceForm unit={unit} onCancel={onCloseForms} onUpdated={onUpdated} /> : null}{showSettings ? <ThresholdForm unit={unit} onCancel={onCloseForms} onUpdated={onUpdated} /> : null}<div className="inventory-history"><h3>Movement history</h3>{error ? <p className="inventory-panel-error" role="alert">{error}</p> : movements.length === 0 ? <p>No movement rows are returned for this stock unit.</p> : <ul>{movements.map(movement => <li key={movement.id}><div><strong>{movement.movement_type.replaceAll('_', ' ')}</strong><span>{movement.reason || 'No reason recorded'}</span></div><div className={movement.quantity_delta > 0 ? 'inventory-positive' : 'inventory-negative'}>{movement.quantity_delta > 0 ? '+' : ''}{movement.quantity_delta}</div></li>)}</ul>}</div></Card></aside>
}

function OpeningBalanceForm({ unit, onCancel, onUpdated }: { unit: StockUnit; onCancel: () => void; onUpdated: () => void }) { const [quantity, setQuantity] = useState(''); const [error, setError] = useState<string | null>(null); const [saving, setSaving] = useState(false); async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setSaving(true); setError(null); try { await getApiClient().request(`inventory/${unit.id}/opening-balance/`, { method: 'POST', body: { quantity: Number(quantity) }, decode: decodeMovement }); onUpdated() } catch (requestError) { setError(errorMessage(requestError, 'adjustment')) } finally { setSaving(false) } } return <form className="inventory-adjustment" onSubmit={submit}><h3>Record opening balance</h3><p>This is allowed once, before any stock activity.</p>{error ? <p role="alert" className="product-form-error">{error}</p> : null}<label>Opening quantity<input className="input" type="number" min="1" step="1" value={quantity} onChange={event => setQuantity(event.target.value)} required /></label><div><button className="button button-secondary" type="button" onClick={onCancel}>Cancel</button><button className="button" type="submit" disabled={saving}>{saving ? 'Recording…' : 'Record opening balance'}</button></div></form> }

function ThresholdForm({ unit, onCancel, onUpdated }: { unit: StockUnit; onCancel: () => void; onUpdated: () => void }) { const [threshold, setThreshold] = useState(unit.low_stock_threshold === null ? '' : String(unit.low_stock_threshold)); const [error, setError] = useState<string | null>(null); const [saving, setSaving] = useState(false); async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setSaving(true); setError(null); try { await getApiClient().request(`inventory/${unit.id}/`, { method: 'PATCH', body: { low_stock_threshold: threshold === '' ? null : Number(threshold) }, decode: decodeStockUnit }); onUpdated() } catch (requestError) { setError(errorMessage(requestError, 'adjustment')) } finally { setSaving(false) } } return <form className="inventory-adjustment" onSubmit={submit}><h3>Low-stock threshold</h3><p>Set zero or a positive value; leave blank to remove the alert threshold.</p>{error ? <p role="alert" className="product-form-error">{error}</p> : null}<label>Threshold<input className="input" type="number" min="0" step="1" value={threshold} onChange={event => setThreshold(event.target.value)} /></label><div><button className="button button-secondary" type="button" onClick={onCancel}>Cancel</button><button className="button" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save threshold'}</button></div></form> }

function AdjustmentForm({ unit, onCancel, onAdjusted }: { unit: StockUnit; onCancel: () => void; onAdjusted: () => void }) {
  const [quantity, setQuantity] = useState(''); const [reason, setReason] = useState(''); const [error, setError] = useState<string | null>(null); const [submitting, setSubmitting] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSubmitting(true); setError(null)
    try { await getApiClient().request(`inventory/${unit.id}/adjustments/`, { method: 'POST', body: { quantity_delta: Number(quantity), reason }, decode: decodeMovement }); onAdjusted() }
    catch (requestError) { setError(errorMessage(requestError, 'adjustment')) }
    finally { setSubmitting(false) }
  }
  return <form className="inventory-adjustment" onSubmit={submit}><h3>Record manual adjustment</h3><p>Use a positive number to add stock or a negative number to remove stock.</p>{error ? <p role="alert" className="product-form-error">{error}</p> : null}<label>Quantity change<input className="input" type="number" step="1" value={quantity} onChange={event => setQuantity(event.target.value)} required /></label><label>Reason<textarea className="input" value={reason} onChange={event => setReason(event.target.value)} maxLength={240} required /></label><div><button className="button button-secondary" type="button" onClick={onCancel} disabled={submitting}>Cancel</button><button className="button" type="submit" disabled={submitting}>{submitting ? 'Recording…' : 'Record adjustment'}</button></div></form>
}

function InventoryState({ title, description, action, loading = false }: { title: string; description: string; action?: ReactNode; loading?: boolean }) {
  return <Card className="products-state" aria-busy={loading || undefined}>{loading ? <span className="dashboard-spinner" aria-hidden="true" /> : <span className="products-state-mark" aria-hidden="true">□</span>}<h2>{title}</h2><p>{description}</p>{action ? <div>{action}</div> : null}</Card>
}
