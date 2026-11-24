# SellerOS data dictionary and constraints

**Status:** DB-02 field-level design record. It defines the minimum PostgreSQL/Django data contract for the DB-01 entities. It creates no models, migrations, APIs, fixtures, or real-data records.

## 1. Contract boundary and selected prototype defaults

This dictionary is the physical-field companion to the [logical ERD](erd.md). DB-01 names logical entity keys such as `account_id`; this document selects the concrete Django model convention: every entity has a UUID `id` primary key and relations use the referenced model's `<name>_id` column. Future APIs serialize every UUID as the opaque string field `id`, consistent with the existing [API contract](api-contract.md). No business endpoint exists yet, so this document does not claim a live request or response shape.

The following minimum decisions are selected for the standalone prototype so schema work can proceed:

- PostgreSQL `uuid` / Django `UUIDField` is used for all primary keys; IDs are generated server-side and are never accepted as ownership authority.
- Timestamps are stored as UTC `timestamptz` with Django `USE_TZ=True`. Store-facing grouping/display uses an IANA store timezone; the prototype default is `Asia/Dhaka`.
- The prototype currency is `BDT`, stored as ISO 4217 `currency_code`. Monetary values use PostgreSQL `numeric(12,2)` / Python `Decimal`, `ROUND_HALF_UP` at every persisted monetary boundary. Floating point is prohibited for money.
- Sellable quantities and stock are whole units (`integer`), never fractional. Price is strictly greater than zero; known zero cost is allowed and distinct from missing cost (`NULL`).
- `PENDING` is the stored first submitted order status and is displayed to the seller as **New**, satisfying FR-06 without changing the approved lifecycle. `DRAFT` is an internal preparation status; it may be empty, but `PENDING` and later statuses require at least one item.
- A product is either standalone or variant-based. A standalone product has exactly one `StockUnit` with no variant. A variant-based product has no default stock unit and exactly one `StockUnit` for each variant. A product cannot switch between those modes after it has an order item or inventory movement.
- Customer contact values are optional and are not hard-unique; social-commerce customers can share a phone/email. A display name is required. No address, payment, sensitive-trait, social-platform, or credit field is stored.
- Analysis logs contain only synthetic-case/metric references and metadata, never provider keys, raw prompts, raw customer messages, addresses, payment data, or unrestricted generated text. The selected local retention period is 30 days from creation; deletion enforcement is a later implementation responsibility.

These are prototype decisions, not financial-accounting advice, provider approval, or permission to process real customer data. The approved synthetic-only policy remains in force.

## 2. Common data conventions

| Convention | Rule |
| --- | --- |
| Names | Django model fields use `snake_case`; API resource keys are lower camel-free field names exactly as serialized later (for example `created_at`, `seller_delivery_cost`). |
| Primary keys | `id`: `uuid`, non-null, PK, server-generated. API representation: opaque UUID string. |
| Foreign keys | Use `uuid` FK columns. A client may supply a related resource ID only where its later endpoint allows it; the server scopes/authorizes it before persistence. |
| Audit times | `created_at`: non-null UTC `timestamptz`, server-set once. `updated_at`: non-null UTC `timestamptz`, server-updated only on mutable rows. |
| Money | `numeric(12,2)` in `BDT`; values are decimal strings in a future JSON API to avoid JavaScript precision loss. Never use `float`/`double precision`. |
| Quantity | `integer`, measured in whole sellable units. Positive means `>= 1`; stock/threshold uses `>= 0`. |
| Text | Unicode text, trimmed on input; blank strings are rejected where a field is required. Limits are validation limits, not a reason to truncate user data silently. |
| Date/time | Calendar dates use PostgreSQL `date`; event times use `timestamptz`. UTC storage and store-timezone display are both required. |
| Deletion | Historical business rows are protected from ordinary deletion. Products/variants use an active flag; staff access uses an active flag. See the per-entity delete policy. |
| Store isolation | Every direct store FK is server-derived or checked against the authenticated owner's/active staff member's store. Indirect links must resolve to the same store in the transaction. |

## 3. Account, store, and access records

### Account

| Field | PostgreSQL / Django type | Null / default | Validation and ownership |
| --- | --- | --- | --- |
| `id` | `uuid` / `UUIDField` | PK; generated | Account identifier; no tenant parent. API exposes it only where later authorization permits. |
| `email` | `varchar(254)` / `EmailField` | required | Trim and lowercase before save; unique case-insensitively across accounts; valid email syntax required. |
| `password` | Django password-hash field | required for password authentication | Django-managed one-way hash only; never serialize, log, seed with a real credential, or treat as a profile field. |
| `is_active` | `boolean` | required; default `true` | Inactive accounts cannot authenticate or access seller records. |
| `created_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC account creation time. |
| `updated_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC last account-record update time. |

**Constraints:** `UNIQUE (LOWER(email))`. An account may own at most one store or hold one staff membership, never both. That cross-table participation rule needs service/transactional validation in addition to ordinary FKs.

**Delete policy:** do not ordinarily delete an account with a store, membership, or historical log reference. Deactivate it instead; any exceptional removal requires an explicit administrative retention process.

### Store

| Field | PostgreSQL / Django type | Null / default | Validation and ownership |
| --- | --- | --- | --- |
| `id` | `uuid` / `UUIDField` | PK; generated | Tenant root. |
| `owner_id` | `uuid` FK → `Account.id` / `OneToOneField` | required | Server-derived during onboarding; unique; owner cannot be a staff member. `on_delete=PROTECT`. |
| `name` | `varchar(160)` / `CharField` | required | Trimmed non-blank business/store name; not globally unique. |
| `timezone` | `varchar(64)` / `CharField` | required; default `Asia/Dhaka` | Must be a valid IANA timezone. Used only for display/grouping; storage remains UTC. |
| `currency_code` | `char(3)` / `CharField` | required; default `BDT` | Must be uppercase `BDT` in this prototype. Changing it after a store exists is not allowed. |
| `created_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC creation time. |
| `updated_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC profile-update time. |

**Constraints:** `UNIQUE (owner_id)`. No client-owned `owner_id` assignment, store transfer, or cross-store record reassignment.

**Delete policy:** `PROTECT` all operational history. Store deletion, transfer, and recreation are outside ordinary seller operations.

### StoreMembership

| Field | PostgreSQL / Django type | Null / default | Validation and ownership |
| --- | --- | --- | --- |
| `id` | `uuid` / `UUIDField` | PK; generated | Membership identifier. |
| `store_id` | `uuid` FK → `Store.id` / `ForeignKey` | required | Owner creates/revokes only for its own store; `on_delete=PROTECT`. |
| `account_id` | `uuid` FK → `Account.id` / `OneToOneField` | required | Staff account; one membership maximum; must not own any store; `on_delete=PROTECT`. |
| `role` | `varchar(16)` / `CharField(choices=...)` | required; fixed `STAFF` | The owner role is represented only by `Store.owner_id`; client cannot choose another role. |
| `is_active` | `boolean` | required; default `true` | False revokes business access immediately. |
| `created_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC provisioning time. |
| `updated_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC activation/revocation time. |

**Constraints:** `UNIQUE (account_id)` and `CHECK (role = 'STAFF')`. Re-enable the same row if an owner reinstates an account; never create a second membership or let revocation create owner/onboarding eligibility.

**Delete policy:** revoke (`is_active=false`), do not ordinary-delete; keep the membership as authorization history.

## 4. Catalogue and inventory records

### Product

| Field | PostgreSQL / Django type | Null / default | Validation and ownership |
| --- | --- | --- | --- |
| `id` | `uuid` / `UUIDField` | PK; generated | Product identifier. |
| `store_id` | `uuid` FK → `Store.id` / `ForeignKey` | required | Server-scoped; `on_delete=PROTECT`. |
| `name` | `varchar(160)` / `CharField` | required | Trimmed, non-blank seller-facing product name. |
| `category` | `varchar(80)` / `CharField` | nullable; default `NULL` | Optional free-text category; no unapproved category taxonomy/table. |
| `selling_price` | `numeric(12,2)` / `DecimalField` | required | BDT; strictly greater than `0.00`. Applies to the product and all of its variants. |
| `unit_cost` | `numeric(12,2)` / `DecimalField` | nullable; default `NULL` | BDT; when known, `>= 0.00`. `NULL` means unknown—not zero—and blocks a complete profit claim. |
| `has_variants` | `boolean` | required; default `false` | Selects standalone versus variant-based stock rule; cannot change after historical use. |
| `is_active` | `boolean` | required; default `true` | False removes the product from new order selection but preserves history. |
| `created_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC creation time. |
| `updated_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC latest mutable-catalogue update time. |

**Constraints:** no global product-name uniqueness. A deactivated product/variant cannot be attached to a new draft/order. A product with `has_variants=true` must have variants before transition to `PENDING`.

**Delete policy:** deactivate, never cascade-delete an item referenced by an order item, stock unit, or movement.

### ProductVariant

| Field | PostgreSQL / Django type | Null / default | Validation and ownership |
| --- | --- | --- | --- |
| `id` | `uuid` / `UUIDField` | PK; generated | Variant identifier. |
| `product_id` | `uuid` FK → `Product.id` / `ForeignKey` | required | Parent product must have `has_variants=true`; `on_delete=PROTECT`. |
| `name` | `varchar(80)` / `CharField` | required | Trimmed non-blank option label, for example `Blue` or `Large`; no SKU field in this minimum prototype. |
| `is_active` | `boolean` | required; default `true` | False prevents new use but preserves historical reference. |
| `created_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC creation time. |
| `updated_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC last variant update time. |

**Constraints:** `UNIQUE (product_id, LOWER(name))`; a variant inherits its product's price, cost, category, currency, and store. It cannot be used with an order/item or stock unit from another store.

**Delete policy:** deactivate, never delete through historical item/movement references.

### StockUnit

| Field | PostgreSQL / Django type | Null / default | Validation and ownership |
| --- | --- | --- | --- |
| `id` | `uuid` / `UUIDField` | PK; generated | The single stock-bearing identity used by the ledger. |
| `store_id` | `uuid` FK → `Store.id` / `ForeignKey` | required | Must equal the product/variant store; `on_delete=PROTECT`. |
| `product_id` | `uuid` FK → `Product.id` / `ForeignKey` | required | Parent catalogue product; `on_delete=PROTECT`. |
| `variant_id` | `uuid` FK → `ProductVariant.id` / `ForeignKey` | nullable; default `NULL` | `NULL` only for standalone products; non-null only for a variant of `product_id`; `on_delete=PROTECT`. |
| `quantity_on_hand` | `integer` / `IntegerField` | required; default `0` | Whole units; `>= 0`. Updated only atomically with an inventory movement. |
| `low_stock_threshold` | `integer` / `IntegerField` | nullable; default `NULL` | Whole units; `>= 0`. `NULL` means “not configured,” never a guessed threshold. |
| `created_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC initialization time. |
| `updated_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC latest balance/threshold update time. |

**Constraints:** partial unique `UNIQUE (product_id) WHERE variant_id IS NULL`; partial unique `UNIQUE (variant_id) WHERE variant_id IS NOT NULL`; check/product-service validation that product, variant, and store agree. For `has_variants=false`, exactly one null-variant unit is required. For `has_variants=true`, each active variant requires exactly one unit and no null-variant unit.

**Delete policy:** `PROTECT`; close/deactivate the linked catalogue record instead of removing stock history.

### InventoryMovement

| Field | PostgreSQL / Django type | Null / default | Validation and ownership |
| --- | --- | --- | --- |
| `id` | `uuid` / `UUIDField` | PK; generated | Immutable movement identifier. |
| `store_id` | `uuid` FK → `Store.id` / `ForeignKey` | required | Must equal the stock unit and any order item store; `on_delete=PROTECT`. |
| `stock_unit_id` | `uuid` FK → `StockUnit.id` / `ForeignKey` | required | The only inventory subject changed; `on_delete=PROTECT`. |
| `order_item_id` | `uuid` FK → `OrderItem.id` / `ForeignKey` | nullable; default `NULL` | Required for order confirmation/cancellation/return movements; absent for opening/manual adjustments. |
| `reversal_of_id` | `uuid` self-FK → `InventoryMovement.id` / `ForeignKey` | nullable; default `NULL` | Required for cancellation/return restoration; points to the original confirmation deduction; `on_delete=PROTECT`. |
| `movement_type` | `varchar(32)` / `CharField(choices=...)` | required | One of `OPENING_BALANCE`, `MANUAL_ADJUSTMENT`, `ORDER_CONFIRMATION_DEDUCTION`, `ORDER_CANCELLATION_RESTORATION`, `ORDER_RETURN_RESTORATION`. |
| `quantity_delta` | `integer` / `IntegerField` | required | Nonzero whole units. Confirmation deduction is negative; opening/manual/restoration direction must agree with its declared type. |
| `operation_id` | `uuid` / `UUIDField` | required; server-generated | Idempotency identity for the triggering operation; do not accept it as a store authority. |
| `reason` | `varchar(240)` / `CharField` | nullable; default `NULL` | Required for `MANUAL_ADJUSTMENT`; otherwise optional concise operational reason. |
| `created_by_id` | `uuid` FK → `Account.id` / `ForeignKey` | required | Authenticated owner/staff member who initiated the operation; `on_delete=PROTECT`. |
| `occurred_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC committed event time. |

**Constraints:** `CHECK (quantity_delta <> 0)`; `UNIQUE (stock_unit_id, movement_type, operation_id)`; `UNIQUE (reversal_of_id) WHERE reversal_of_id IS NOT NULL`. A transaction locks the stock unit, validates available quantity, writes this immutable row, and updates `quantity_on_hand` together. This dictionary does not authorize an adjustment endpoint.

**Delete policy:** immutable and `PROTECT`; corrections are compensating movements, never row edits/deletions.

## 5. Customers, orders, and expenses

### Customer

| Field | PostgreSQL / Django type | Null / default | Validation and ownership |
| --- | --- | --- | --- |
| `id` | `uuid` / `UUIDField` | PK; generated | Customer identifier. |
| `store_id` | `uuid` FK → `Store.id` / `ForeignKey` | required | Server-scoped; `on_delete=PROTECT`. |
| `display_name` | `varchar(160)` / `CharField` | required | Trimmed non-blank seller-visible name/label. |
| `phone` | `varchar(32)` / `CharField` | nullable; default `NULL` | Optional trimmed contact value; no delivery/verification action is implied. |
| `email` | `varchar(254)` / `EmailField` | nullable; default `NULL` | Optional normalized email syntax; not globally or store-unique. |
| `created_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC creation time. |
| `updated_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC latest profile update time. |

**Constraints:** a customer belongs to one store. Same-store duplicate contacts are permitted; seller-side reconciliation is future work. No sensitive attributes, address, payment information, or social-platform identifier is part of this model.

**Delete policy:** do not cascade-delete orders. Deactivate/anonymize only through a later approved privacy workflow; ordinary delete is disallowed.

### SalesOrder

| Field | PostgreSQL / Django type | Null / default | Validation and ownership |
| --- | --- | --- | --- |
| `id` | `uuid` / `UUIDField` | PK; generated | Order identifier; API uses opaque `id`, not a guessable sequence. |
| `store_id` | `uuid` FK → `Store.id` / `ForeignKey` | required | Server-scoped tenant root; `on_delete=PROTECT`. |
| `customer_id` | `uuid` FK → `Customer.id` / `ForeignKey` | nullable; default `NULL` | If set, customer must be in the same store; `on_delete=PROTECT`. |
| `status` | `varchar(24)` / `CharField(choices=...)` | required; default `DRAFT` | `DRAFT`, `PENDING`, `CONFIRMED`, `PROCESSING`, `SHIPPED`, `DELIVERED`, `CANCELLED`, `RETURN_REQUESTED`, `RETURNED`, `REFUNDED`. API/UI display `PENDING` as `New`. |
| `currency_code` | `char(3)` / `CharField` | required; default `BDT` | Immutable BDT snapshot for this order. |
| `order_discount` | `numeric(12,2)` / `DecimalField` | required; default `0.00` | BDT; `>= 0.00` and `<=` sum of line gross before transition from `DRAFT`. |
| `seller_delivery_cost` | `numeric(12,2)` / `DecimalField` | nullable; default `NULL` | BDT; when recorded, `>= 0.00`. `NULL` is unknown and differs from explicit `0.00`. |
| `confirmed_at` | `timestamptz` / `DateTimeField` | nullable; default `NULL` | First successful confirmation time; immutable once set. |
| `delivered_at` | `timestamptz` / `DateTimeField` | nullable; default `NULL` | Original delivery time; never overwritten by later return/refund handling. |
| `cancelled_at` | `timestamptz` / `DateTimeField` | nullable; default `NULL` | Set once for an allowed cancellation. |
| `return_requested_at` | `timestamptz` / `DateTimeField` | nullable; default `NULL` | Set when an allowed return request is recorded. |
| `returned_at` | `timestamptz` / `DateTimeField` | nullable; default `NULL` | Set once for an accepted/received return. |
| `refunded_at` | `timestamptz` / `DateTimeField` | nullable; default `NULL` | Set once when the financial completion state is recorded. |
| `created_at` | `timestamptz` / `DateTimeField` | required; server-set | Draft creation time. |
| `updated_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC latest allowed update/transition time. |

**Constraints:** status transition validation follows the approved lifecycle; a confirmed-or-later order has one or more items; all related catalogue/customer/movement rows must be same-store. No payment status, payment amount, customer-paid delivery charge, tax calculation, or gateway reference is stored. Order gross/net totals are derived from item snapshots and `order_discount`, not separately writable fields.

**Delete policy:** no ordinary physical deletion after confirmation. A draft may be deleted only before it has an inventory movement; no confirmation/history cascade is allowed.

### OrderItem

| Field | PostgreSQL / Django type | Null / default | Validation and ownership |
| --- | --- | --- | --- |
| `id` | `uuid` / `UUIDField` | PK; generated | Immutable line-item identifier. |
| `order_id` | `uuid` FK → `SalesOrder.id` / `ForeignKey` | required | Parent order; `on_delete=PROTECT` once the order is not a deletable draft. |
| `product_id` | `uuid` FK → `Product.id` / `ForeignKey` | required | Same-store product reference retained for traceability; `on_delete=PROTECT`. |
| `variant_id` | `uuid` FK → `ProductVariant.id` / `ForeignKey` | nullable; default `NULL` | Required exactly when the product is variant-based; must belong to `product_id`; `on_delete=PROTECT`. |
| `product_name_snapshot` | `varchar(160)` / `CharField` | required | Captured from product when the line is fixed; never overwritten by catalogue edits. |
| `variant_name_snapshot` | `varchar(80)` / `CharField` | nullable; default `NULL` | Captured only for a selected variant; never overwritten by variant edits. |
| `quantity` | `integer` / `PositiveIntegerField` | required | Whole units, `>= 1`. |
| `selling_price_snapshot` | `numeric(12,2)` / `DecimalField` | required | BDT; `> 0.00`; captured when the line leaves draft. |
| `unit_cost_snapshot` | `numeric(12,2)` / `DecimalField` | nullable; default `NULL` | BDT; captured at confirmation; known value `>= 0.00`; `NULL` remains unknown. |
| `discount_allocation` | `numeric(12,2)` / `DecimalField` | required; default `0.00` | BDT; `>= 0.00`; all item allocations sum exactly to `SalesOrder.order_discount` using selected rounding. |
| `created_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC line creation time. |

**Constraints:** a product may appear in more than one line, but confirmation aggregates all demand for the same stock unit. Price/name snapshots are fixed on `DRAFT → PENDING`; cost snapshot is fixed on `PENDING → CONFIRMED`. Product/variant current values cannot rewrite these fields.

**Delete policy:** delete only with a deletable draft. Otherwise protect; history and movements remain intact.

### Expense

| Field | PostgreSQL / Django type | Null / default | Validation and ownership |
| --- | --- | --- | --- |
| `id` | `uuid` / `UUIDField` | PK; generated | Expense identifier. |
| `store_id` | `uuid` FK → `Store.id` / `ForeignKey` | required | Server-scoped; `on_delete=PROTECT`. |
| `description` | `varchar(240)` / `CharField` | required | Trimmed non-blank seller-entered description. |
| `category` | `varchar(80)` / `CharField` | required | Trimmed non-blank seller-entered category; no controlled taxonomy in this increment. |
| `amount` | `numeric(12,2)` / `DecimalField` | required | BDT; strictly greater than `0.00`. |
| `incurred_on` | `date` / `DateField` | required | Store-local business date; cannot be in the future for the prototype. |
| `recorded_by_id` | `uuid` FK → `Account.id` / `ForeignKey` | required | Authorized own-store owner/staff member; `on_delete=PROTECT`. |
| `created_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC recording time. |
| `updated_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC correction time before aggregate use. |

**Constraints:** delivery cost is not a general `Expense`; it belongs in `SalesOrder.seller_delivery_cost`. There is no order FK and no automatic allocation to orders/products. **[DECISION REQUIRED]** A controlled expense-category taxonomy, reporting treatment, and category-level analytics are not selected; this field is currently required free text only.

**Delete policy:** correct with a tracked update before reporting; do not ordinary-delete an expense already included in a saved analysis. A later reporting/audit task can add a correction ledger if required.

## 6. Analysis/AI provenance record

### AnalysisLog

| Field | PostgreSQL / Django type | Null / default | Validation and ownership |
| --- | --- | --- | --- |
| `id` | `uuid` / `UUIDField` | PK; generated | Tenant-scoped provenance identifier. |
| `store_id` | `uuid` FK → `Store.id` / `ForeignKey` | required | Authorized current store only; `on_delete=PROTECT`. |
| `requested_by_id` | `uuid` FK → `Account.id` / `ForeignKey` | required | Owner/active staff member who requested the computation; `on_delete=PROTECT`. |
| `feature` | `varchar(32)` / `CharField(choices=...)` | required | One of `CUSTOMER_ASSISTANT`, `BUSINESS_ADVISOR`, `CUSTOMER_SEGMENTATION`, `DEMAND_FORECAST`, `PROFIT_INTELLIGENCE`, `WHAT_IF_SIMULATOR`. |
| `outcome_state` | `varchar(16)` / `CharField(choices=...)` | required | One of `SUCCEEDED`, `UNAVAILABLE`, `BLOCKED`, `FAILED`; never use it to imply an unverified AI/business outcome. |
| `input_reference` | `varchar(160)` / `CharField` | required | Synthetic fixture/case ID or deterministic metric-snapshot reference; no raw prompt, message, customer contact, or secret. |
| `method_version` | `varchar(100)` / `CharField` | required | Deterministic algorithm/version or approved model identifier used for this run. |
| `provider_model` | `varchar(100)` / `CharField` | nullable; default `NULL` | Set only after a provider/model is approved; never store a key, endpoint credential, or account token. |
| `period_start` | `date` / `DateField` | nullable; default `NULL` | Required for period-based advisor/profit/forecast/segment requests; otherwise null. |
| `period_end` | `date` / `DateField` | nullable; default `NULL` | Required with `period_start`; must be on/after it. |
| `input_digest` | `char(64)` / `CharField` | nullable; default `NULL` | SHA-256 digest of approved minimized synthetic input where reproducibility needs an integrity check; never a substitute for an access-control decision. |
| `expires_at` | `timestamptz` / `DateTimeField` | required | `created_at + 30 days`; scheduled cleanup is a future implementation task. |
| `created_at` | `timestamptz` / `DateTimeField` | required; server-set | UTC request/computation time. |

**Constraints:** `CHECK ((period_start IS NULL AND period_end IS NULL) OR (period_start <= period_end))`. The log has no raw request/result text field. It records only the limited provenance required by FR-19; visible generated drafts/results, if later stored, need a separate privacy-reviewed entity and provider decision.

**Delete policy:** remove after `expires_at` through a future controlled cleanup process. Until then, protect it from ordinary cascade deletion and scope it to the authorized store.

**[DECISION REQUIRED] DP-02:** no external provider/model is selected or enabled. The nullable `provider_model` field preserves honest unavailable/blocked outcomes without inventing a provider integration.

## 7. Cross-record integrity matrix

| Relationship / rule | Enforcement required before persistence |
| --- | --- |
| Owner and staff exclusivity | Account cannot own a store and have a `StoreMembership`; `Store.owner_id` and `StoreMembership.account_id` are never client-authoritative. |
| Store consistency | Product, stock unit, customer, order, order item, movement, expense and analysis log links resolve to the same store in one transaction. |
| Variant consistency | `ProductVariant.product_id`, `StockUnit.product_id`/`variant_id`, and `OrderItem.product_id`/`variant_id` must agree. |
| Catalogue lifecycle | New order lines require active product and, if used, active variant. Existing transaction snapshots remain readable after deactivation. |
| Stock safety | Lock stock unit, require sufficient `quantity_on_hand`, write a nonduplicate movement, and update balance atomically. Never allow a negative balance. |
| Status effects | Confirmation sets the cost snapshot and one deduction; allowed cancellation/return restoration references that deduction exactly once. Delivery/reversal timestamps are never overwritten. |
| Discount arithmetic | Sum of `OrderItem.discount_allocation` equals `SalesOrder.order_discount`; discount cannot exceed line gross total. |
| Customer privacy | Customer link is optional, never cross-store, and contact values do not grant authentication or cause an external message. |
| Analysis minimization | Log reference/digest/version only; store scope before any retrieval; no secret/raw-message field and no automatic external action. |

## 8. ERD and API-contract alignment review

| Shared concern | Agreement |
| --- | --- |
| Entity set | All DB-01 entities are represented: Account, Store, StoreMembership, Product, ProductVariant, StockUnit, InventoryMovement, Customer, SalesOrder, OrderItem, Expense, AnalysisLog. |
| Logical vs physical IDs | `erd.md` entity-qualified logical names map to this document's UUID `id` fields and UUID FKs. API ID values remain opaque strings. |
| Optional links | `StockUnit.variant_id`, movement order/reversal links, `SalesOrder.customer_id`, `OrderItem.variant_id`, and `AnalysisLog.provider_model` are nullable exactly as described here. |
| Tenant scope | Direct `store_id` or inherited parent scope is required; API list/filter behavior must scope first, as the API contract requires. |
| API transport | Existing `/api/v1/` conventions, direct success resources, page-number list envelope, and error envelope remain unchanged. This dictionary registers fields only; it does not register routes or alter pagination/error shapes. |
| Money/dates | Existing API contract left resource money/date serialization open. DB-02 resolves the internal type and future JSON rule without claiming a live endpoint. |

## 9. DB-02 verification scope

This is documentation-only work. Review it structurally before schema implementation:

1. Every DB-01 entity has an `id`, store ownership path, field type, nullable/default rule, validation, and delete behavior.
2. Required proposal operations map to Product/StockUnit/Movement, Customer/Order/Item, Expense, and AnalysisLog without adding excluded integrations.
3. The logical ERD uses the same entities/relations, and the API contract remains transport-only with opaque string IDs.
4. No field stores provider secrets, raw real-customer data, payment-gateway data, social-platform credentials, autonomous-action instructions, or fabricated AI/ML results.

Future work: DB-03 can convert this design into Django models and migrations, with database constraints plus transactional service validation for the cross-table rules that PostgreSQL FKs cannot express alone.
