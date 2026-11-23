# SellerOS API conventions — BACKEND-05

10 October 2026, updated for AUTH-01. This contract defines transport conventions, not business fields/endpoints. Existing public `/health/` and `/ready/` retain their separate probe payloads. AUTH-01 registers only account registration, token login, and current-account validation routes; no product or order route exists. Existing direct-success and error-envelope behavior is preserved.

## Version and naming

Future business APIs use `/api/v1/`, trailing slash, lowercase plural resource nouns, and opaque string representations of IDs. Example future paths `/api/v1/products/` and `/api/v1/orders/{id}/` are planned names, not live endpoints. GET lists/details, POST creation (201), PATCH partial update (200), and DELETE only where an approved policy permits it (204, no body). Explicit lifecycle actions may use POST under the resource after rules are approved; never replace order transitions with arbitrary PATCH. No deletion/archival/business rule is selected here. Breaking contract changes require a new version or explicit migration agreement.

## AUTH-01 authentication routes

`POST /api/v1/auth/register/` and `POST /api/v1/auth/login/` are public JSON-only endpoints. Successful responses directly return `{"account":{"id":"<opaque UUID>","email":"..."},"token":"<opaque bearer token>"}` with 201 or 200 respectively. `GET /api/v1/auth/me/` requires `Authorization: Token <token>` and directly returns `{"id":"<opaque UUID>","email":"..."}`. These endpoints do not create stores or confer store access.

Auth validation errors use the established envelope. Duplicate registration is 400/`validation_error`; unknown email, wrong password, and inactive account are 401/`authentication_failed` with the same generic detail; missing token on `/me/` is 401/`not_authenticated`. AUTH-01's IP/cache-backed limits are registration 3/hour and login 5/minute; see [authentication setup](setup/authentication.md) for validation and token-lifecycle boundaries.

## Success and pagination

Detail/create/update success returns the serialized resource directly, with no success wrapper. Future collection APIs use StandardPagination (DRF generic-view default): page-number pagination, default 20, optional page_size integer 1–100. List shape:

```json
{"count":1,"next":null,"previous":null,"results":[{"id":"example"}]}
```

count is the total authorized filtered result count, not total across stores. next/previous are nullable URL strings; clients must validate origin/allowed API path before following rather than forwarding credentials to arbitrary URLs. Existing paginator emits absolute links. page starts at 1; invalid/out-of-range pages produce 404/not_found; DRF's last alias is supported. Invalid page_size produces 400/validation_error rather than silent fallback. Lists need deterministic order with a unique tie-breaker; each module specifies supported sort keys and its ordering before shipping. Page-number lists can shift under concurrent mutations; no snapshot/cursor consistency guarantee. Empty collection: count 0, results [], both links null.

## Filtering

Each endpoint declares allowlisted query parameters and typed value validation, using validate_query_parameters before filtering its already-authorized queryset. Unknown or repeated parameters produce 400/validation_error. page/page_size must be explicitly allowed for paginated views. No implicit store_id/owner_id filter grants access. Filter names, enums, search/sort fields and date boundaries remain per-module contracts; no universal automatic ORM filtering or django-filter dependency is added. Tests use category as a synthetic fixture only. Never pass arbitrary query keys to ORM lookups; permission/store scoping precedes filters, counts and serialization. Lists must not expose foreign records through search/counts.

## Error shape

```json
{"error":{"code":"validation_error","details":{"quantity":["Use a positive quantity."]}}}
```

Stable required fields: error object, string code, details containing nested string/list/object messages. Non-field validation uses non_field_errors; nested serializer errors retain nesting. Client logic uses status/code, not human message text. No universal resource schema or per-field machine error-code contract is invented. Examples are synthetic, not exact business validations.

| HTTP | Code | Details convention |
| --- | --- | --- |
| 400 | validation_error | Field/non-field nested messages |
| 400 | parse_error | detail string |
| 403 | permission_denied | detail string |
| 401 or 403 | not_authenticated / authentication_failed | detail string; DRF status depends on chosen authentication scheme |
| 404 | not_found | detail string (missing object or invalid page) |
| 405 | method_not_allowed | detail string; Allow header preserved |
| 415 | unsupported_media_type | detail string |
| 429 | throttled | detail string; Retry-After preserved |

Token authentication is now the global DRF authentication class. Public registration/login views explicitly opt out of token parsing; other protected DRF views return 401/`not_authenticated` with `WWW-Authenticate: Token` when no valid token is supplied. Authenticated same-store permissions are future authorization work. Future scoped object lookup returns 404 for inaccessible foreign IDs rather than disclosing existence; actual permission failure on an authorized context is 403. Existing handler preserves status and protocol headers.

The envelope applies to DRF-handled exceptions only. Resolver 404, middleware errors and unexpected 500s may have non-JSON bodies today; clients must handle non-JSON failure safely. Never display raw HTML/trace output. Unknown failures are not serialized from exception text. Do not place secrets/private inputs in validation messages. Wider global failure wrapping is not implemented by this task.

## Frontend consumption and business boundaries

`frontend/src/api/types.ts` contains prefix, pagination/query and recursive error-detail types. `contract-examples.ts` checks list/validation/permission/not-found examples with TypeScript satisfies; it is not loaded into the shell or an API client. Actual network validation and query building belong to FRONTEND-02. Future dates/decimal-money serialization need explicit resource contracts; currency/rounding, financial timestamps, return rules and forecast/scenario thresholds remain [DECISION REQUIRED] in earlier planning records. No numeric money/ID/date type is silently imposed on business models.

## Verification evidence

Initial branch backend; pre-existing changes to docs/setup/environment.md and untracked postgresql.md were preserved. Inspected DRF handler/settings/tests and frontend tsconfig; no existing business contract or business routes found. New test views are not registered publicly.

Verified using the backend virtualenv Python and config.settings.test, with the existing local environment loaded without printing values:

- Django management `check`: no issues.
- Django management `test core.tests core.test_settings core.test_environment core.test_api core.test_health core.test_contract core.test_database.DatabaseConfigurationTests`: 23 tests passed. This selection checks database configuration without creating a database.
- After adding the oversized page_size guard, `test core.test_contract --verbosity 1`: all 3 tests passed again.
- `npm run typecheck --prefix frontend`: passed.
- `npm run build --prefix frontend`: passed on retry outside the restricted sandbox; the first attempt hit filesystem EPERM while resolving index.html.
- `git diff --check`: passed; Git reported only line-ending conversion warnings.

No dependency added, database schema change, secret, frontend feature screen or commit. Next dependency is the Master Plan's frontend/schema/API design work; no next task started.
