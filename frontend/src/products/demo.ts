/** Presentation-only records; not an API schema or persistent catalogue. */
export const demoProducts = [
  { id: 'DEMO-P01', name: 'Canvas tote', category: 'Accessories', price: 120, stock: 3 },
  { id: 'DEMO-P02', name: 'Desk organizer', category: 'Home & desk', price: 240, stock: 2 },
  { id: 'DEMO-P03', name: 'Notebook set', category: 'Stationery', price: 100, stock: 18 },
  { id: 'DEMO-P04', name: 'Travel pouch', category: 'Accessories', price: 90, stock: 0 },
] as const
