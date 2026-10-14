/** Synthetic presentation fixtures only. Never imported by the API transport. */
export const demoOrders = [
  { id: 'DEMO-104', date: '2026-10-14', item: 'Canvas tote', amount: 120, status: 'Confirmed' },
  { id: 'DEMO-103', date: '2026-10-13', item: 'Desk organizer', amount: 240, status: 'Delivered' },
  { id: 'DEMO-102', date: '2026-10-11', item: 'Canvas tote', amount: 180, status: 'Delivered' },
  { id: 'DEMO-101', date: '2026-10-08', item: 'Notebook set', amount: 300, status: 'Delivered' },
] as const
export const demoInventory = [
  { name: 'Canvas tote', stock: 3, threshold: 5 },
  { name: 'Desk organizer', stock: 2, threshold: 4 },
  { name: 'Notebook set', stock: 18, threshold: 5 },
] as const
export const demoDates = ['2026-10-08', '2026-10-09', '2026-10-10', '2026-10-11', '2026-10-12', '2026-10-13', '2026-10-14']
export function demoOverview(days: 3 | 7) {
  const dates = demoDates.slice(-days)
  const orders = demoOrders.filter(order => dates.includes(order.date))
  const delivered = orders.filter(order => order.status === 'Delivered')
  const revenue = delivered.reduce((sum, order) => sum + order.amount, 0)
  return {
    orders, revenue, average: delivered.length ? revenue / delivered.length : 0,
    attention: demoInventory.filter(product => product.stock <= product.threshold),
    series: dates.map(date => ({ date, amount: delivered.filter(order => order.date === date).reduce((sum, order) => sum + order.amount, 0) })),
  }
}
