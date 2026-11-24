const SESSION_STORAGE_KEY = 'selleros.auth.session.v1'

export type AuthenticatedAccount = {
  id: string
  email: string
}

export type AuthSession = {
  account: AuthenticatedAccount
  token: string
}

function isAccount(value: unknown): value is AuthenticatedAccount {
  return value !== null
    && typeof value === 'object'
    && 'id' in value
    && typeof value.id === 'string'
    && 'email' in value
    && typeof value.email === 'string'
}

function isSession(value: unknown): value is AuthSession {
  return value !== null
    && typeof value === 'object'
    && 'token' in value
    && typeof value.token === 'string'
    && value.token.length > 0
    && 'account' in value
    && isAccount(value.account)
}

export function getAuthSession(): AuthSession | null {
  try {
    const stored = window.sessionStorage.getItem(SESSION_STORAGE_KEY)
    if (!stored) return null
    const value: unknown = JSON.parse(stored)
    return isSession(value) ? value : null
  } catch {
    return null
  }
}

export function saveAuthSession(session: AuthSession): void {
  window.sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session))
}

export function clearAuthSession(): void {
  window.sessionStorage.removeItem(SESSION_STORAGE_KEY)
}
