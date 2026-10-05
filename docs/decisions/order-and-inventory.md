# SellerOS Order, Revenue, Refund, and Inventory Rules

## 1. Purpose

PLAN-03 decision record, 5 October 2026. Establish deterministic order, revenue, refund and inventory conventions for later ORDER, INV, ANALYTICS, PROFIT, DASH, ADVISOR, FORECAST and SIM tasks. This is documentation only: no models, APIs, services, transactions, migrations, screens or executable tests are implemented.

Authority: the user's PLAN-03 approved prototype policies; [PLAN-02 scope](../requirements/scope.md), [proposal traceability](../requirements/traceability.csv), and [PLAN-02 evidence](../requirements/plan-02-evidence.md). Proposal FR-06 remains preserved. The policy supplied in this chat is the source for the rules below; approval means a user-supplied working project rule, not evidence of instructor review.

## 2. Scope

Standalone seller-entered records, deterministic management analytics and explainable decision support. Retain the approved React/Vite/TypeScript, Tailwind/shadcn, TanStack Query/Recharts, Python/Django/DRF/Django ORM, PostgreSQL and Pandas/NumPy/Scikit-learn architecture. XGBoost is conditional; backend LLM selection/privacy is a separate decision. Use synthetic or otherwise authorized data. All protected actions require authorized same-store access; detailed roles await PLAN-04.

Preserve existing `check.py`, source documents and PLAN-02 files. No order/inventory implementation or existing decision directory was found at inspection. The branch was `main` and the working tree was clean, unlike the earlier PLAN-02 session where documents were untracked. Current Git state takes precedence over that historical evidence.

## 3. Working Prototype Decisions

**APPROVED WORKING PROTOTYPE RULE:** recognize completed sales on actual delivery; deduct stock once on confirmation; restore once on qualifying cancellation or accepted return; preserve transaction snapshots; keep missing costs visible; use order-level discounts; separate delivery and general expenses; prevent negative stock; apply all effects atomically and idempotently.

**[DECISION REQUIRED] DR-01 — New versus PENDING.** PLAN-02 and proposal FR-06 require New, Confirmed, Processing, Shipped and Delivered. The supplied policy uses PENDING instead of New. Preserve New as an approved requirement and the supplied PENDING behavior as a proposed mapping; do not silently rename, add a NEW transition, or assume equivalence. Approve either `PENDING` with display label New, or a written FR-06 amendment before status schema/API implementation. Other supplied statuses extend the lifecycle without removing the four shared statuses.

Rules not affected by a listed conflict are approved working rules. A listed conflict/gap blocks only dependent behavior; it does not authorize guessing or invalidate unrelated rules. See section 22 for all remaining decisions.

## 4. Order Statuses

| Supplied status | Meaning | Completed-sale revenue / COGS | Inventory effect on entry |
| --- | --- | --- | --- |
| DRAFT | Preparation, not finalized | None / none | None |
| PENDING | Submitted, not confirmed; naming subject to DR-01 | None / none | None; no reservation |
| CONFIRMED | Seller accepts | None recognized; cost snapshot associated | Deduct entire ordered quantity once, atomically |
| PROCESSING | Preparation for dispatch | None recognized | None additional; prior deduction remains |
| SHIPPED | Dispatched | None recognized | None additional |
| DELIVERED | Customer actually received order | Recognize sale and snapshot-based COGS once | None |
| CANCELLED | Will not be fulfilled | No completed-sale revenue/COGS | Restore prior deduction once, if any |
| RETURN_REQUESTED | Requested, not accepted/received | Retain prior recognized sale/COGS only if actually delivered; no new recognition | None |
| RETURNED | Seller received/accepted returned goods | Reverse previously recognized affected revenue/COGS once; none to reverse if never delivered | Restore accepted previously deducted quantity once |
| REFUNDED | Financial completion for applicable amount | Reflect existing reversal; no repeated subtraction or COGS reversal | None additional |

Confirmed cost association is not recognition of completed-sale COGS. A status alone cannot prove an earlier delivery: history matters, particularly after a shipped return request. Missing snapshot cost remains unknown, not zero. The current full-order return boundary applies; references to affected quantities do not authorize partial returns.

## 5. Allowed Status Transitions

The supplied directed state machine contains exactly these 14 edges:

```text
DRAFT -> PENDING
DRAFT -> CANCELLED
PENDING -> CONFIRMED
PENDING -> CANCELLED
CONFIRMED -> PROCESSING
CONFIRMED -> CANCELLED
PROCESSING -> SHIPPED
PROCESSING -> CANCELLED
SHIPPED -> DELIVERED
SHIPPED -> RETURN_REQUESTED
DELIVERED -> RETURN_REQUESTED
RETURN_REQUESTED -> RETURNED
RETURN_REQUESTED -> DELIVERED
RETURNED -> REFUNDED
```

Every unlisted edge is rejected. CANCELLED and REFUNDED are terminal in this machine. A repeated request is an idempotent retry, not permission for a self-transition with repeated effects. Replaying a historical operation after the order has progressed must not move it backward.

**[DECISION REQUIRED] DR-02:** `SHIPPED -> RETURN_REQUESTED -> DELIVERED` could falsely recognize delivery if a pre-delivery request is merely rejected. For a previously delivered order, returning to DELIVERED retains the original delivery event without recognizing it twice. For a shipped-origin request, require a decision defining actual-delivery evidence versus rejection/resumption and whether SHIPPED resumption needs an explicit edge. Do not treat rejection as proof of delivery.

Examples rejected: DRAFT -> DELIVERED; PENDING -> SHIPPED or DELIVERED; CANCELLED -> CONFIRMED; DELIVERED -> CANCELLED; REFUNDED -> DELIVERED or CONFIRMED; SHIPPED -> CANCELLED. No arbitrary jumps or incompatible backward moves.

## 6. Revenue Recognition

**APPROVED WORKING PROTOTYPE RULE:** the actual DELIVERED event is the completed-sale recognition event. Payment receipt does not recognize revenue. This is a product analytics convention, not formal accounting advice.

DRAFT/PENDING/CONFIRMED/PROCESSING/SHIPPED/CANCELLED recognize no completed-sale revenue. RETURN_REQUESTED makes no reversal and retains only an already-delivered sale. RETURNED reverses the applicable recognized merchandise net amount once; REFUNDED records financial completion without another reversal. A shipped return that never reached actual delivery has zero recognized revenue and zero completed-sale COGS to reverse.

Separate original delivery and reversal history so current status filtering cannot erase or duplicate a historical sale. Partial reversal is OUT OF SCOPE for the first implementation unless separately approved.

## 7. Gross Sales, Discount, and Net Sales

**APPROVED WORKING PROTOTYPE RULE:**

```text
line_gross = quantity * selling_price_snapshot
order_gross = sum(eligible line_gross)
0 <= order_discount <= order_gross
net_sales_before_refunds = order_gross - order_discount
line_discount = order_discount * line_gross / order_gross
line_net = line_gross - line_discount
```

Discount is order-level and stored separately from gross and net. Allocate proportionally only when line-level profit/reversal needs it. Use Decimal-safe arithmetic; no floating-point financial calculations. Do not divide by zero for an empty/zero-gross order. Line allocations must sum to the recorded order discount and line net amounts to the recorded order net.

**[DECISION REQUIRED] DR-04:** currency, Decimal precision, rounding mode and allocation remainder/tie-breaking method remain unapproved. Do not choose cents, a currency, or a rounding rule from the developer's locale. Zero-gross orders need the price decision in DR-05.

Illustrative synthetic arithmetic, not a currency or rounding decision: gross lines 60 and 40, discount 10 => allocations 6 and 4, net lines 54 and 36, order net 90. An accepted full return reverses 90 recognized merchandise revenue exactly once, not 100 and not another 90 when marked REFUNDED.

## 8. Cancellation Rules

**APPROVED WORKING PROTOTYPE RULE:** cancellation follows only DRAFT/PENDING/CONFIRMED/PROCESSING -> CANCELLED. “Before delivery” does not expand this whitelist to SHIPPED cancellation. DRAFT/PENDING cancellation has no stock effect. CONFIRMED/PROCESSING cancellation restores the quantity previously deducted exactly once and excludes completed-sale revenue/COGS. After shipment use the return workflow; after delivery never use cancellation.

Repeated cancellation cannot restore stock twice. Any cancellation refund must stay within its approved eligible amount, create no revenue, and reverse no completed-sale revenue that was never recognized.

**[DECISION REQUIRED] DR-03:** the supplied refund rule associates refunds with cancellation after deduction, but there is no CANCELLED -> REFUNDED edge, payment convention or cancellation-refund cap for never-recognized sales. Preserve the terminal CANCELLED state. Decide how to record cancellation financial completion and establish its amount/eligibility separately from recognized-sales reversal. No payment gateway or new transition is inferred.

## 9. Return and Refund Rules

**APPROVED WORKING PROTOTYPE RULE:** returns apply only after shipment/delivery. SHIPPED or DELIVERED -> RETURN_REQUESTED -> RETURNED -> REFUNDED. Requested alone has no stock/revenue/COGS reversal. Acceptance/receipt at RETURNED restores the previously deducted accepted goods and reverses previously recognized affected revenue and snapshot COGS once. Record the approved refund amount/liability; REFUNDED records completion without repeating economic effects.

Refunds must not create revenue, exceed eligible recognized sales for a sale reversal, restore stock twice, or duplicate reversal under retries. Cancellation eligibility is subject to DR-03. No partial item cancellation, partial quantity return, or partial refund is authorized for the first prototype; any such extension requires a separate rule/task.

**[DECISION REQUIRED] DR-06:** a full return reverses the returned merchandise net revenue, while the supplied wording also says refunded amount is removed from net revenue. These agree when refund equals that reversed amount. Define eligibility and treatment if the approved refund differs, includes non-merchandise charges, or no payment occurred. Until decided, do not silently subtract both return value and cash refund, invent a full-refund amount, or infer delivery-cost reimbursement. Handling damaged/non-resellable goods also needs a decision before inventory restoration can distinguish them; the supplied working baseline restores accepted quantity.

## 10. Inventory Deduction and Restoration

**APPROVED WORKING PROTOTYPE RULE:** deduct exactly once at CONFIRMED. Available stock must cover every requested quantity; no negative inventory, partial confirmation, or partial deduction. Subsequent PROCESSING/SHIPPED/DELIVERED has no additional deduction.

Restore exactly once on cancellation after deduction or receipt/acceptance at RETURNED. DRAFT/PENDING cancellation restores nothing. RETURN_REQUESTED restores nothing. REFUNDED restores nothing additional. Total restored quantity cannot exceed prior deducted quantity. Inventory movements must reference the relevant order/order item, and restoration must be traceable to its original deduction; the storage mechanism is a later design task, not a model choice here. No reservation is introduced.

For multiple lines/products, confirmation is all-or-nothing. If multiple lines refer to the same stock unit, compare their combined demand with availability so separate checks cannot oversell. Product/variant stock identity remains subject to PLAN-02 D-08.

## 11. Atomicity and Idempotency

**APPROVED WORKING PROTOTYPE RULE:** status change, snapshots and associated deduction/restoration/reversal must succeed together or have no effect. Failure must leave status, stock and related business records at their pre-operation state; never silently save a partial inconsistent result.

Later ORDER-03 must use a database transaction for confirmation and prove rollback through failure testing. Concurrent confirmations must serialize or otherwise enforce the available-stock invariant in PostgreSQL. Exactly-once business effects must survive duplicate requests and retries, including after a successful operation with a lost response. Later tasks must select the concurrency and operation-identity design; no Django service or lock code is implemented here. Invalid transitions and unauthorized/cross-store actions have no side effects. Same-store checks apply to all linked products, stock, customers and order/reversal records.

## 12. Cost Snapshot / COGS Rules

**APPROVED WORKING PROTOTYPE RULE:** capture transaction-time unit product cost at confirmation per item; recognized COGS uses that snapshot at delivery, and accepted returns reverse the same snapshot-based amount. Product master cost changes never rewrite historical order costs. Capture association at confirmation, recognition at delivery: these are distinct events.

Missing cost stays unknown and visible; never assume zero. A known zero cost must be distinguished from missing. A missing cost does not permit a complete profit claim. How to present incomplete totals is deferred to PROFIT tasks; no fabricated margin or cost imputation.

## 13. Delivery Cost and Other Expenses

**APPROVED WORKING PROTOTYPE RULE:** seller-paid delivery cost is a separate input, not product selling price and not silently mixed into revenue. Explicit zero differs from absent/not recorded. It may contribute separately to profit analysis. Marketing, packaging, platform fees, utilities and other general costs remain Expense records. Do not arbitrarily allocate them to individual orders.

**[DECISION REQUIRED] DR-06/DR-08:** customer-paid delivery charges, refundability/recovery of delivery costs, order-specific versus general packaging categorization, and exact period-expense aggregation need written rules before affected financial calculations. Returning goods does not imply the original seller-paid courier expense disappeared. Prevent double counting a cost as both order delivery and a general expense.

## 14. Date and Timezone Rules

**APPROVED WORKING PROTOTYPE RULE:** use the original actual-delivery timestamp as the default completed-sale date. Retain cancellation dates for operational analysis, never as sale dates. Preserve original delivery and separate return/refund event dates. Use the configured store timezone for user-visible grouping; do not silently mix UTC/local dates.

**[DECISION REQUIRED] DR-07:** select the temporary project timezone if stores do not yet have one. The chat timezone is not automatically a business timezone. Define reversal-period reporting (event-period adjustment versus restated delivery period), date-range boundary semantics and timestamp handling before analytics contracts. Neither rerouting to DELIVERED nor a retry may replace the original delivery timestamp.

## 15. Historical Snapshot Rules

**APPROVED WORKING PROTOTYPE RULE:** later order items must preserve product reference, product/variant identity, name where needed for historical display, quantity, selling-price snapshot, confirmation-time cost snapshot and applicable discount allocation. Current name, price, cost or SKU/variant changes must not rewrite transaction calculations or history.

**[DECISION REQUIRED] DR-08:** specify when selling price/identity snapshots become fixed (draft, submission or confirmation), what edits are allowed before/after confirmation, and how subsequent approved corrections are recorded. Only cost capture at confirmation is explicitly fixed by this baseline. Snapshot preservation must also survive the later product deactivation/archive policy; do not invent deletion semantics.

## 16. Analytics Inclusion Rules

**APPROVED WORKING PROTOTYPE RULE:** include actual DELIVERED sales; apply accepted-return/refund reversal once to eligible previously recognized values. Exclude DRAFT/PENDING/CONFIRMED/PROCESSING/SHIPPED/CANCELLED from completed-sale revenue. RETURN_REQUESTED retains an original delivered sale until acceptance, but a shipped-origin request has no delivered sale to include. RETURNED/REFUNDED retain traceable sale/reversal history and final adjusted net values, rather than disappearing under current-status filtering.

Dashboard, profit, advisor, forecast and simulator must share these eligibility rules. They must not create their own status definitions. Forecast demand series must use eligible sale history; exact return quantity/date-series handling belongs to PLAN-05 with DR-07 resolved. Incomplete costs affect profit completeness, not whether actual delivery occurred. Operational counts of pending/cancelled orders are separately labeled, not completed sales.

## 17. Profit Analysis Boundary

**APPROVED WORKING PROTOTYPE RULE:** management-analysis estimate, not formal accounting profit or tax advice:

```text
estimated_operating_profit = net_sales - COGS - seller_delivery_cost
                            - applicable_recorded_operating_expenses
```

The pasted conceptual list rendered costs as bullets; the intended deduction relationship is made explicit here, consistent with its cost inputs. Exact order/product/period aggregation, expense scope and completeness contract remain for PROFIT tasks. No unsupported general-expense allocation; no unknown cost converted to zero; no repeated revenue/COGS reversal. Cancellation contributes no completed-sale profit, but treatment of any incurred non-sale expenses must be resolved, not erased by a status filter. LLMs may explain verified metrics but cannot supply arithmetic results.

## 18. Edge Cases

| ID | Case | Expected behavior |
| --- | --- | --- |
| E-01 | Insufficient stock at confirmation | Reject entire operation; unchanged status/stock; no negative quantity |
| E-02 | Duplicate confirmation | No additional deduction/snapshot rewrite; no backward status change |
| E-03 | Duplicate cancellation | No second restoration |
| E-04 | Duplicate accepted return | No second restoration or revenue/COGS reversal |
| E-05 | Duplicate refund | No second financial completion/reversal/restoration |
| E-06 | Cancel after deduction | Allowed only CONFIRMED/PROCESSING; restore once; no sale |
| E-07 | Return after delivery | Request unchanged; acceptance restores/reverses once; refund completes only |
| E-08 | Invalid status jump | Reject, no business effects |
| E-09 | Master price changes after transaction | Preserve historical selling-price snapshot; freeze timing DR-08 |
| E-10 | Master cost changes after confirmation | Preserve confirmation cost snapshot |
| E-11 | Missing cost | Remains unknown; display incomplete profit data |
| E-12 | Zero quantity | Reject finalized confirmation; require positive quantities |
| E-13 | Negative quantity | Reject; cannot increase stock through negative deduction |
| E-14 | Zero/negative price | Negative incompatible with nonnegative gross/net; reject; zero-price eligibility DR-05 |
| E-15 | Discount exceeds gross | Reject; no negative net sales |
| E-16 | Refund exceeds eligible amount | Reject; cancellation eligibility DR-03 and amount rules DR-06 |
| E-17 | Multiple lines | Validate/confirm atomically; proportional discounts; repeated stock identity aggregated |
| E-18 | Multiple products | Check all quantities; any unavailable product fails entire operation |
| E-19 | Empty order | Cannot confirm/deliver; whether an empty preparation draft is allowed DR-05 |
| E-20 | Concurrent confirmations | At most available stock committed; no negative inventory |
| E-21 | Database failure at confirmation | Roll back order status, snapshots and stock effects together |
| E-22 | Failure during cancellation/restoration | Roll back all effects; retry may restore once after success |
| E-23 | Timezone/date boundary | Group by approved store timezone; no mixed bases; DR-07 blocks fallback choice |
| E-24 | Return requested, not accepted | No restoration/reversal; retain only an original delivered sale |
| E-25 | Shipped cancellation request | Reject CANCELLED transition; use return workflow |
| E-26 | Return before actual delivery | Restore on acceptance; no completed revenue/COGS to reverse |
| E-27 | Reject shipped-origin return request | DR-02: do not fabricate delivery; dependent path blocked |
| E-28 | Cancellation financial refund | DR-03: no completed-sale reversal; recording/cap require decision |
| E-29 | Missing versus explicit zero delivery cost | Distinguish and disclose; never impute missing as zero |
| E-30 | Cross-store or unauthorized linked data | Deny without status/stock/financial effects |
| E-31 | Partial cancellation/return/refund | Out of scope; reject unsupported operation |
| E-32 | Refund differs from returned net value | DR-06; do not double-subtract or choose adjustment policy |

Positive quantities and nonempty confirmed orders follow the supplied available-stock and no-partial-deduction invariants. Whether fractional quantities or free products are supported is explicitly open, not an implicit unit/price policy.

## 19. Future Implementation Test Matrix

These are specifications only. No executable tests or results are claimed. Planned locations: order/inventory service tests under `backend/apps/orders/tests/` and `backend/apps/inventory/tests/`, analytics/profit tests under their future modules, UI review under `frontend/src/features/orders/`, and recorded results under `docs/evidence/`. Paths may be adapted after setup while retaining cases.

| ID | Scenario and synthetic setup | Expected assertion | Later owner task / dependency |
| --- | --- | --- | --- |
| T-01 | PENDING order quantity 2, stock 5; confirm | CONFIRMED and stock 3, one deduction | ORDER/INV; DR-01 |
| T-02 | Quantity 6, stock 5; confirm | Reject, PENDING and stock 5 unchanged | ORDER/INV; DR-01 |
| T-03 | Inject failure after stock write before confirmation commit | Entire status/snapshot/stock rollback | ORDER/INV |
| T-04 | Cancel confirmed quantity 2 with prior deduction | CANCELLED; restore 2 once; no completed-sale COGS/revenue | ORDER/INV |
| T-05 | Repeat successful cancellation | Stock unchanged on retry | ORDER/INV |
| T-06 | Actually deliver shipped eligible order | Recognize snapshot net revenue/COGS once; original delivery date | ORDER/ANALYTICS |
| T-07 | Mix cancelled and delivered orders | Completed-sale totals exclude cancelled | ANALYTICS/PROFIT |
| T-08 | Accept full delivered return for net 90 | Reverse 90 once; retain original sale history | ORDER/ANALYTICS; DR-06 |
| T-09 | Accept full return quantity 2 | Restore 2 exactly once | ORDER/INV |
| T-10 | Repeat accepted-return operation | No additional stock or revenue/COGS effect | ORDER/INV/ANALYTICS |
| T-11 | Change current product price after transaction | Historical net revenue unchanged | ORDER; DR-08 |
| T-12 | Change master cost after confirmation | Delivery/reversal use original cost | ORDER/PROFIT |
| T-13 | Missing cost fixture | Unknown visible; no fabricated complete profit | PROFIT |
| T-14 | Enumerate all source/target status pairs | Exactly section 5 whitelist; all others reject; DR-02 path remains blocked pending decision | ORDER; DR-01/02 |
| T-15 | Discount greater than gross or negative | Validation error; unchanged records, never negative net | ORDER |
| T-16 | Refund exceeds eligible recognized amount | Reject, no effects | ORDER; DR-03/06 |
| T-17 | Two simultaneous quantity-2 confirmations, stock 3 | One commits, one fails; final stock 1 | ORDER/INV |
| T-18 | Foreign-store order/product/customer or unauthenticated request | Denied; no mutation | AUTH/ORDER/INV; PLAN-04 |
| T-19 | Retry successful refund after lost response | One completion; no repeated reversal/restoration | ORDER; DR-06 |
| T-20 | Delivered return request remains unaccepted | Original revenue/COGS retained; stock unchanged | ORDER/ANALYTICS |
| T-21 | Shipped return accepted before delivery | Restore once; zero completed revenue/COGS reversal | ORDER/INV |
| T-22 | Two lines gross 60/40, discount 10 | Allocations 6/4, net 54/36, total 90 | ORDER/PROFIT; DR-04 for general rounding |
| T-23 | Multiple products, one insufficient; or repeated same product lines | All-or-nothing; combined stock demand checked | ORDER/INV |
| T-24 | Inject failure during cancellation restoration | Entire rollback; later retry restores once | ORDER/INV |
| T-25 | Delivered at timezone boundary, return next period | Approved grouping and reversal-period contract, preserved event dates | ANALYTICS; DR-07 |
| T-26 | DRAFT/PENDING cancellation; shipped cancellation attempt | No stock restoration for undeducted order; shipped cancellation denied | ORDER/INV |
| T-27 | Empty, zero/negative quantity, zero/negative price fixtures | Apply section 18; no silent free-product/empty-draft policy | ORDER; DR-05 |
| T-28 | Missing vs zero delivery cost; general expense fixture | Visible completeness; no invented per-order allocation/double counting | PROFIT; DR-08 |
| T-29 | Cancelled refund or mismatched return/refund amount | Follow written resolution; no unrecognized revenue reversal | ORDER/PROFIT; DR-03/06 |
| T-30 | Dashboard/advisor/forecast/simulator consume same sale fixture | Shared eligibility; no independent status invention | ANALYTICS/DASH/ADVISOR/FORECAST/SIM; PLAN-05 |

## 20. Out of Scope

No Django models, serializers, APIs, services, migrations, frontend, payment/refund gateway, courier/social integrations, automatic messaging, formal accounting/tax calculations, complex partial refunds, autonomous actions, live customer data, LLM integration, forecasting/ML or simulator implementation. No stock reservation. No executable future tests. No unrelated file modifications or automatic commit.

## 21. Dependencies for ORDER-01 onward

Before later implementation: resolve DR-01 before status contracts; DR-02 before the shipped-request rejection path; DR-03/06 before refund contracts; DR-04 before monetary allocations; DR-05 before quantity/price validation; DR-07 before date aggregation; DR-08 before edit/snapshot/expense contracts. Continue PLAN-04 for store access, PLAN-05 for analytic/forecast/scenario contracts, PLAN-06 for data/provider policy. Complete required setup, schema/API, authentication and product/inventory foundations per Master Plan before ORDER tasks. This document is no authorization to skip prerequisites.

PLAN-02 D-01 is substantially specified but remains blocked for DR-01/02/03/06. D-02 is partly specified: discount level, delivery separation, missing-cost visibility, cost snapshot and delivery recognition date are fixed; currency, rounding, timezone and exact profit aggregation remain open. Other PLAN-02 decisions remain unchanged. The register/source files are preserved; a later authorized traceability update can link these resolutions without claiming implemented tests.

## 22. Instructor/Team Review Notes

| Decision | Required review, no inferred answer |
| --- | --- |
| DR-01 | Resolve required New label versus supplied PENDING; preserve FR-06 until approved amendment/mapping |
| DR-02 | Define rejection/resumption of shipped-origin return requests without fabricated delivery |
| DR-03 | Define cancellation refund eligibility, cap and completion record with terminal CANCELLED and no recognized sale |
| DR-04 | Currency, precision, rounding and proportional-allocation residuals |
| DR-05 | Free/zero-price products, empty drafts, integer versus fractional quantities, negative-cost validation |
| DR-06 | Full return refund amount, non-merchandise components, no-payment cases, damaged goods, nonrecoverable delivery expense |
| DR-07 | Fallback business timezone, timestamp/range conventions and reversal reporting period |
| DR-08 | Selling-price/identity freeze timing, permitted edits/corrections, expense categorization/aggregation and historical references |

No instructor review or contributor credit is inferred. The ordinary path is deterministic; the listed dependent cases remain **[DECISION REQUIRED]**. Do not describe the entire lifecycle as implementation-ready while these are open. Next task is **PLAN-04**, not ORDER-01 or SETUP-01.

### Documentation verification

Inspection commands: `git status --short --branch`, `git branch --show-current`, `rg --files --hidden -g '!.git'`, `Get-Content docs/requirements/scope.md`, `Get-Content docs/requirements/plan-02-evidence.md`, `Import-Csv docs/requirements/traceability.csv` (selected related requirements), `Test-Path docs/decisions`, `git log -3 --oneline`. All were read-only. Results: initial branch main and clean tree; no existing decision directory; PLAN-02 is present in commit `44646c2`; FR-06 explicitly requires New. No application code besides the print script was present.

PowerShell structural assertions using `Get-Content -Raw` and `[regex]::Matches` passed: 22 numbered sections, 10 supplied status rows, 14 whitelisted transition lines, 32 edge cases, 30 planned tests and DR-01–DR-08 references. Manual consistency review verified confirmation versus recognition timing, shipped-origin returns, return/refund non-duplication, cancellation limits, immutable costs, and explicit decision gates. This is document validation, not executed future behavior.

Final review commands: `git status`, `git diff --stat`, `git diff`, `git diff --no-index --stat -- NUL docs/decisions/order-and-inventory.md`, `git diff --no-index --check -- NUL docs/decisions/order-and-inventory.md`, and `git diff --no-index -- NUL docs/decisions/order-and-inventory.md`. Tracked diffs were empty; the new untracked document was reviewed via no-index diff. No whitespace-error diagnostics; Git warned that LF may become CRLF. No-index comparisons report exit 1 for the added-file difference, not an application failure. At final inspection the branch was `docs`; the agent did not run a checkout/switch or commit. Only this new file was untracked. No application tests were run because this is a document-only change.
