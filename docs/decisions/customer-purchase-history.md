# CUSTOMER-03 derived purchase-history rule

Customer purchase history is read-only and is never copied into mutable customer fields. `get_customer_purchase_history(customer)` reads only orders whose `store_id` and `customer_id` match the supplied customer.

An order counts as a currently eligible purchase only when it has a non-null `delivered_at` and status `DELIVERED` or `RETURN_REQUESTED`. A return request does not reverse an actual delivery. `RETURNED` and `REFUNDED` orders are excluded because the approved first-prototype rule treats accepted full returns as one reversal of the completed sale. All other statuses are excluded.

For every eligible order, net merchandise spend is `sum(quantity × selling_price_snapshot) - order_discount`. Seller delivery cost, payment state, customer delivery charge, tax, and general expenses are not customer purchase totals. `last_purchase_at` is the latest eligible `delivered_at`; no eligible order gives count `0`, total `0.00`, and no last-purchase timestamp.

**[DECISION REQUIRED] DR-04 / DR-06 / DR-07:** rounding/allocation, partial returns/refunds, and reporting-period semantics need approval before broader sales, profit, segmentation, or analytics totals are implemented. CUSTOMER-03 does not add an order API, lifecycle transition service, payment workflow, or a persisted customer summary.
