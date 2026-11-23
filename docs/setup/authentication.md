# Authentication API — AUTH-01

SellerOS uses Django REST Framework's built-in `rest_framework.authtoken` application with `TokenAuthentication`; no third-party package is added. The token is an opaque bearer credential. Use it only over HTTPS outside local development, never place it in a URL, query parameter, screenshot, error message, source file, or browser-visible provider configuration.

## Routes and payloads

All routes use JSON and the existing `/api/v1/` convention.

| Method and route | Access | Request | Success |
| --- | --- | --- | --- |
| `POST /api/v1/auth/register/` | Public; 3 requests/IP/hour | `email`, `password` | `201` with `account` (`id`, `email`) and `token` |
| `POST /api/v1/auth/login/` | Public; 5 requests/IP/minute | `email`, `password` | `200` with `account` (`id`, `email`) and a newly rotated `token` |
| `GET /api/v1/auth/me/` | `Authorization: Token <token>` | None | `200` with account `id` and `email` |

Every successful registration creates only an account; it does not create a store, assign a role, grant staff access, or expose another store. A successful login deletes that account's prior DRF token before issuing a new token, so only one active prototype token exists per account.

## Validation and failure behavior

- Emails are trimmed/lowercased and case-insensitively unique.
- Passwords must have at least 12 characters and cannot be entirely numeric. Passwords are hashed by the existing account model and never returned.
- Duplicate registration returns the established `400` `validation_error` envelope with an `email` detail.
- Unknown email, wrong password, and inactive account all return the same `401` `authentication_failed` envelope: `Unable to log in with provided credentials.` This avoids account-existence disclosure.
- Missing/invalid bearer credentials on `GET /me/` return `401` `not_authenticated`; malformed/unknown tokens use the existing DRF authentication error behavior.
- Rate limits are process/cache backed prototype safeguards, not a distributed abuse-control service. A throttled request uses the existing `429` `throttled` error contract.

## Boundary and follow-up

This task intentionally does not add logout, password reset, email verification, token expiry, staff provisioning, store onboarding, browser session cookies, or store-level authorization. Tokens are long-lived until the next successful login rotates them; a production release requires a token-expiry/revocation policy and HTTPS deployment review before use with real accounts.
