import { useId, type ComponentProps } from 'react'

type FieldBaseProps = {
  label: string
  helpText?: string
  error?: string
}

function FieldMessages({ helpText, error, helpId, errorId }: Pick<FieldBaseProps, 'helpText' | 'error'> & { helpId: string; errorId: string }) {
  return <>
    {helpText ? <p id={helpId} className="form-field-help">{helpText}</p> : null}
    {error ? <p id={errorId} className="form-field-error" role="alert">{error}</p> : null}
  </>
}

function describedBy(helpText: string | undefined, error: string | undefined, helpId: string, errorId: string) {
  return [helpText ? helpId : '', error ? errorId : ''].filter(Boolean).join(' ') || undefined
}

export function TextField({ label, helpText, error, id, required, className = '', ...props }: FieldBaseProps & ComponentProps<'input'>) {
  const generatedId = useId()
  const fieldId = id ?? `field-${generatedId}`
  const helpId = `${fieldId}-help`
  const errorId = `${fieldId}-error`

  return <div className="form-field">
    <label htmlFor={fieldId}>{label}{required ? <span aria-hidden="true"> *</span> : null}</label>
    <input {...props} id={fieldId} required={required} className={`input ${className}`} aria-invalid={error ? true : undefined} aria-describedby={describedBy(helpText, error, helpId, errorId)} />
    <FieldMessages helpText={helpText} error={error} helpId={helpId} errorId={errorId} />
  </div>
}

export function SelectField({ label, helpText, error, id, required, className = '', children, ...props }: FieldBaseProps & ComponentProps<'select'>) {
  const generatedId = useId()
  const fieldId = id ?? `field-${generatedId}`
  const helpId = `${fieldId}-help`
  const errorId = `${fieldId}-error`

  return <div className="form-field">
    <label htmlFor={fieldId}>{label}{required ? <span aria-hidden="true"> *</span> : null}</label>
    <select {...props} id={fieldId} required={required} className={`input ${className}`} aria-invalid={error ? true : undefined} aria-describedby={describedBy(helpText, error, helpId, errorId)}>{children}</select>
    <FieldMessages helpText={helpText} error={error} helpId={helpId} errorId={errorId} />
  </div>
}
