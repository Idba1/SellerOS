import { useState, type FormEvent } from 'react'
import { TextField } from '../components/FormFields'
import { login, messageFromAuthError, register } from './api'
import { saveAuthSession } from './session'

type AuthMode = 'login' | 'register'

function AuthFrame({ children }: { children: React.ReactNode }) {
  return <main className="auth-page">
    <section className="auth-brand-panel" aria-label="SellerOS introduction">
      <a className="auth-wordmark" href="/login">SellerOS</a>
      <div className="auth-brand-copy">
        <p className="eyebrow">SELLEROS WORKSPACE</p>
        <h1>Less busywork.<br />More clarity.</h1>
        <p>Manage your social-commerce records in one focused workspace, with the facts you need for confident day-to-day decisions.</p>
        <ul>
          <li>Organize products and orders</li>
          <li>Track stock and seller-entered expenses</li>
          <li>Review insights from recorded data</li>
        </ul>
      </div>
      <p className="auth-panel-footnote">A social-commerce decision-support prototype.</p>
    </section>
    <section className="auth-form-panel">{children}</section>
  </main>
}

function passwordError(password: string): string | undefined {
  if (password.length === 0) return 'Enter your password.'
  return undefined
}

export function AuthenticationPage({ mode: initialMode = 'login' }: { mode?: AuthMode }) {
  const [mode, setMode] = useState<AuthMode>(initialMode)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [attempted, setAttempted] = useState(false)
  const checkedEmailError = !email.trim() ? 'Enter your email address.' : !/^\S+@\S+\.\S+$/.test(email) ? 'Enter a valid email address.' : undefined
  const checkedPasswordError = passwordError(password)
  const emailError = attempted ? checkedEmailError : undefined
  const localPasswordError = attempted ? checkedPasswordError : undefined

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAttempted(true)
    if (checkedEmailError || checkedPasswordError) return
    setLoading(true)
    setSubmitError(null)
    try {
      const session = mode === 'login' ? await login(email, password) : await register(email, password)
      saveAuthSession(session)
      window.location.assign('/')
    } catch (error) {
      setSubmitError(messageFromAuthError(error))
    } finally {
      setLoading(false)
    }
  }

  const title = mode === 'login' ? 'Welcome back' : 'Create your account'
  const description = mode === 'login'
    ? 'Sign in to access your SellerOS workspace.'
    : 'Create a seller account to begin setting up your workspace.'

  return <AuthFrame>
    <div className="auth-card">
      <div className="auth-card-heading"><p className="eyebrow">SELLER ACCESS</p><h2>{title}</h2><p>{description}</p></div>
      <div className="auth-mode" role="group" aria-label="Authentication action">
        <button className={mode === 'login' ? 'auth-mode-current' : ''} type="button" aria-pressed={mode === 'login'} onClick={() => { setMode('login'); setSubmitError(null); setAttempted(false) }}>Sign in</button>
        <button className={mode === 'register' ? 'auth-mode-current' : ''} type="button" aria-pressed={mode === 'register'} onClick={() => { setMode('register'); setSubmitError(null); setAttempted(false) }}>Create account</button>
      </div>
      {submitError ? <p className="auth-error" role="alert">{submitError}</p> : null}
      <form className="auth-form" onSubmit={submit} noValidate>
        <TextField label="Email address" name="email" type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} error={emailError} required />
        <TextField label="Password" name="password" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={password} onChange={event => setPassword(event.target.value)} error={localPasswordError} helpText={mode === 'register' ? 'Use at least 12 characters. A numeric-only password is not accepted.' : undefined} required />
        <button className="button auth-submit" type="submit" disabled={loading}>{loading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}</button>
      </form>
      <a className="auth-recovery-link" href="/forgot-password">Forgot your password?</a>
      <p className="auth-disclosure">SellerOS stores the access token only for this browser tab. Never share it or include it in screenshots.</p>
    </div>
  </AuthFrame>
}

export function PasswordRecoveryUnavailable({ reset = false }: { reset?: boolean }) {
  return <AuthFrame>
    <div className="auth-card auth-unavailable-card">
      <p className="eyebrow">SELLER ACCESS</p>
      <h2>{reset ? 'Set a new password' : 'Forgot your password?'}</h2>
      <p>Password recovery is not available in this prototype because SellerOS has no approved reset or email-verification service yet.</p>
      <p className="auth-unavailable-note">This page deliberately does not collect an email address or a new password: no recovery action could be completed safely.</p>
      <a className="button auth-submit" href="/login">Back to sign in</a>
    </div>
  </AuthFrame>
}
