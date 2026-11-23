# Store profile API — AUTH-02

SellerOS already stores `Store` in the `accounts` app because the one-store owner/staff relation is its tenant boundary. AUTH-02 adds API access to that existing model; it does not duplicate, move, or migrate the store table.

## Route

`/api/v1/stores/current/` is the only store-profile route in this task. It accepts JSON and requires `Authorization: Token <token>`.

| Method | Who may use it | Request / response |
| --- | --- | --- |
| `POST` | Active account with neither an owned store nor any staff-membership row | Request: `name`, optional IANA `timezone`; response: 201 `{id, name, timezone, currency_code}`. Owner is always the authenticated account. |
| `GET` | Store owner or active staff member | Response: 200 `{id, name, timezone, currency_code}` for their own authorized store only. |

Currency is server-owned `BDT`; owner IDs, currency overrides, and every other unsupported field are rejected rather than ignored. Owner/staff membership data, owner email, account IDs, and settings-management controls are never returned by this profile payload.

## Access and errors

- A staff account, including a revoked staff account with a retained membership row, cannot create a store.
- An owner cannot create a second store; create returns 400 `validation_error`.
- A revoked staff member or account with no permitted store gets 404 `not_found` from `GET`, with no profile data.
- No token gets 401 `not_authenticated`; staff create gets 403 `permission_denied`.
- `POST` is protected by an account-row lock and the existing unique owner constraint to prevent duplicate stores under concurrent owner requests.

No profile update endpoint is included. Staff cannot manage store settings, and owner updates are a later authorized task.
