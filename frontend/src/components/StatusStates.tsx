import type { ReactNode } from 'react'

type StatusStateProps = {
  title: string
  children: ReactNode
  action?: ReactNode
}

export function LoadingState({ title = 'Loading', children = 'Please wait while this information becomes available.' }: Partial<StatusStateProps>) {
  return <section className="status-state status-loading" aria-live="polite" aria-busy="true"><span className="status-spinner" aria-hidden="true" /><div><h2>{title}</h2><p>{children}</p></div></section>
}

export function EmptyState({ title, children, action }: StatusStateProps) {
  return <section className="status-state"><div><h2>{title}</h2><p>{children}</p>{action ? <div className="status-action">{action}</div> : null}</div></section>
}

export function ErrorState({ title = 'Something went wrong', children = 'Try again. If the problem continues, check the request and your connection.', action }: Partial<StatusStateProps>) {
  return <section className="status-state status-error" role="alert"><div><h2>{title}</h2><p>{children}</p>{action ? <div className="status-action">{action}</div> : null}</div></section>
}
