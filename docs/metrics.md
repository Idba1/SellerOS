# SellerOS sales metric contract — ANALYTICS-01

This is the shared definition for future dashboard sales metrics. It defines the meaning and eligibility of figures; it does not create an analytics endpoint, dashboard query, period lock, return workflow, profit calculation, or forecast. All monetary examples are synthetic and are not seller performance evidence.

## 1. Scope and authoritative record facts

All metric queries must begin with the authorized store context. They use only that store's `SalesOrder`, immutable `OrderItem` snapshots, and `OrderStatusEvent` history. A current `SalesOrder.status` alone is not sufficient for historical sales metrics: a returned/refunded order may have had a prior delivery, while a shipped-origin return request may never have been delivered.

The prototype currency is BDT. Monetary arithmetic uses persisted `Decimal` values; no float conversion, product's current price/cost, or inferred missing value is permitted. Seller-paid delivery cost, general expenses, COGS, margin, tax, payment receipt, and forecasts are outside this sales-metric contract.

## 2. Date basis and period inclusion

The completed-sale date is the original `OrderStatusEvent` whose `to_status` is `DELIVERED`. Its event timestamp is converted to the order's configured `Store.timezone` before it is shown or compared with a user-selected calendar date. The matching `SalesOrder.delivered_at` is a convenience field; historical event evidence is the source of truth if the values differ.

For a future date-range request, a delivered event belongs to a selected local calendar date when its converted local date equals that date. The hand-calculable examples below treat their written calendar ranges as inclusive; this is not a selected production query-boundary rule. No dashboard/API range parameter is introduced by this task.

**[DECISION REQUIRED] DR-07:** exact timestamp boundary format, default dashboard range, bucket size (day/week/month), and return/reversal-period policy are not approved. A future implementation must carry the requested local date range, store timezone, cutoff/as-of time, and selected grouping in its response; it must not substitute UTC dates or the viewer's browser timezone.

## 3. Eligible records and status treatment

| Lifecycle evidence | Completed-sale base metrics | Reason |
| --- | --- | --- |
| Original `DELIVERED` event | Include once on its original delivery date. | Delivery is the approved recognition event. |
| `DRAFT`, `PENDING`, `CONFIRMED`, `PROCESSING`, `SHIPPED`, `CANCELLED` without a delivery event | Exclude. | None is a completed sale. |
| `RETURN_REQUESTED` after an original delivery | Retain in **base delivered** metrics; no reversal yet. | A request alone has no economic reversal. |
| `RETURNED` or `REFUNDED` after delivery | Keep delivery evidence visible; do not remove the row by current-status filtering. | A later reversal must be applied exactly once under an approved reversal contract. |
| Shipped-origin return request with no delivery event | Exclude. | A return request is not proof of actual delivery. |

The current order-status implementation does not yet execute cancellation-after-deduction, accepted-return, or refund effects. A future analytics implementation must therefore fail closed rather than calculate return-adjusted figures from incomplete status history.

## 4. Defined base metrics

All metrics below are scoped to one authorized store and a selected period of eligible original delivery events.

| Metric | Formula | Availability and limit |
| --- | --- | --- |
| `delivered_order_count` | Count distinct orders with one eligible original delivery event. | Available only when event history is complete for the selected period. |
| `delivered_units` | Sum `OrderItem.quantity` for eligible delivered orders. | Uses immutable order-line quantity, not current inventory. |
| `delivered_gross_sales` | Sum `quantity × selling_price_snapshot` for eligible delivered items. | Before order discounts and reversals. |
| `delivered_order_discounts` | Sum `SalesOrder.order_discount` once per eligible delivered order. | Discount is order-level; this metric does not allocate it to products. |
| `delivered_net_sales_before_reversals` | `delivered_gross_sales − delivered_order_discounts`. | Base delivered sales only; not a retained-sales or profit claim. |
| `retained_net_sales` | Base delivered net less one eligible accepted-return/refund adjustment. | **Unavailable** until DR-06/DR-07 define reversal amount and period attribution. |
| `average_order_value` | Candidate: delivered net / completed-order denominator. | **Unavailable** until AC-01 fixes denominator and return treatment. |

`OrderItem.unit_cost_snapshot = NULL` does not block the base sales metrics; it blocks a complete COGS/profit/margin claim. A known zero cost remains distinct from unknown cost. Product edits, deactivation, or current selling price/cost never rewrite the snapshot-based calculation.

**[DECISION REQUIRED] DR-04:** metric aggregation must use the approved persisted decimal rounding rule once it is finalized. No new aggregate rounding, discount-allocation remainder, or display precision is selected here.

## 5. Return and refund boundary

The metric contract keeps two different concepts visible:

1. **Base delivered sales** are calculated from original delivery events and remain auditable after a later return.
2. **Retained/adjusted sales** require the accepted reversal amount, exactly-once reversal identity, and an approved decision for whether the adjustment appears in the original delivery period or the return event period.

Until those rules and implementation exist, a period containing returned/refunded records may show base delivered figures with an explicit `return_adjustment_status: decision_required`; it must not silently show zero, subtract both a return and a refund, or treat a return request as a completed reversal.

**[DECISION REQUIRED] DR-06 / AC-01:** confirm the eligible return/refund amount, fully returned-order count treatment, and retained-unit/order semantics. **[DECISION REQUIRED] DR-07:** choose event-period adjustment versus restating the original delivery period.

## 6. Empty, incomplete, and invalid periods

| State | Allowed presentation |
| --- | --- |
| Declared complete coverage; no eligible delivery events | `delivered_order_count = 0`, `delivered_units = 0`, and monetary base metrics `0.00`, visibly labeled complete/empty. |
| Coverage/import/event history absent or incomplete | `unavailable`, with the missing condition; never present zero as known performance. |
| Events exist but return-adjusted rule is unresolved | Base delivered figures may be shown with a decision-blocked adjusted metric. |
| Invalid cross-store link, duplicate delivery evidence, missing snapshot, or inconsistent event ordering | `invalid_data`; do not calculate a successful metric. |

Current records do not store a universal ingestion-coverage flag, so a future API cannot claim a period is complete merely because a query returns zero rows. The selected cutoff/as-of timestamp and data-completeness source must be included before live dashboard metrics are released.

## 7. Hand-calculable synthetic examples

These examples reference `data/sample/synthetic-orders-expenses-timeseries.v1.json`; they are contract checks, not dashboard output.

| Store/local period | Eligible fixture deliveries | Hand calculation | Expected base result |
| --- | --- | --- | --- |
| Store A, 2026-01-01 through 2026-02-28 | `order-a-delivered-normal` (2 × BDT 850.00) and `order-a-delivered-missing-cost` (1 × BDT 390.00) | gross = 1,700.00 + 390.00; discounts = 0.00; net before reversals = 2,090.00 − 0.00 | 2 orders; 3 units; gross BDT 2,090.00; net-before-reversals BDT 2,090.00. |
| Store A, March 2026 | `order-a-delivered-returned` originally delivers 1 × BDT 1,200.00 and later returns | Base delivered gross/net-before-reversals = 1,200.00; return-adjusted retained net is blocked. | 1 base delivered order; 1 unit; BDT 1,200.00 base net; adjusted metric unavailable pending DR-06/DR-07. |
| Store B, 2025-10-01 through 2025-10-31 | `order-b-delivered-sparse` (1 × BDT 760.00) | gross = 760.00; discount = 0.00 | 1 order; 1 unit; gross/net-before-reversals BDT 760.00. |
| Any declared-complete period with no eligible events | none | Sum over empty complete set | 0 orders; 0 units; BDT 0.00 base figures. |

The missing-cost example is valid for sales totals but not evidence of complete profit. The returned fixture proves that base delivery and final adjusted values are different concepts; it does not authorize a live return-adjusted dashboard number.

## 8. Verification and implementation gate

`backend/tests/test_metrics_contract.py` recomputes the first example from the reviewed manifest and verifies the BDT 2,090.00 / 3-unit result. It also checks that this document preserves delivery-event, timezone, return, incomplete-period, and decision-required disclosures.

No analytics model, endpoint, query, cache, dashboard widget, or frontend fixture is created by ANALYTICS-01. Before ANALYTICS-02 implements a calculation, it must resolve or explicitly preserve the listed return/date/rounding gates and prove same-store isolation, event-history correctness, empty-versus-incomplete behavior, and hand-calculated examples.
