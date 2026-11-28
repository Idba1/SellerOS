import { useState, type FormEvent } from 'react'
import { TextField } from '../components/FormFields'
import { confirmPasswordReset, login, messageFromAuthError, register, requestPasswordReset } from './api'
import { clearAuthSession, saveAuthSession } from './session'

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
      // Both new and existing accounts pass through the authorized store gate.
      // It shows setup only when the account has no accessible store; otherwise
      // it confirms the current profile and offers the dashboard continuation.
      window.location.assign('/store/setup')
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
export function PasswordRecoveryPage() {
  const [email, setEmail] = useState('')
  const [attempted, setAttempted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [confirmation, setConfirmation] = useState<string | null>(null)
  const emailError = !email.trim() ? 'Enter your email address.' : !/^\S+@\S+\.\S+$/.test(email) ? 'Enter a valid email address.' : undefined

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAttempted(true)
    if (emailError) return
    setLoading(true)
    setSubmitError(null)
    try {
      setConfirmation(await requestPasswordReset(email))
    } catch (error) {
      setSubmitError(messageFromAuthError(error))
    } finally {
      setLoading(false)
    }
  }

  return <AuthFrame>
    <div className="auth-card">
      <div className="auth-card-heading"><p className="eyebrow">SELLER ACCESS</p><h2>Forgot your password?</h2><p>Enter your account email and we will send a password-reset link if the account is active.</p></div>
      {confirmation ? <div className="auth-success" role="status"><p>{confirmation}</p><p>For local development, check the backend terminal for the generated link.</p></div> : <>
        {submitError ? <p className="auth-error" role="alert">{submitError}</p> : null}
        <form className="auth-form" onSubmit={submit} noValidate>
          <TextField label="Email address" name="email" type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} error={attempted ? emailError : undefined} required />
          <button className="button auth-submit" type="submit" disabled={loading}>{loading ? 'Sending link…' : 'Send reset link'}</button>
        </form>
      </>}
      <a className="auth-recovery-link" href="/login">Back to sign in</a>
    </div>
  </AuthFrame>
}
export function PasswordResetPage() {
  const parameters = new URLSearchParams(window.location.search)
  const uid = parameters.get('uid')
  const token = parameters.get('token')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [attempted, setAttempted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const passwordError = password.length < 12 ? 'Use at least 12 characters.' : undefined
  const confirmationError = confirmation !== password ? 'Passwords do not match.' : undefined

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAttempted(true)
    if (!uid || !token || passwordError || confirmationError) return
    setLoading(true)
    setSubmitError(null)
    try {
      const detail = await confirmPasswordReset(uid, token, password)
      clearAuthSession()
      setSuccess(detail)
    } catch (error) {
      setSubmitError(messageFromAuthError(error))
    } finally {
      setLoading(false)
    }
  }

  return <AuthFrame>
    <div className="auth-card">
      <div className="auth-card-heading"><p className="eyebrow">SELLER ACCESS</p><h2>Set a new password</h2><p>Your new password will sign out existing SellerOS browser sessions.</p></div>
      {!uid || !token ? <div className="auth-error" role="alert">This password reset link is incomplete or invalid.</div> : success ? <div className="auth-success" role="status"><p>{success}</p></div> : <>
        {submitError ? <p className="auth-error" role="alert">{submitError}</p> : null}
        <form className="auth-form" onSubmit={submit} noValidate>
          <TextField label="New password" name="password" type="password" autoComplete="new-password" value={password} onChange={event => setPassword(event.target.value)} error={attempted ? passwordError : undefined} helpText="Use at least 12 characters. A numeric-only password is not accepted." required />
          <TextField label="Confirm new password" name="confirmation" type="password" autoComplete="new-password" value={confirmation} onChange={event => setConfirmation(event.target.value)} error={attempted ? confirmationError : undefined} required />
          <button className="button auth-submit" type="submit" disabled={loading}>{loading ? 'Resetting password…' : 'Reset password'}</button>
        </form>
      </>}
      <a className="auth-recovery-link" href="/login">Back to sign in</a>
    </div>
  </AuthFrame>
}
