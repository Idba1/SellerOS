# Estimated-profit formula and cost treatment

## 1. Purpose and scope

This document approves the narrow SellerOS **estimated operational profit** calculation for a single authorized store. It is deterministic decision-support arithmetic, not tax, cash-flow, accrual, or formally audited accounting.

It applies only after the caller has resolved the store server-side. It does not change existing analytics responses or create a profit API. No value in this document is a forecast, an AI result, a payout amount, or a guarantee of profit.

## 2. Approved period and eligibility basis

For the first implementation, a profit request must describe whole store-local business days: inclusive `start_date` through inclusive `end_date`. The server converts them using the store's recorded IANA timezone to the half-open instant interval:

```
[ start_date 00:00:00 local, (end_date + 1 day) 00:00:00 local )
```

An order is a base eligible sale only when it has exactly one original immutable `DELIVERED` status event in that interval. The delivery event determines sale recognition; `created_at`, current product price/cost, and a mutable current order status do not. Duplicate delivery evidence is invalid and prevents a result, consistent with the base sales-summary contract.

A reversal is eligible in the business-date period containing the first terminal `RETURNED` or `REFUNDED` status event after an original delivery. SellerOS v1 supports full-order reversals only. `RETURN_REQUESTED` has no financial effect, and a later `REFUNDED` status after a `RETURNED` reversal has no second financial effect.

Store-level operating expenses are eligible when `Expense.incurred_on` falls inclusively between `start_date` and `end_date`. This deliberately uses the expense's existing store-local business date, not `created_at` or `updated_at`.

## 3. Approved formula

All monetary inputs are BDT `Decimal` values stored to two decimal places. For each eligible order line `i`:

```
line_gross_i       = quantity_i × selling_price_snapshot_i
line_net_revenue_i = line_gross_i − discount_allocation_i
line_cogs_i        = quantity_i × unit_cost_snapshot_i
```

For the authorized store and selected period:

```
delivery_net_revenue     = Σ line_net_revenue_i for eligible deliveries
delivery_product_cost    = Σ line_cogs_i for eligible deliveries
return_net_reversal      = Σ line_net_revenue_i for eligible full-order reversals
return_cost_reversal     = Σ line_cogs_i for eligible full-order reversals
net_revenue              = delivery_net_revenue − return_net_reversal
product_cost             = delivery_product_cost − return_cost_reversal
seller_delivery_cost     = Σ order.seller_delivery_cost for eligible deliveries
recorded_operating_cost  = Σ expense.amount
estimated_operational_profit =
    net_revenue − product_cost − seller_delivery_cost − recorded_operating_cost
estimated_profit_margin_percent =
    estimated_operational_profit / net_revenue × 100
```

`estimated_profit_margin_percent` is available only when `net_revenue > 0` and every required cost condition below is satisfied. It is never substituted with `0%` for a zero or unknown denominator.

### Revenue and discount treatment

- Use `selling_price_snapshot`, never the current catalogue selling price.
- Use persisted `OrderItem.discount_allocation`, never a newly calculated allocation. The existing order invariant requires all line allocations to equal `SalesOrder.order_discount`, so line-net revenue reconciles exactly to order gross minus its stored order discount.
- Product/variant names are descriptive snapshots only; they do not affect arithmetic.

### Product cost treatment

- Use `unit_cost_snapshot`, fixed when the order is confirmed, never a current catalogue cost.
- A `NULL unit_cost_snapshot` is an unknown cost, not BDT 0.00. If any eligible line has an unknown snapshot cost, suppress the profit and margin figures and return a clear incomplete-cost status.

### Delivery cost treatment

- Use `SalesOrder.seller_delivery_cost` once per eligible order. A stored `0.00` is a known zero.
- A `NULL seller_delivery_cost` is unknown, not BDT 0.00. If any eligible order has no recorded seller delivery cost, suppress profit and margin as incomplete.
- Customer-paid shipping, courier settlements, and payment-gateway fees are outside the current data model and are not inferred.

### Operating expense treatment and allocation

- Deduct every recorded same-store expense in the selected business-date period once from the **store-level** estimate.
- Do not allocate general expenses to orders, products, variants, customers, or individual days. Therefore the first product-performance endpoint must not present profit ranking or per-product profit.
- For the prototype, seller-entered `Expense` rows are the authoritative operating-expense ledger. A period with no rows has recorded operating cost `0.00`; outputs label this component `seller_entered_expenses` rather than claiming formal accounting completeness.

## 4. Reversals, missing data, and output states

### Returns and refunds

The first terminal `RETURNED` or `REFUNDED` event reverses the full order's stored line-net revenue and stored line COGS in that event's store-local business-date period. This produces a negative net-revenue/product-cost adjustment when the original delivery belongs to an earlier period. It does not reverse the original outbound `seller_delivery_cost`, because that delivery service has already been consumed. A following refund after a return is informational only and does not create a second reversal.

Partial returns are not supported in SellerOS v1: the interface/service must reject any attempt to record a partial-return amount or quantity until a future schema explicitly stores returned quantities and costs. It must not infer a partial return from an order-level status.

### Completeness gates

Do not calculate or display a numeric profit/margin when any of these applies:

| Condition | Required status |
| --- | --- |
| Duplicate delivery evidence | `unavailable_invalid_delivery_evidence` |
| Unknown `unit_cost_snapshot` on an eligible line | `unavailable_missing_product_cost` |
| Unknown `seller_delivery_cost` on an eligible order | `unavailable_missing_delivery_cost` |

When a period has no deliveries or reversals, its revenue and product cost are BDT `0.00`; its profit can therefore be negative when it contains recorded operating expenses. An implementation may still expose non-financial diagnostics (for example, which cost category is missing) only if it does not disclose another store's data. It must not fill unknown inputs with zero or silently omit their costs.

## 5. Rounding and reconciliation

All persisted money is BDT with two decimal places. Use Python `Decimal` arithmetic; never binary floating point.

1. Preserve the stored line discount allocations. Their creation already uses `ROUND_HALF_UP` and leaves the final-line remainder so the saved allocations reconcile exactly to the order discount.
2. Multiply integer quantity by the two-decimal stored snapshot price/cost and sum the resulting `Decimal` values without an intermediate reallocation.
3. Sum delivery and expense values once each.
4. Quantize the final monetary outputs to BDT `0.01` using `ROUND_HALF_UP` before serializing them as two-decimal strings.
5. Quantize percentage margin to `0.01` percentage points using `ROUND_HALF_UP`; label it as an estimate.

An implementation test must verify that the displayed revenue reconciles to the line totals and that the displayed profit equals the displayed component subtraction under this rule.

## 6. Worked synthetic examples

### Example A — complete, hand-checkable aggregate

Period: 1–31 January, store-local dates. The period has no returned/refunded included orders.

| Input | Value (BDT) |
| --- | ---: |
| Line A: `2 × 100.00`, discount allocation `10.00`, unit cost `40.00` | gross 200.00; net revenue 190.00; COGS 80.00 |
| Line B: `1 × 80.00`, discount allocation `0.00`, unit cost `30.00` | gross/net revenue 80.00; COGS 30.00 |
| Seller delivery cost for the two orders | 15.00 |
| Recorded packaging expense | 12.00 |
| Recorded advertising expense | 8.00 |

```
net_revenue             = 190.00 + 80.00 = 270.00
product_cost            = 80.00 + 30.00 = 110.00
seller_delivery_cost    = 15.00
recorded_operating_cost = 12.00 + 8.00 = 20.00
estimated profit        = 270.00 − 110.00 − 15.00 − 20.00 = 125.00
estimated margin        = 125.00 / 270.00 × 100 = 46.30%
```

Expected presentation: estimated operational profit `BDT 125.00`, estimated margin `46.30%`, and expense component `seller_entered_expenses`.

### Example B — missing snapshot cost

If Line B has `unit_cost_snapshot = NULL`, its BDT 80.00 revenue can remain a recorded sales fact, but profit and margin must not be calculated. Expected status: `unavailable_missing_product_cost`; do not replace its cost with `0.00` or a current product cost.

### Example C — full-order return in a later period

If Line A is first marked `RETURNED` in February, January remains unchanged. February receives its reversal from the stored snapshots:

```
net_revenue adjustment = −190.00
product_cost adjustment = −80.00
seller_delivery_cost adjustment = 0.00
February estimated profit = −190.00 − (−80.00) = −110.00
```

If the order subsequently becomes `REFUNDED`, February remains `BDT -110.00`; there is no second deduction. A partial return is rejected rather than estimated.

## 7. Fixed prototype policy boundaries

- The metric is explicitly pre-tax and excludes payment-gateway fees, customer-paid shipping, courier settlements not stored as `seller_delivery_cost`, cash collection, inventory shrinkage, and any unrecorded return-shipping charge. SellerOS must neither infer nor add a zero-valued row for these excluded components.
- The authoritative v1 operating-expense ledger is the seller-entered `Expense` table. The label `seller_entered_expenses` communicates that this is a prototype business ledger, not audited accounting.
- Reports recompute from the current immutable order snapshots, status events, and current expense rows. SellerOS v1 has no period lock, correction ledger, or partial-day profit report; the date range always represents complete store-local business days.
- General operating expenses are deducted only at store aggregate level. SellerOS v1 does not expose product/order/customer profit or allocate expenses among them.

## 8. Implementation and verification boundary

Before a profit service or API is built, implement automated tests matching Examples A–C plus date-boundary, foreign-store isolation, zero-revenue margin, duplicate-delivery, and rounding-reconciliation cases. The current ANALYTICS-03/04 endpoints intentionally remain base-delivered sales views and must not be relabelled as profit.

Review outcome for PROFIT-01: the formula and worked examples above are the fixed prototype baseline. Missing stored product/delivery costs block an unreliable number; they are data-quality failures, not unresolved business decisions.
