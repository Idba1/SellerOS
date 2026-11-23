import { useEffect, useRef } from 'react'

type ConfirmationDialogProps = {
  open: boolean
  title: string
  description: string
  confirmLabel: string
  onConfirm: () => void
  onCancel: () => void
  busy?: boolean
}

export function ConfirmationDialog({ open, title, description, confirmLabel, onConfirm, onCancel, busy = false }: ConfirmationDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const cancelRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open && !dialog.open) {
      dialog.showModal()
      cancelRef.current?.focus()
    }
    if (!open && dialog.open) dialog.close()
  }, [open])

  return <dialog ref={dialogRef} className="confirmation-dialog" aria-labelledby="confirmation-title" aria-describedby="confirmation-description" onCancel={event => { event.preventDefault(); if (!busy) onCancel() }}>
    <div className="confirmation-dialog-content">
      <h2 id="confirmation-title">{title}</h2>
      <p id="confirmation-description">{description}</p>
      <div className="dialog-actions">
        <button ref={cancelRef} className="button button-secondary" type="button" onClick={onCancel} disabled={busy}>Cancel</button>
        <button className="button" type="button" onClick={onConfirm} disabled={busy}>{busy ? 'Working…' : confirmLabel}</button>
      </div>
    </div>
  </dialog>
}
