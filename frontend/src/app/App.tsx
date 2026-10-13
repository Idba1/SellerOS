import { useEffect } from 'react'
import { routes, resolveRoute } from './routes'

export function App() {
  const route = resolveRoute(window.location.pathname)
  const title = route?.title ?? 'Page not found'
  useEffect(() => { document.title = `${title} | SellerOS` }, [title])

  return (
    <div className="workspace">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className="site-header">
        <a className="brand" href="/">SellerOS</a>
        <p>Social-commerce decision support</p>
      </header>
      <div className="workspace-body">
        <nav aria-label="Main navigation">
          <ul className="nav-list">
            {routes.map((item) => (
              <li key={item.path}>
                <a href={item.path} aria-current={item === route ? 'page' : undefined}>
                  {item.title}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <main id="main-content" tabIndex={-1}>
          <p className="eyebrow">Your business workspace</p>
          <h1>{title}</h1>
          {route ? (
            <>
              <p>{route.description}</p>
              <section className="placeholder" aria-labelledby="placeholder-title">
                <h2 id="placeholder-title">Coming in a later development task</h2>
                <p>This page is a navigation placeholder. Business records and actions are not available yet.</p>
              </section>
            </>
          ) : (
            <>
              <p>This address does not match a SellerOS page.</p>
              <a href="/">Return to dashboard</a>
            </>
          )}
        </main>
      </div>
    </div>
  )
}
