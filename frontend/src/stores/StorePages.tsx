import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { TextField, SelectField } from '../components/FormFields'
import { ErrorState, LoadingState } from '../components/StatusStates'
import { Badge, Card } from '../ui/primitives'
import { getAuthSession } from '../auth/session'
import { createStore, getCurrentStore, isMissingStore, messageFromStoreError, type StoreProfile } from './api'

type ViewState =
  | { status: 'loading' }
  | { status: 'setup' }
  | { status: 'profile'; store: StoreProfile }
  | { status: 'signed-out' }
  | { status: 'error'; message: string }

const timezoneOptions = [
  { value: 'Asia/Dhaka', label: 'Asia/Dhaka' },
  { value: 'UTC', label: 'UTC' },
  { value: 'America/New_York', label: 'America/New_York' },
]

function useStoreProfile() {
  const [state, setState] = useState<ViewState>({ status: 'loading' })

  async function load() {
    if (!getAuthSession()) {
      setState({ status: 'signed-out' })
      return
    }
    setState({ status: 'loading' })
    try {
      const store = await getCurrentStore()
      setState(store ? { status: 'profile', store } : { status: 'setup' })
    } catch (error) {
      setState(isMissingStore(error) ? { status: 'setup' } : { status: 'error', message: messageFromStoreError(error) })
    }
  }

  useEffect(() => { void load() }, [])
  return { state, setState, reload: load }
}

function SetupLayout({ children }: { children: ReactNode }) {
  return <main className="store-setup-page">
    <section className="store-setup-intro">
      <a className="auth-wordmark" href="/">SellerOS</a>
      <div className="store-setup-copy">
        <p className="eyebrow">SELLEROS / STORE SETUP</p>
        <h1>Let’s make SellerOS yours</h1>
        <p>Set up your store information. You can review these details in Settings after setup.</p>
        <div className="store-setup-note"><strong>Important</strong><span>SellerOS uses BDT for this prototype. Currency conversion is not available.</span></div>
      </div>
    </section>
    <section className="store-setup-form-panel">{children}</section>
  </main>
}

function SignedOutState({ setup }: { setup: boolean }) {
  return <section className={setup ? 'store-setup-card' : ''}>
    <p className="eyebrow">SELLER ACCESS</p>
    <h2>Sign in required</h2>
    <p>You need an authenticated SellerOS account before {setup ? 'setting up a store' : 'viewing a store profile'}.</p>
    <a className="button" href="/login">Go to sign in</a>
  </section>
}

function StoreSetupForm({ onCreated }: { onCreated: (store: StoreProfile) => void }) {
  const [name, setName] = useState('')
  const [timezone, setTimezone] = useState('Asia/Dhaka')
  const [attempted, setAttempted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [requestError, setRequestError] = useState<string | null>(null)
  const nameError = attempted && !name.trim() ? 'Enter your store name.' : undefined

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAttempted(true)
    if (!name.trim()) return
    setLoading(true)
    setRequestError(null)
    try {
      const store = await createStore({ name: name.trim(), timezone })
      if (!store) throw new Error('Store response was empty.')
      onCreated(store)
    } catch (error) {
      setRequestError(messageFromStoreError(error))
    } finally {
      setLoading(false)
    }
  }

  return <div className="store-setup-card">
    <div className="store-card-heading"><p className="eyebrow">STORE INFORMATION</p><h2>Set up your store</h2><p>Only required information is requested. Your store identity is always selected server-side.</p></div>
    {requestError ? <p className="auth-error" role="alert">{requestError}</p> : null}
    <form className="auth-form" onSubmit={submit} noValidate>
      <TextField label="Store name" name="store-name" autoComplete="organization" value={name} onChange={event => setName(event.target.value)} error={nameError} required />
      <div className="form-field"><span className="store-field-label">Currency</span><output className="store-readonly-field">BDT — Bangladeshi Taka <small>Fixed for the SellerOS prototype</small></output></div>
      <SelectField label="Time zone" name="timezone" value={timezone} onChange={event => setTimezone(event.target.value)} required>{timezoneOptions.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</SelectField>
      <div className="store-submit-row"><a className="button button-secondary" href="/">Back to dashboard</a><button className="button" type="submit" disabled={loading}>{loading ? 'Saving…' : 'Save and continue'}</button></div>
    </form>
  </div>
}

function ProfileDetails({ store, compact = false }: { store: StoreProfile; compact?: boolean }) {
  const account = getAuthSession()?.account
  return <>
    <div className={compact ? 'store-profile-grid compact' : 'store-profile-grid'}>
      <Card aria-labelledby="store-profile-title"><div className="section-heading"><div><p className="eyebrow">STORE PROFILE</p><h2 id="store-profile-title">{store.name}</h2><p>Current store information returned by the authorized API.</p></div><Badge tone="accent">Read only</Badge></div><dl className="profile-facts"><div><dt>Currency</dt><dd>{store.currency_code}</dd></div><div><dt>Time zone</dt><dd>{store.timezone}</dd></div></dl><p className="profile-boundary">Store editing is unavailable because the approved API currently supports only create and read.</p></Card>
      <Card aria-labelledby="user-profile-title"><p className="eyebrow">USER PROFILE</p><h2 id="user-profile-title">Your account</h2><dl className="profile-facts"><div><dt>Email address</dt><dd>{account?.email ?? 'Unavailable'}</dd></div><div><dt>Access</dt><dd>Authenticated seller</dd></div></dl><p className="profile-boundary">Account profile updates are not available in the current API.</p></Card>
    </div>
  </>
}

export function StoreSetupPage() {
  const { state, setState, reload } = useStoreProfile()
  return <SetupLayout>
    {state.status === 'loading' ? <LoadingState title="Checking your store" /> : null}
    {state.status === 'signed-out' ? <SignedOutState setup /> : null}
    {state.status === 'error' ? <ErrorState title="Unable to load store setup" action={<button className="button" onClick={() => void reload()}>Try again</button>}>{state.message}</ErrorState> : null}
    {state.status === 'setup' ? <StoreSetupForm onCreated={store => setState({ status: 'profile', store })} /> : null}
    {state.status === 'profile' ? <section className="store-setup-card"><p className="eyebrow">STORE SETUP COMPLETE</p><h2>Your store is ready</h2><p>Your existing store remains unchanged. Review the authorized profile below or continue to your dashboard.</p><ProfileDetails store={state.store} compact /><a className="button" href="/">Continue to dashboard</a></section> : null}
  </SetupLayout>
}

export function StoreProfilePage() {
  const { state, reload } = useStoreProfile()
  if (state.status === 'loading') return <LoadingState title="Loading store profile" />
  if (state.status === 'signed-out') return <SignedOutState setup={false} />
  if (state.status === 'error') return <ErrorState title="Unable to load store profile" action={<button className="button" onClick={() => void reload()}>Try again</button>}>{state.message}</ErrorState>
  if (state.status === 'setup') return <Card className="store-empty-state"><p className="eyebrow">STORE PROFILE</p><h2>Finish store setup first</h2><p>Your account does not yet have a store profile. Create one before using store-scoped SellerOS data.</p><a className="button" href="/store/setup">Set up store</a></Card>
  return <><div className="page-heading"><div><p className="eyebrow">SETTINGS</p><h1>Your profile</h1><p className="page-description">Review the current store and account information returned by SellerOS.</p></div><Badge tone="accent">Authorized data</Badge></div><ProfileDetails store={state.store} /></>
}
