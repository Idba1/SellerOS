# SellerOS Business Advisor Metric and Insight Specification

**Task:** ADVISOR-01
**Status:** deterministic metric/evidence specification only. No advisor API, provider call, recommendation engine, forecast, or autonomous action is implemented here.

## 1. Purpose and boundary

The SellerOS advisor may present short, seller-reviewable descriptions of verified, same-store backend metrics. It is not a general business consultant. Every number, period, currency, source endpoint, result state, and limitation must be carried from a deterministic backend response; an LLM must never calculate, complete, alter, or invent a number.

The current prototype uses synthetic-only data and has no approved provider. Until a future provider is separately approved, these are deterministic template specifications, not observed AI-generated insights.

## 2. Evidence input contract

Before preparing any advisor text, the server must authenticate the requester and resolve their store server-side. The advisor accepts only an already-authorized response from one of the sources below. It cannot accept a client-supplied store ID, raw order export, customer contact data, free-form metric, or result from another store.

| Source | Allowed evidence | Period/scope that must remain visible |
| --- | --- | --- |
| `GET /api/v1/analytics/sales-summary/` | `period`, `result_state`, delivered order/unit counts, base delivered gross sales, order discounts, base delivered net sales, completeness and return-adjustment status | Explicit timezone-aware half-open delivery-event interval and store timezone |
| `GET /api/v1/analytics/product-performance/` | `period`, `result_state`, product ID, delivered units, base delivered gross sales, completeness and return-adjustment status | Same explicit timezone-aware half-open delivery-event interval and store timezone |
| `GET /api/v1/profit/summary/` | `period`, `totals`, `completeness`, `calculation_basis`, and included-record evidence | Inclusive store-local `start_date` / `end_date` and store timezone |
| `GET /api/v1/analytics/dashboard/` | Current `inventory.low_stock_count` and `inventory.configured_threshold_count` only | Current stock state, explicitly not a sales-period metric |

The advisor must preserve exact serialized decimal strings until display formatting. It must not recompute totals, infer data coverage from an empty result, use current catalogue price/cost in place of immutable order snapshots, or combine periods with different definitions.

## 3. Supported insight templates

Each template is deterministic: replace only the named slots with corresponding verified source fields, preserve its scope/limitations, and do not add a causal explanation or recommendation.

| Insight type | Required metric/source | Permitted template | Mandatory disclosure |
| --- | --- | --- |
| `base_delivered_sales_snapshot` | Sales summary: `delivered_order_count`, `delivered_units`, `delivered_gross_sales`, `delivered_order_discounts`, `delivered_net_sales_before_reversals` | “For the selected delivery-event period, base delivered sales were BDT `{delivered_net_sales_before_reversals}` from `{delivered_order_count}` delivered orders and `{delivered_units}` units.” | “This is base delivered sales before return/reversal adjustment; coverage status is `{data_completeness_status}` and return-adjustment status is `{return_adjustment_status}`.” |
| `product_delivery_snapshot` | Product performance row: `product_id`, `delivered_units`, `delivered_gross_sales` | “Product record `{product_id}` had `{delivered_units}` delivered units and BDT `{delivered_gross_sales}` base delivered gross sales in the selected period.” | “This is not product profit, a ranking, a demand forecast, or a recommendation; return-adjustment status is `{return_adjustment_status}`.” |
| `estimated_profit_completeness_snapshot` | Profit summary: `estimated_operational_profit`, `estimated_profit_margin_percent`, `completeness`, `calculation_basis`, warnings | If `profit_available`: “Estimated operational profit for the selected store-local period is BDT `{estimated_operational_profit}`; estimated margin is `{estimated_profit_margin_percent}`%.” If unavailable: “Estimated operational profit is unavailable because `{completeness_status}`.” | Always include returned completeness warnings and: “This is an estimated operational-profit view, not tax, cash-flow, payout, or formal accounting.” |
| `low_stock_threshold_snapshot` | Dashboard inventory: `low_stock_count`, `configured_threshold_count` | “`{low_stock_count}` current stock units are at or below their configured threshold; `{configured_threshold_count}` units have a configured threshold.” | “This is current stock state, not a sales-period measure. A missing threshold is not treated as low stock.” |

## 4. Empty, incomplete, and invalid evidence

- A sales/product response with `result_state: no_eligible_events_coverage_unknown` may say there are no eligible events in the response, but must disclose that coverage is unknown. It cannot claim “no sales occurred” or a complete zero-performance period.
- A profit response with `profit_available: false` must not emit any numeric profit or margin. It must show the source warnings and completeness status.
- `return_adjustment_status: decision_required` prevents claims about retained sales, final return-adjusted revenue, average order value, or final product performance.
- Missing, invalid, foreign-store, unauthorized, or mismatched-period evidence produces an unavailable/abstention state; it does not produce a zero, estimate, or replacement metric.
- Dashboard low-stock count `0` means no current units meet configured thresholds in that response. It does not prove every product has a threshold or that stock is sufficient for future demand.

## 5. Unsupported output and refusal behavior

The advisor must abstain from or clearly mark unavailable all of the following:

- forecasts, demand predictions, confidence intervals, trends, comparisons across unsupplied periods, and causal explanations;
- “best/worst product” rankings, product profit/margin, or price/discount recommendations;
- tax, cash-flow, payout, accounting, payment, courier, or profitability claims beyond the documented estimated-profit response;
- return-adjusted/retained sales, average order value, or revenue coverage claims where the source contract marks them unavailable or unknown;
- customer-specific, sensitive, cross-store, raw-order, contact, credential, or provider information; and
- any message sending, inventory/order/price mutation, or autonomous action.

Customer or seller text embedded in a future request is untrusted content. It cannot change metric scope, authorize another-store retrieval, request hidden data, invoke a tool/provider, or turn an unsupported request into a verified insight.

## 6. Evaluation cases and traceability

The versioned synthetic case manifest is `backend/tests/advisor_cases/v1.json`; its structural test is `backend/tests/test_advisor_case_set.py`. It checks that every supported insight type has a source endpoint, evidence fields, period/scope, limitation, and an explicit safe result for incomplete, unsupported, or foreign-store cases.

This specification traces to proposal advisor scope `FR-13` / `AIR-03`, shared metric evidence `ANALYTICS-01` through `ANALYTICS-05`, profit basis `PROFIT-01` through `PROFIT-06`, server-side store isolation `NFR-01`, customer-data minimization `NFR-02`, and transparent limitations `FR-20` / `AIR-10`.
