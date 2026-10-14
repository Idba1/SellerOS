import type { ReactNode } from 'react'
import { routes } from './routes'
import { Badge } from '../ui/primitives'

const groups = [
  { label: 'Workspace', paths: ['/', '/products', '/inventory', '/customers', '/orders', '/expenses'] },
  { label: 'Intelligence', paths: ['/profit', '/assistant', '/advisor', '/segments', '/forecast', '/simulator'] },
  { label: 'Manage', paths: ['/settings'] },
]
function NavMark({ intelligence }: { intelligence: boolean }) {
  return <svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.6">{intelligence ? <path d="M4 19V13m8 6V5m8 14V9M2 21h20" /> : <><rect x="4" y="4" width="16" height="16" rx="4" /><path d="M4 10h16M10 10v10" /></>}</svg>
}
export function AppLayout({ title, path, children }: { title: string; path?: string; children: ReactNode }) {
  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to main content</a>
    <aside className="sidebar" aria-label="SellerOS workspace">
      <a className="brand" href="/"><span className="brand-mark" aria-hidden="true">S</span><span>SellerOS<span className="brand-caption">Seller workspace</span></span></a>
      <nav aria-label="Main navigation">
        {groups.map(group => <div className="nav-group" key={group.label}>
          <p className="nav-label">{group.label}</p>
          <ul className="nav-list">{routes.filter(route => group.paths.includes(route.path)).map(route => <li key={route.path}>
            <a href={route.path} aria-current={path === route.path ? 'page' : undefined}><NavMark intelligence={group.label === 'Intelligence'} /><span>{route.title}</span></a>
          </li>)}</ul>
        </div>)}
      </nav>
      <div className="sidebar-note"><Badge>Project prototype</Badge><p>Business features are being developed. No live store data is connected.</p></div>
    </aside>
    <div className="app-body">
      <header className="topbar">
        <div><p className="breadcrumb">Workspace <span aria-hidden="true">/</span> {title}</p><p className="topbar-title">{title}</p></div>
        <div className="profile" aria-label="Demo profile placeholder"><span className="avatar" aria-hidden="true">S</span><div><strong>Seller profile</strong><span>Demo workspace</span></div></div>
      </header>
      <main id="main-content" tabIndex={-1}>{children}</main>
      <footer className="app-footer">SellerOS <span aria-hidden="true">·</span> Social-commerce decision support</footer>
    </div>
  </div>
}
