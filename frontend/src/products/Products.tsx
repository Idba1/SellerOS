import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { ApiClientError } from '../api/client'
import { getApiClient } from '../api/config'
import { getAuthSession } from '../auth/session'
import { Badge, Card } from '../ui/primitives'
import { decodeProduct, decodeProductDetail, decodeProductPage, type Product, type ProductDetail, type ProductPayload } from './api'

const money = new Intl.NumberFormat('en-BD', { style: 'currency', currency: 'BDT', minimumFractionDigits: 2, maximumFractionDigits: 2 })
const PAGE_SIZE = 20
type Filters = { page: number; category: string; isActive: 'all' | 'true' | 'false'; ordering: 'name' | '-name' | 'created_at' | '-created_at' }
const initialFilters: Filters = { page: 1, category: '', isActive: 'all', ordering: 'name' }

function errorMessage(error: unknown, resource: 'products' | 'details' | 'create') {
  if (error instanceof ApiClientError && error.isAuthError) return 'Your session is no longer authorized. Sign in again to continue.'
  if (error instanceof ApiClientError && error.status === 404) return 'Finish store setup before accessing product records.'
  if (error instanceof ApiClientError && error.kind === 'network') return 'SellerOS could not reach the service. Check your connection and try again.'
  if (error instanceof Error && error.message.includes('VITE_API_BASE_URL')) return 'Product data is unavailable until the frontend API URL is configured.'
  return resource === 'create' ? 'SellerOS could not create this product. Review the fields and try again.' : `SellerOS could not load product ${resource}. Please try again.`
}
function displayCategory(category: string | null) { return category || 'Uncategorized' }

export function Products({ inventory = false }: { inventory?: boolean }) {
  const hasSession = Boolean(getAuthSession())
  const [filters, setFilters] = useState<Filters>(initialFilters)
  const [categoryDraft, setCategoryDraft] = useState('')
  const [products, setProducts] = useState<Product[]>([])
  const [total, setTotal] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<ProductDetail | null>(null)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [detailsError, setDetailsError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  async function loadProducts(nextFilters: Filters) {
    if (!hasSession) return
    setLoading(true); setError(null); setSelected(null); setDetailsError(null)
    try {
      const response = await getApiClient().request('products/', {
        query: { page: nextFilters.page, page_size: PAGE_SIZE, category: nextFilters.category || undefined, is_active: nextFilters.isActive === 'all' ? undefined : nextFilters.isActive, ordering: nextFilters.ordering },
        decode: decodeProductPage,
      })
      setProducts(response?.results ?? []); setTotal(response?.count ?? 0)
    } catch (requestError) {
      setProducts([]); setTotal(null); setError(errorMessage(requestError, 'products'))
    } finally { setLoading(false) }
  }

  useEffect(() => { void loadProducts(initialFilters) }, [])

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const next = { ...filters, page: 1, category: categoryDraft.trim() }
    setFilters(next); void loadProducts(next)
  }
  function resetFilters() { setCategoryDraft(''); setFilters(initialFilters); void loadProducts(initialFilters) }
  async function openProduct(productId: string) {
    setDetailsLoading(true); setDetailsError(null); setSelected(null)
    try { setSelected(await getApiClient().request(`products/${productId}/`, { decode: decodeProductDetail }) ?? null) }
    catch (requestError) { setDetailsError(errorMessage(requestError, 'details')) }
    finally { setDetailsLoading(false) }
  }
  function changePage(page: number) { const next = { ...filters, page }; setFilters(next); void loadProducts(next) }

  if (inventory) return <InventoryBoundary />
  return <>
    <div className="products-hero"><div><p className="eyebrow">CATALOGUE</p><h1>Products</h1><p className="page-description">Review and maintain the products in your authorized store catalogue.</p></div><div className="products-hero-actions"><Badge tone="accent">Live catalogue</Badge>{hasSession ? <button className="button" onClick={() => setShowCreate(true)}>Add product</button> : null}</div></div>
    {!hasSession ? <ProductsState title="Sign in to view products" description="Product records are available only to an authenticated SellerOS account." action={<a className="button" href="/login">Go to sign in</a>} /> : <>
      <form className="card product-controls" onSubmit={applyFilters}><label>Category<input className="input" type="search" value={categoryDraft} onChange={event => setCategoryDraft(event.target.value)} placeholder="Exact category name" /></label><label>Product status<select className="input" value={filters.isActive} onChange={event => setFilters(current => ({ ...current, isActive: event.target.value as Filters['isActive'] }))}><option value="all">All products</option><option value="true">Active</option><option value="false">Inactive</option></select></label><label>Sort by<select className="input" value={filters.ordering} onChange={event => setFilters(current => ({ ...current, ordering: event.target.value as Filters['ordering'] }))}><option value="name">Name: A–Z</option><option value="-name">Name: Z–A</option><option value="-created_at">Newest created</option><option value="created_at">Oldest created</option></select></label><button className="button" type="submit" disabled={loading}>{loading ? 'Loading…' : 'Apply filters'}</button><button className="button button-secondary" type="button" onClick={resetFilters} disabled={loading}>Reset</button></form>
      {showCreate ? <CreateProduct onCancel={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); void loadProducts(filters) }} /> : null}
      {loading ? <ProductsState title="Loading products" description="Retrieving authorized catalogue records." loading /> : null}
      {error ? <ProductsState title="Unable to load products" description={error} action={<button className="button" onClick={() => void loadProducts(filters)}>Retry</button>} /> : null}
      {!loading && !error && total === 0 ? <ProductsState title="Your catalogue is empty" description="Create your first product to start maintaining product records." action={<button className="button" onClick={() => setShowCreate(true)}>Add product</button>} /> : null}
      {!loading && !error && total !== null && total > 0 ? <section className="products-layout"><Card className="products-table-card"><div className="section-heading"><div><p className="eyebrow">CATALOGUE RECORDS</p><h2>{total} {total === 1 ? 'product' : 'products'}</h2><p>Showing page {filters.page} of {Math.ceil(total / PAGE_SIZE)}.</p></div><Badge>{filters.isActive === 'all' ? 'All statuses' : filters.isActive === 'true' ? 'Active only' : 'Inactive only'}</Badge></div><div className="table-wrap" tabIndex={0}><table className="products-table"><caption className="sr-only">Products in the authorized SellerOS catalogue</caption><thead><tr><th scope="col">Product</th><th scope="col">Category</th><th scope="col">Selling price</th><th scope="col">Variants</th><th scope="col">Status</th><th scope="col"><span className="sr-only">Actions</span></th></tr></thead><tbody>{products.map(product => <tr key={product.id}><th scope="row"><span className="product-name">{product.name}</span><small>{product.id}</small></th><td>{displayCategory(product.category)}</td><td>{money.format(Number(product.selling_price))}</td><td>{product.has_variants ? 'Variant-based' : 'Standalone'}</td><td><span className={`product-status ${product.is_active ? 'product-status-active' : 'product-status-inactive'}`}>{product.is_active ? 'Active' : 'Inactive'}</span></td><td><button className="table-action" onClick={() => void openProduct(product.id)}>View</button></td></tr>)}</tbody></table></div><div className="products-pagination"><span>Page {filters.page}</span><div><button className="button button-secondary" disabled={loading || filters.page === 1} onClick={() => changePage(filters.page - 1)}>Previous</button><button className="button button-secondary" disabled={loading || products.length < PAGE_SIZE} onClick={() => changePage(filters.page + 1)}>Next</button></div></div></Card><ProductDetails product={selected} loading={detailsLoading} error={detailsError} /></section> : null}
      <Card className="product-contract-note"><p className="eyebrow">CATALOGUE SCOPE</p><p>Category filtering is an exact match as defined by the API. Product stock and low-stock state are not included in product records; use the inventory workspace for approved stock data.</p><a className="text-link" href="/inventory">Open inventory <span aria-hidden="true">→</span></a></Card>
    </>}
  </>
}

function CreateProduct({ onCancel, onCreated }: { onCancel: () => void; onCreated: () => void }) {
  const [name, setName] = useState(''); const [category, setCategory] = useState(''); const [price, setPrice] = useState(''); const [cost, setCost] = useState('')
  const [hasVariants, setHasVariants] = useState(false); const [isActive, setIsActive] = useState(true); const [error, setError] = useState<string | null>(null); const [submitting, setSubmitting] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSubmitting(true); setError(null)
    const body: ProductPayload = { name: name.trim(), category: category.trim() || null, selling_price: price, unit_cost: cost.trim() || null, has_variants: hasVariants, is_active: isActive }
    try { await getApiClient().request('products/', { method: 'POST', body, decode: decodeProduct }); onCreated() }
    catch (requestError) { setError(errorMessage(requestError, 'create')) }
    finally { setSubmitting(false) }
  }
  return <Card className="product-create" aria-labelledby="create-product-title"><div className="section-heading"><div><p className="eyebrow">NEW CATALOGUE RECORD</p><h2 id="create-product-title">Add product</h2><p>Only fields supported by the product API are included.</p></div><button className="table-action" onClick={onCancel}>Close</button></div>{error ? <p className="product-form-error" role="alert">{error}</p> : null}<form className="product-create-form" onSubmit={submit}><label>Product name<input className="input" value={name} onChange={event => setName(event.target.value)} required maxLength={160} /></label><label>Category <span>(optional)</span><input className="input" value={category} onChange={event => setCategory(event.target.value)} maxLength={80} /></label><label>Selling price (BDT)<input className="input" type="number" inputMode="decimal" min="0.01" step="0.01" value={price} onChange={event => setPrice(event.target.value)} required /></label><label>Unit cost (BDT) <span>(optional)</span><input className="input" type="number" inputMode="decimal" min="0" step="0.01" value={cost} onChange={event => setCost(event.target.value)} /></label><label className="product-check"><input type="checkbox" checked={hasVariants} onChange={event => setHasVariants(event.target.checked)} />This product has variants</label><label className="product-check"><input type="checkbox" checked={isActive} onChange={event => setIsActive(event.target.checked)} />Active in catalogue</label><div className="product-create-actions"><button className="button button-secondary" type="button" onClick={onCancel} disabled={submitting}>Cancel</button><button className="button" type="submit" disabled={submitting}>{submitting ? 'Creating…' : 'Create product'}</button></div></form></Card>
}

function ProductDetails({ product, loading, error }: { product: ProductDetail | null; loading: boolean; error: string | null }) {
  return <aside className="product-detail-panel" aria-live="polite">{loading ? <Card className="product-detail-state"><span className="dashboard-spinner" aria-hidden="true" /><h2>Loading product details</h2></Card> : error ? <Card className="product-detail-state"><h2>Details unavailable</h2><p>{error}</p></Card> : product ? <Card><p className="eyebrow">PRODUCT DETAILS</p><h2>{product.name}</h2><dl className="product-facts"><div><dt>Category</dt><dd>{displayCategory(product.category)}</dd></div><div><dt>Selling price</dt><dd>{money.format(Number(product.selling_price))}</dd></div><div><dt>Unit cost</dt><dd>{product.unit_cost === null ? 'Not recorded' : money.format(Number(product.unit_cost))}</dd></div><div><dt>Configuration</dt><dd>{product.has_variants ? 'Variant-based' : 'Standalone product'}</dd></div></dl><div className="product-variants"><h3>Variants</h3>{product.variants.length === 0 ? <p>No variant records are returned for this product.</p> : <ul>{product.variants.map(variant => <li key={variant.id}><span>{variant.name}</span><span className={`product-status ${variant.is_active ? 'product-status-active' : 'product-status-inactive'}`}>{variant.is_active ? 'Active' : 'Inactive'}</span></li>)}</ul>}</div><p className="product-detail-footnote">Editing and variant maintenance are not exposed by this screen yet.</p></Card> : <Card className="product-detail-state"><p className="eyebrow">PRODUCT DETAILS</p><h2>Select a product</h2><p>Choose View to inspect the record and its returned variants.</p></Card>}</aside>
}

function ProductsState({ title, description, action, loading = false }: { title: string; description: string; action?: ReactNode; loading?: boolean }) {
  return <Card className="products-state" aria-busy={loading || undefined}>{loading ? <span className="dashboard-spinner" aria-hidden="true" /> : <span className="products-state-mark" aria-hidden="true">□</span>}<h2>{title}</h2><p>{description}</p>{action ? <div>{action}</div> : null}</Card>
}

function InventoryBoundary() {
  return <><div className="products-hero"><div><p className="eyebrow">OPERATIONS</p><h1>Inventory</h1><p className="page-description">Stock balances and movements are intentionally kept separate from catalogue records.</p></div><Badge tone="accent">Inventory API</Badge></div><Card className="products-state"><span className="products-state-mark" aria-hidden="true">□</span><h2>Inventory screen is next</h2><p>The product page does not infer stock values. Inventory will use its own authorized endpoint and movement history.</p><a className="button" href="/products">Open products</a></Card></>
}
