/** Isolated presentation records; neither an API schema nor real customer data. */
export const demoOrders = [
  { id: 'DEMO-O104', date: '2026-10-14', customer: 'Demo customer A', product: 'Canvas tote', quantity: 1, amount: 120, status: 'Confirmed' },
  { id: 'DEMO-O103', date: '2026-10-13', customer: 'Demo customer B', product: 'Desk organizer', quantity: 1, amount: 240, status: 'Shipped' },
  { id: 'DEMO-O102', date: '2026-10-12', customer: 'Demo customer C', product: 'Notebook set', quantity: 2, amount: 200, status: 'Processing' },
  { id: 'DEMO-O101', date: '2026-10-08', customer: 'Demo customer D', product: 'Canvas tote', quantity: 1, amount: 120, status: 'Delivered' },
] as const
