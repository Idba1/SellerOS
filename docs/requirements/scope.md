# SellerOS scope baseline and proposal traceability

PLAN-02, recorded 5 October 2026. This document preserves the approved scope; it does not implement features or resolve business decisions. PLAN-01 found only `check.py` and the two source documents, with no application, manifests, configuration, or existing API contracts. The audit evidence remains in the PLAN-01 chat; no application run was claimed.

## Sources and authority

- [Proposal](../../documents/SellerOS_Project_Proposal_41-STA1_Vibelectuals.pdf), dated 3 October 2026: objectives and scope pp. 3–4; workflow p. 5; six features and techniques pp. 6–7; requirements pp. 7–10; technologies pp. 10–11; ethics and future work p. 13.
- [Master Plan](../../documents/SellerOS_Codex_Implementation_Task_Master_Plan%20(2).docx), dated 5 October 2026: sections 2–3, PLAN-01, PLAN-02, and start gate.
- [Requirement traceability register](traceability.csv): exact requirement wording normalized for whitespace, proposal page, planned module, verification case, evidence location, and decision dependency.

The Master Plan fixes PostgreSQL where the proposal says “PostgreSQL or SQL.” Keep React/Vite/TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, Recharts; Python/Django/DRF/Django ORM; PostgreSQL; Pandas/NumPy/Scikit-learn. XGBoost and clustering are conditional on justified data/evaluation, not mandatory additions. LLM integration stays backend-isolated; provider selection is unresolved. Paths in the register are proposed locations, not existing files or finalized schemas/API contracts. Every row is PLANNED with no implementation or test result claimed.

## Objectives

The general objective is a standalone web-based business intelligence and decision-support platform that organizes social-commerce seller records, explains performance, and supports routine decisions. The AI objective covers evaluated grounded reply suggestions, business insights, behavior segmentation, demand forecasting, metric interpretation, and labeled what-if estimates; financial arithmetic remains deterministic.

| Proposal specific objective (p. 3) | Requirement coverage | Planned outcome/evidence |
| --- | --- | --- |
| Connected product, inventory, order, customer, expense records for a seller account | FR-01–07, NFR-01, NFR-05, NFR-08 | Store-scoped operational workflow and integration cases |
| Sales and estimated profit from seller-entered costs | FR-08–10, AIR-07 | Verified aggregation and hand-calculated profit cases |
| Replies grounded in product, price, stock records | FR-11–12, AIR-01–02, AIR-10 | Retrieval fixtures and draft review evaluation |
| Plain-language performance patterns from available data | FR-13, AIR-03, AIR-09 | Metric-to-summary consistency evaluation |
| Non-sensitive purchase-behavior grouping | FR-14, AIR-04 | Criteria and boundary-case verification |
| Demand estimation when sufficient history exists | FR-15–16, AIR-05–06 | Time-aware baseline comparison or insufficient-data evidence |
| Price/discount scenarios with disclosed assumptions | FR-17–18, AIR-08, AIR-10 | Hand-calculated scenario and presentation cases |
| Test workflows and AI with documented representative criteria | FR-19–20, NFR-01–10 | Workflow, security, usability, performance and AI evaluation records |

## Included operations

Seller/store account and business profile; catalogue name/category/price/cost/variants/stock; inventory changes and seller-configured low-stock indicators; linked customers, products and orders; customer purchase history; expenses; period sales dashboards and estimated profit. Authorized entry/import is the data boundary, but a generalized import feature is not independently specified or authorized by this task. Prototype testing and demonstration use project, sample, or otherwise authorized data.

New, Confirmed, Processing, Shipped, and Delivered are required order status labels (FR-06). Their transitions, revenue eligibility, and stock effects remain open. Product deactivation is explicitly required (FR-02); archive/delete policy and variant implementation details still need decisions.

## Six AI and analytics features

| Feature | Inputs and processing | Output and verification | Coverage |
| --- | --- | --- | --- |
| AI Customer Assistant | Seller-entered/pasted message; retrieve current store product, variant, price, stock facts; backend LLM draft | Internal inbox; editable/discardable suggestion; relevance, factual consistency, grounding, unsupported-claim checks | FR-11–12, AIR-01–02, AIR-09–10 |
| AI Business Advisor | Computed sales/order/inventory/customer/cost summaries for selected period | Plain-language summary tied to metrics/period; consistency and usefulness review | FR-13, AIR-03, AIR-09 |
| Customer Segmentation | Approved recency, order count, spend, purchase history; interpretable rules first | Defined groups with visible criteria; consistency and interpretability checks; no sensitive traits | FR-14, AIR-04 |
| Demand Forecasting | Time-ordered product sales; sufficiency audit; justified method and simple baseline | Product/horizon/estimate/limitations, or explicit insufficient-data response; time-aware comparison | FR-15–16, AIR-05–06, AIR-09 |
| Profit Intelligence | Recorded revenue, product cost, delivery cost, discounts, expenses; deterministic formulas | Order/product/period estimated profit and margins, included/missing fields; arithmetic checks; optional explanation | FR-09, AIR-07, NFR-06 |
| What-if Business Simulator | Product and selected price/discount change; historical sales/costs; documented method | Estimated sales/revenue/profit changes and material assumptions; formula/input verification | FR-17–18, AIR-08, AIR-10 |

FR-19–20 and NFR-01–10 apply across these features. Numeric outputs must come from calculations/models, never invented LLM arithmetic. Missing/inconsistent evidence must produce disclosure or a request for data. All outcomes above are planned, not observed evaluation results.

## No-build list

The prototype excludes all proposal p. 4 boundaries and p. 13 future extensions:

1. Live Facebook Messenger, Instagram, WhatsApp Business APIs or automatic social-platform collection.
2. Automatic AI reply sending or customer follow-up without seller review; automated follow-up integrations are future work.
3. Courier booking/tracking APIs, payment-gateway processing, and financial-accounting integrations.
4. Guarantees of forecast accuracy, sales growth, improved outcomes, or unmeasured performance/AI quality claims.
5. Credit scoring, sensitive personal profiling, or customer decisions affecting product/service access; segments must not deny service or drive high-impact decisions.
6. General autonomous agents making purchases, changing prices, contacting customers, altering inventory, placing orders, or making financial commitments.
7. Complex multi-store enterprise operations, tax advice, and formal accounting statements.
8. Promised larger-data forecasting studies, extra model comparisons, enhanced uncertainty research, or seller usability studies beyond the agreed evaluation; these are separately scoped future work.
9. Uninterrupted production availability or production-scale workload guarantees (NFR-08–09).
10. Unreviewed real customer data, browser-side provider secrets, invented store facts, or claims that SellerOS outperforms other products without separate evidence.

## Decision dependencies

No dependent implementation may guess these rules:

| ID | [DECISION REQUIRED] | Planned resolution |
| --- | --- | --- |
| D-01 | Order transitions, sales/profit statuses, cancellation/refund/return behavior, stock deduction/restoration | PLAN-03 |
| D-02 | Discount level, delivery/expense placement, missing costs, date basis, timezone, currency, rounding | PLAN-03; PROFIT-01 |
| D-03 | One/multiple stores, account membership and staff roles; reconcile proposal future multi-store support with Master Plan's open account/store choice without enabling enterprise scope | PLAN-04 |
| D-04 | Forecast minimums, granularity, horizon, baseline/candidate model, metric/split; approved segmentation features/thresholds | PLAN-05; FORECAST-02–06; SEGMENT tasks |
| D-05 | Simulator supported changes, baseline selection and demand-response assumptions; no causal claim | PLAN-05; SIM-01 |
| D-06 | LLM provider terms, privacy/retention, server-side key policy, budget, availability, timeout/fallback; request-log minimization/redaction and retention | PLAN-06 |
| D-07 | Synthetic-only versus authorized data, access/reset/removal/retention and institutional requirements before real-data processing; demo environment, dataset and evaluation criteria | PLAN-06; DATA-01; later evaluation/deployment tasks |
| D-08 | Variant requirement reconciliation (proposal includes variants; Master Plan calls optional variants open), SKU uniqueness, duplicate customers, delete/archive semantics preserving required deactivation | Written decision before DB/API tasks |

Changes to these requirements or exclusions require an explicit scope decision and updated traceability before dependent coding. Planned team roles are not contribution evidence. No runtime setup, business rule, API contract, schema, or test result is approved by this record.

## PLAN-02 verification and next dependency

Verify that FR-01–20, AIR-01–10, and NFR-01–10 occur exactly once in the register, retain source wording, have source pages and nonempty planned implementation/test/evidence fields, and preserve all seven explicit proposal exclusions plus AI/future-work boundaries above. No application tests can run because no application exists. PLAN-03 is next: decide order, revenue, refund, and inventory rules. This task does not start it.
