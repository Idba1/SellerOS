import { useEffect, useState, type ReactNode } from 'react'
import { routes } from './routes'
import { getAuthSession } from '../auth/session'
import { getCurrentStore, isMissingStore } from '../stores/api'
import { Badge } from '../ui/primitives'

const groups = [
  { label: 'Workspace', paths: ['/', '/products', '/inventory', '/customers', '/orders', '/expenses'] },
  { label: 'Intelligence', paths: ['/analytics', '/profit', '/assistant', '/advisor', '/segments', '/forecast', '/simulator'] },
  { label: 'Manage', paths: ['/settings'] },
]
function NavMark({ intelligence }: { intelligence: boolean }) {
  return <svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.6">{intelligence ? <path d="M4 19V13m8 6V5m8 14V9M2 21h20" /> : <><rect x="4" y="4" width="16" height="16" rx="4" /><path d="M4 10h16M10 10v10" /></>}</svg>
}

type ProfileSummary = {
  name: string
  workspace: string
}

function accountDisplayName(email: string): string {
  return email.split('@')[0] || email
}

function useProfileSummary(): ProfileSummary {
  const session = getAuthSession()
  const [workspace, setWorkspace] = useState(() => session ? 'Loading workspace…' : 'Sign in required')

  useEffect(() => {
    if (!session) return

    let active = true
    getCurrentStore()
      .then(store => {
        if (active) setWorkspace(store?.name || 'Store setup required')
      })
      .catch(error => {
        if (!active) return
        setWorkspace(isMissingStore(error) ? 'Store setup required' : 'Workspace unavailable')
      })

    return () => { active = false }
  }, [session?.account.id])

  return {
    name: session ? accountDisplayName(session.account.email) : 'Guest seller',
    workspace,
  }
}

export function AppLayout({ title, path, children }: { title: string; path?: string; children: ReactNode }) {
  const profile = useProfileSummary()
  const avatarInitial = (profile.workspace === 'Loading workspace…' || profile.workspace === 'Store setup required' || profile.workspace === 'Workspace unavailable'
    ? profile.name
    : profile.workspace).trim().charAt(0).toUpperCase() || 'S'

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
        <div className="profile" aria-label="Seller account and workspace"><span className="avatar" aria-hidden="true">{avatarInitial}</span><div><strong>{profile.name}</strong><span>{profile.workspace}</span></div></div>
      </header>
      <main id="main-content" tabIndex={-1}>{children}</main>
      <footer className="app-footer">SellerOS <span aria-hidden="true">·</span> Social-commerce decision support</footer>
    </div>
  </div>
}
