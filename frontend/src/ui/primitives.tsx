import type { ComponentProps, ReactNode } from 'react'

export function Card({ children, className = '', ...props }: ComponentProps<'section'>) {
  return <section {...props} className={`card ${className}`}>{children}</section>
}
export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'accent' }) {
  return <span className={`badge badge-${tone}`}>{children}</span>
}
