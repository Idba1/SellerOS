export const routes = [
  { path: '/', title: 'Dashboard', description: 'Sales and business overview.' },
  { path: '/products', title: 'Products', description: 'Your product catalogue.' },
  { path: '/inventory', title: 'Inventory', description: 'Stock records and movements.' },
  { path: '/customers', title: 'Customers', description: 'Customer records and purchase history.' },
  { path: '/orders', title: 'Orders', description: 'Order records and progress.' },
  { path: '/expenses', title: 'Expenses', description: 'Recorded business expenses.' },
  { path: '/profit', title: 'Profit intelligence', description: 'Estimated profit from recorded costs.' },
  { path: '/assistant', title: 'Customer assistant', description: 'Customer reply drafts for seller review.' },
  { path: '/advisor', title: 'Business advisor', description: 'Insights grounded in business metrics.' },
  { path: '/segments', title: 'Customer segmentation', description: 'Purchase-behavior groups.' },
  { path: '/forecast', title: 'Demand forecasting', description: 'Demand estimates and data limitations.' },
  { path: '/simulator', title: 'What-if simulator', description: 'Scenarios with disclosed assumptions.' },
  { path: '/settings', title: 'Store settings', description: 'Store profile and configuration.' },
] as const

export function resolveRoute(pathname: string) {
  const path = pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname
  return routes.find((route) => route.path === path)
}
