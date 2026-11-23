import { StrictMode, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { ConfirmationDialog } from '../src/components/ConfirmationDialog'
import { SelectField, TextField } from '../src/components/FormFields'
import { EmptyState, ErrorState, LoadingState } from '../src/components/StatusStates'
import '../src/styles/index.css'

function Fixture() {
  const [name, setName] = useState('')
  const [error, setError] = useState<string | undefined>()
  const [open, setOpen] = useState(false)
  const [result, setResult] = useState('')
  const [retryCount, setRetryCount] = useState(0)
  const validate = () => setError(name.trim() ? undefined : 'Enter a product name.')

  return <main className="component-test-fixture">
    <h1>Form primitive fixture</h1>
    <TextField id="product-name" label="Product name" required helpText="Use a clear seller-facing name." error={error} value={name} onChange={event => setName(event.target.value)} />
    <SelectField id="category" label="Category" helpText="Fixture choices only."><option>Accessories</option><option>Stationery</option></SelectField>
    <button className="button" type="button" onClick={validate}>Validate field</button>
    <button className="button button-secondary" type="button" onClick={() => setOpen(true)}>Open confirmation</button>
    <p data-testid="confirmation-result" aria-live="polite">{result}</p>
    <ConfirmationDialog open={open} title="Confirm fixture action" description="This test action does not persist data." confirmLabel="Confirm action" onCancel={() => { setOpen(false); setResult('Cancelled') }} onConfirm={() => { setOpen(false); setResult('Confirmed') }} />
    <LoadingState title="Loading fixture">No network request is made.</LoadingState>
    <EmptyState title="No fixture records">This demonstrates an empty state.</EmptyState>
    <ErrorState title="Fixture error" action={<button className="button button-secondary" type="button" onClick={() => setRetryCount(count => count + 1)}>Retry fixture</button>}>This demonstrates safe error feedback.</ErrorState>
    <p data-testid="retry-count">Retries: {retryCount}</p>
  </main>
}

const root = document.getElementById('root')
if (!root) throw new Error('Test fixture root is missing')
createRoot(root).render(<StrictMode><Fixture /></StrictMode>)
