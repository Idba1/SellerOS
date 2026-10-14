import { useEffect } from 'react'
import { resolveRoute } from './routes'
import { AppLayout } from './AppLayout'
import { Badge, Card } from '../ui/primitives'
import { Dashboard } from '../dashboard/Dashboard'

export function App() {
  const route = resolveRoute(window.location.pathname)
  const title = route?.title ?? 'Page not found'
  useEffect(() => { document.title = `${title} | SellerOS` }, [title])
  if (route?.path === '/') return <AppLayout title={title} path={route.path}><Dashboard /></AppLayout>
  return <AppLayout title={title} path={route?.path}>
    <div className="page-heading"><div><p className="eyebrow">YOUR BUSINESS WORKSPACE</p><h1>{title}</h1><p className="page-description">{route?.description ?? 'This address does not match a SellerOS page.'}</p></div><Badge tone="accent">{route ? 'Preview' : 'Not found'}</Badge></div>
    {route ? <>
      <Card className="feature-placeholder" aria-labelledby="placeholder-title">
        <div className="placeholder-mark" aria-hidden="true"><svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="4" width="18" height="16" rx="3" /><path d="M3 9h18M8 13h8M8 16h5" /></svg></div>
        <Badge>Planned feature</Badge><h2 id="placeholder-title">Your {title.toLowerCase()} workspace is taking shape</h2><p>This page is a navigation placeholder. Business records and actions will be available in a later development task.</p>
        <div className="placeholder-footnote">No live data or generated results are displayed.</div>
      </Card>
      <div className="support-grid">
        <Card aria-labelledby="records-title"><p className="eyebrow">ORGANIZE</p><h2 id="records-title">Keep your records connected</h2><p>Explore the planned product, customer and order workspaces.</p><a className="text-link" href="/products">Explore products <span aria-hidden="true">→</span></a></Card>
        <Card aria-labelledby="insights-title"><p className="eyebrow">UNDERSTAND</p><h2 id="insights-title">Make room for better insights</h2><p>Business intelligence will use recorded data and disclosed assumptions.</p><a className="text-link" href="/profit">Explore profit intelligence <span aria-hidden="true">→</span></a></Card>
      </div>
    </> : <Card className="feature-placeholder"><h2>We could not find that page</h2><p>Use the sidebar to choose a workspace, or return to the dashboard.</p><a className="button" href="/">Return to dashboard</a></Card>}
  </AppLayout>
}
