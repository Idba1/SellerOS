import { useEffect } from 'react'
import { resolveRoute } from './routes'
import { AppLayout } from './AppLayout'
import { Card } from '../ui/primitives'
import { Dashboard } from '../dashboard/Dashboard'
import { Products } from '../products/Products'
import { Inventory } from '../inventory/Inventory'
import { Customers } from '../customers/Customers'
import { Expenses } from '../expenses/Expenses'
import { Profit } from '../profit/Profit'
import { Assistant } from '../assistant/Assistant'
import { Advisor } from '../advisor/Advisor'
import { Segments } from '../segments/Segments'
import { Forecast } from '../forecast/Forecast'
import { Simulator } from '../simulator/Simulator'
import { Orders } from '../orders/Orders'
import { Analytics } from '../analytics/Analytics'
import { AuthenticationPage, PasswordRecoveryPage, PasswordResetPage } from '../auth/AuthPage'
import { StoreProfilePage, StoreSetupPage } from '../stores/StorePages'

export function App() {
  const route = resolveRoute(window.location.pathname)
  const title = route?.title ?? 'Page not found'
  useEffect(() => { document.title = `${title} | SellerOS` }, [title])
  if (route?.path === '/login') return <AuthenticationPage />
  if (route?.path === '/forgot-password') return <PasswordRecoveryPage />
  if (route?.path === '/reset-password') return <PasswordResetPage />
  if (route?.path === '/store/setup') return <StoreSetupPage />
  if (route?.path === '/') return <AppLayout title={title} path={route.path}><Dashboard /></AppLayout>
  if (route?.path === '/analytics') return <AppLayout title={title} path={route.path}><Analytics /></AppLayout>
  if (route?.path === '/orders') return <AppLayout title={title} path={route.path}><Orders /></AppLayout>
  if (route?.path === '/products') return <AppLayout title={title} path={route.path}><Products /></AppLayout>
  if (route?.path === '/inventory') return <AppLayout title={title} path={route.path}><Inventory /></AppLayout>
  if (route?.path === '/customers') return <AppLayout title={title} path={route.path}><Customers /></AppLayout>
  if (route?.path === '/expenses') return <AppLayout title={title} path={route.path}><Expenses /></AppLayout>
  if (route?.path === '/profit') return <AppLayout title={title} path={route.path}><Profit /></AppLayout>
  if (route?.path === '/assistant') return <AppLayout title={title} path={route.path}><Assistant /></AppLayout>
  if (route?.path === '/advisor') return <AppLayout title={title} path={route.path}><Advisor /></AppLayout>
  if (route?.path === '/segments') return <AppLayout title={title} path={route.path}><Segments /></AppLayout>
  if (route?.path === '/forecast') return <AppLayout title={title} path={route.path}><Forecast /></AppLayout>
  if (route?.path === '/simulator') return <AppLayout title={title} path={route.path}><Simulator /></AppLayout>
  if (route?.path === '/settings') return <AppLayout title={title} path={route.path}><StoreProfilePage /></AppLayout>
  return <AppLayout title="Page not found" path={undefined}><Card className="feature-placeholder"><h2>We could not find that page</h2><p>Use the sidebar to choose a workspace, or return to the dashboard.</p><a className="button" href="/">Return to dashboard</a></Card></AppLayout>
}
