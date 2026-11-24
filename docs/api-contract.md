# SellerOS API conventions — BACKEND-05

10 October 2026, updated for AUTH-01. This contract defines transport conventions, not business fields/endpoints. Existing public `/health/` and `/ready/` retain their separate probe payloads. AUTH-01 registers only account registration, token login, and current-account validation routes; no product or order route exists. Existing direct-success and error-envelope behavior is preserved.

## Version and naming

Future business APIs use `/api/v1/`, trailing slash, lowercase plural resource nouns, and opaque string representations of IDs. Example future paths `/api/v1/products/` and `/api/v1/orders/{id}/` are planned names, not live endpoints. GET lists/details, POST creation (201), PATCH partial update (200), and DELETE only where an approved policy permits it (204, no body). Explicit lifecycle actions may use POST under the resource after rules are approved; never replace order transitions with arbitrary PATCH. No deletion/archival/business rule is selected here. Breaking contract changes require a new version or explicit migration agreement.

## AUTH-01 authentication routes

`POST /api/v1/auth/register/` and `POST /api/v1/auth/login/` are public JSON-only endpoints. Successful responses directly return `{"account":{"id":"<opaque UUID>","email":"..."},"token":"<opaque bearer token>"}` with 201 or 200 respectively. `GET /api/v1/auth/me/` requires `Authorization: Token <token>` and directly returns `{"id":"<opaque UUID>","email":"..."}`. These endpoints do not create stores or confer store access.

Auth validation errors use the established envelope. Duplicate registration is 400/`validation_error`; unknown email, wrong password, and inactive account are 401/`authentication_failed` with the same generic detail; missing token on `/me/` is 401/`not_authenticated`. AUTH-01's IP/cache-backed limits are registration 3/hour and login 5/minute; see [authentication setup](setup/authentication.md) for validation and token-lifecycle boundaries.

## AUTH-02 store-profile route

`POST` and `GET /api/v1/stores/current/` use the authenticated token context rather than a client-supplied store or owner ID. `POST` accepts only `name` and optional IANA `timezone`, then creates the first store for an eligible account and returns 201 with `{"id":"<opaque UUID>","name":"...","timezone":"...","currency_code":"BDT"}`. `GET` returns that same restricted profile for an owner or active staff member. It has no update operation in AUTH-02.

An owner cannot create a second store (400/`validation_error`); any staff membership prevents store creation (403/`permission_denied`), including an inactive/revoked one. Accounts without a permitted store and revoked staff receive 404/`not_found` from read. Unsupported payload fields, including `owner_id` and `currency_code`, receive 400/`validation_error` rather than being silently ignored. See [store profile setup](setup/store-profile.md).

## AUTH-03 store-scope enforcement

Every future store-owned list, detail, mutation, count, filter, and aggregation must begin with the server-resolved store context and a store-scoped queryset. No client-supplied store/owner/role field can select a tenant. The existing `GET /api/v1/stores/current/` route accepts no query parameters; an attempted `store_id` selector receives 400/`validation_error`, not another store's profile. See [store permission setup](setup/store-permissions.md).

## PRODUCT-03 catalogue reads

`GET /api/v1/products/` and `GET /api/v1/products/{id}/` require token authentication and resolve the current owner/active-staff store server-side. The list is paginated with the standard envelope and returns only the current store's products. It accepts one each of `page`, `page_size`, `category`, `is_active`, and `ordering`; no `store_id` or owner selector is accepted. `category` is a non-blank case-insensitive exact match, `is_active` is `true` or `false` (case-insensitive), and `ordering` is one of `name`, `-name`, `created_at`, or `-created_at`. The default is case-insensitive name ascending followed by UUID ascending; every allowed ordering has UUID as a deterministic tie-breaker.

List rows serialize product catalogue fields only. Detail reads use the same scope, include only that product's variants, and accept no query parameters. A missing or foreign `{id}` has the same 404/`not_found` contract and discloses no product content.

`POST /api/v1/products/` creates a product for the server-resolved current owner/active-staff store and returns the direct serialized resource with 201. `PATCH /api/v1/products/{id}/` partially updates only a same-store product and returns it with 200. Both write routes accept the strict product write fields `name`, `category`, `selling_price`, `unit_cost`, `has_variants`, and `is_active`; `store_id`, ownership fields, and unknown fields return 400/`validation_error`. Setting `is_active` to false deactivates a product. There is no hard-delete route. An API update cannot set `has_variants` false while variant rows still exist; it must preserve a consistent variant-based representation until a separately approved lifecycle operation exists. No variant write, stock, archive/delete route is introduced.

## INV-03 inventory reads and manual adjustment

`GET /api/v1/inventory/` requires token authentication, resolves the current owner/active-staff store server-side, and returns a standard paginated list of that store's stock units. It accepts only `page` and `page_size`, ordered by case-insensitive product name then stock-unit UUID. Each row includes `id`, product/optional variant IDs and names, `quantity_on_hand`, nullable `low_stock_threshold`, `is_low_stock`, and `updated_at`. It never includes a store selector or records from another store.

`GET /api/v1/inventory/{stock_unit_id}/movements/` accepts only pagination parameters and returns the selected same-store stock unit's movement history, newest first with UUID as the tie-breaker. Rows include the movement ID, stock-unit ID, type, signed quantity delta, nullable reason, creating account ID, nullable reversal ID, and occurrence timestamp. A missing or foreign stock-unit ID returns the same 404/`not_found` response and discloses no stock or movement content.

`POST /api/v1/inventory/{stock_unit_id}/adjustments/` accepts exactly `quantity_delta` (a nonzero whole-unit signed delta) and non-blank `reason`. The server selects `MANUAL_ADJUSTMENT`, the authenticated creator, store, and operation ID; client-supplied ownership, movement type, reversal, or operation fields are rejected as 400/`validation_error`. The route calls the atomic inventory service, returning the created movement directly with 201. An adjustment that would make stock negative returns 400/`validation_error` and changes neither the cached quantity nor movement history. INV-03 creates no endpoint for opening balances, order deductions/restorations, threshold editing, or direct quantity updates.

## CUSTOMER-02 customer profiles

`GET /api/v1/customers/` requires token authentication, resolves the current owner/active-staff store server-side, and returns only that store's customer profiles in the standard pagination envelope. It accepts only `page` and `page_size`, ordered by case-insensitive `display_name` then UUID. Rows include `id`, `display_name`, nullable `phone`/`email`, and creation/update timestamps; they never include a store selector.

`GET /api/v1/customers/{customer_id}/` reads one same-store profile. `POST /api/v1/customers/` creates a profile for the server-resolved store and returns it with 201. `PATCH /api/v1/customers/{customer_id}/` partially updates only a same-store profile and returns it with 200. Write payloads accept exactly `display_name`, optional `phone`, and optional `email`; the server rejects store/owner fields and unknown fields. Names must be non-blank; blank optional contact values normalize to `null`; email syntax is validated. Same-store duplicate contacts are permitted: this version has no contact matching, merge, delivery, search, or deletion operation. Missing/foreign detail IDs return indistinguishable 404/`not_found` responses.

`GET /api/v1/customers/{customer_id}/purchase-history/` accepts no query parameters and returns the current same-store derived summary directly: `purchase_count`, nullable `last_purchase_at`, and two-decimal string `total_spend`. It is calculated at request time from recorded eligible order snapshots; the customer table has no cached count, timestamp, or spend column. A freshly seeded eligible order is reflected by the next request, while returned/refunded orders do not add a current eligible purchase. A missing/foreign ID returns 404/`not_found` without profile or order details. This is read-only; order creation/lifecycle APIs are not part of CUSTOMER-05.

## ORDER-05 order reads

`GET /api/v1/orders/` requires token authentication and returns only the server-resolved current store's orders in the standard pagination envelope. It accepts one each of `page`, `page_size`, stored `status`, `created_from`, and `created_to`. Status must be one approved stored order enum. The inclusive date filters use ISO `YYYY-MM-DD` against the server-recorded UTC `created_at` operational timestamp; they are not delivery-date financial/analytics grouping. `created_from` cannot follow `created_to`. Results are newest `created_at` first, then UUID descending.

List rows include opaque order/customer IDs, nullable customer display name, status, currency, order discount, nullable seller delivery cost, lifecycle timestamps, and audit timestamps. `GET /api/v1/orders/{order_id}/` uses the same store scope and additionally includes immutable item snapshots, product/variant IDs, quantities, price/cost snapshots, and discount allocations. Neither endpoint accepts a store selector. Foreign/missing IDs return indistinguishable 404/`not_found` responses. ORDER-05 has no creation, edit, cancellation, refund, payment, or analytics route.

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
