# SellerOS Analytics, Forecast and Scenario Rules

PLAN-05, 5 October 2026. Decision/documentation only. Existing approved constraints are retained; candidate numerical policies below are **not selected or approved**. No models, forecasts, accuracy measurements, provider calls, application code or executable future tests are created.

## 1. Authority and inspection

Sources: [scope baseline](../requirements/scope.md), [40-requirement register](../requirements/traceability.csv), [order/inventory rules](order-and-inventory.md), and [account/store rules](auth-and-store.md). PLAN-04's user-selected owner and active staff may use all approved same-store analytics/AI operations; staff cannot manage users or store settings. Server authorization and same-store data filtering precede every computation/retrieval.

Initial inspection: branch `docs`, clean working tree; two source documents, requirement records, PLAN-03/04 decisions and `check.py`. No application, dataset, API contract, metric implementation or trained model exists. Preserve all previous files and open decisions. This record specifies candidates and gates permitted by PLAN-05; it does not resolve PLAN-03 DR-01–DR-08 or provider/privacy decisions.

Approved stack remains React/Vite/TypeScript with Tailwind/shadcn, TanStack Query/Recharts; Python/Django/DRF/Django ORM; PostgreSQL; Pandas/NumPy/Scikit-learn. XGBoost only if later data/evaluation justifies it. LLMs stay backend-isolated, explain verified metrics and draft suggestions, and never supply financial arithmetic or make autonomous actions.

## 2. Shared output contract and eligibility

Every output must identify authorized store, source/data period, cutoff/as-of time, method/formula or criteria, input completeness, material assumptions, and limitation/fallback status. Display AI text as a suggestion, forecast/scenario numbers as estimates, and deterministic figures as calculated values with their basis. This is a semantic contract, not a finalized JSON/API schema.

Use PLAN-03 actual delivery as completed-sale recognition and the historical confirmation cost/transaction-price snapshots. Exclude unfulfilled/cancelled orders from completed sales. A delivered-origin RETURN_REQUESTED retains recognized sales until acceptance; a shipped-origin request never invents a delivered sale. Accepted returns reverse eligible revenue/COGS once; REFUNDED cannot subtract again. Current status filters alone cannot reconstruct these events.

Use configured store timezone and original delivered date for sale grouping. Currency/rounding, fallback timezone, reversal-period treatment and expense timing remain unresolved. Do not merge currencies or date bases, fill unknown costs with zero, interpret a missing observation as a known zero, or invent a formula for an undefined financial component. An empty *complete* dataset may show zero counts/totals; missing/incomplete history must be visibly distinct. Ratios with zero or unknown denominator are unavailable, not fabricated zero percentages.

## 3. Output definition register

All formulas are subject to the eligibility and unresolved monetary/date contracts above. These definitions operationalize existing requirements; additional optional metrics are candidate choices, not new mandatory features. Verification IDs reference section 8.

| ID / output | Required inputs | Formula or method | Limitation / fallback | Planned verification |
| --- | --- | --- | --- | --- |
| O-01 Sales totals and period chart | Eligible delivery/reversal events, quantities, frozen selling prices, order discount allocations, store/period | Line gross = quantity × snapshot price; gross = sum eligible line gross; net before reversal = gross − order discounts; net after reversal subtracts eligible recognized net reversal once; group by approved period | Reversal date/amount policy DR-06/07 and rounding DR-04 block final period contract; distinguish gross sales from net sales | V-01–03 |
| O-02 Sales counts and product summaries | Eligible order IDs/product identities, quantities and return events | Count distinct completed orders; sum delivered units; show accepted returned units separately. Net retained units = delivered units − accepted returned units under approved event/period policy | Whether fully returned orders count in net order count and exact net-period quantity treatment AC-01; do not label delivered units unconstrained market demand | V-01–03 |
| O-03 Estimated profit and margin | O-01 net revenue, known snapshot COGS, recorded delivery costs and applicable period expenses | Profit = net revenue − eligible snapshot COGS − recorded delivery costs − applicable recorded operating expenses; margin candidate = profit / net revenue × 100 when denominator positive and all required costs known | Missing costs imply incomplete result; no full-profit/margin claim. No general expense allocation to order/product; PROFIT contract and DR-06/08 remain open | V-04–05 |
| O-04 Low-stock indicator | Authorized current stock and seller threshold | Stock ≤ configured threshold | Missing threshold gives not configured, not guessed threshold; stock values are current as-of, not historical sales metrics | V-06 |
| O-05 Customer segmentation | Authorized customer IDs, eligible dated purchases, order counts/spend/category history, as-of cutoff | Candidate interpretable recency/frequency/monetary rules: recency = as-of − most recent eligible purchase date; frequency = distinct eligible purchase count; monetary = eligible net spending; thresholds and label precedence must be approved | No purchase history means unavailable recency, not 0 days; return effects and thresholds AC-02. No sensitive traits, credit scoring or denial of service | V-07–08 |
| O-06 Product demand estimate | Product/variant identity, complete ordered time buckets of eligible sold quantities, history coverage, horizon, return/stockout annotations | Selected simple baseline first; candidate moving mean or last-observation/seasonal naive forecast; compare candidate method using past-only validation | Observed fulfilled sales proxy, not lost/unconstrained demand. Data/policy gates AC-03–06; insufficient history yields no numerical forecast | V-09–13 |
| O-07 What-if estimate | Authorized product, chosen price OR discount change, explicit baseline quantity/period/price/cost, approved discount scope | Candidate deterministic fixed-quantity sensitivity: scenario revenue = baseline quantity × scenario price − applicable scenario discount; scenario profit uses known cost components; delta = scenario − baseline | No price-demand causal inference. Unit/order discount scope, baseline, quantity, rounding and optional expense treatment AC-07; no numeric output when missing inputs | V-14–17 |
| O-08 AI Business Advisor summary | Selected store/period, verified O-01–04 metrics, completeness metadata and relevant records | Backend supplies minimized computed context; LLM explains only available verified figures with period/metric references | Provider unavailable => visible unavailability and verified descriptive metrics; optional deterministic explanation requires explicit approval in PLAN-06; never invent insights | V-18–19 |
| O-09 AI Customer Assistant draft | Entered customer message, current same-store product/variant/price/stock retrieval with as-of context | Retrieve store facts before backend LLM draft; seller reviews/edits/discards; no automatic send | Unknown match/price/availability => disclose or ask for clarification; provider failure => no fake successful AI draft; fallback policy PLAN-06 | V-18–20 |

## 4. Data audit and forecasting candidates

Before selecting thresholds or fitting any model, document per-product earliest/latest eligible dates, bucket coverage, unique nonzero-sale periods, duplicate IDs/events, invalid quantities/timestamps, missing prices/costs, returns, stockout periods, product/variant identity changes, and observation completeness. Cost completeness is needed for profit/scenario outputs, not necessarily a quantity-only forecast. A missing delivery/quantity/date cannot be replaced by synthetic fact. Synthetic test data is valid for workflow verification, not evidence of real-world accuracy.

Candidate choices, all **[DECISION REQUIRED]**:

| Decision | Candidate A | Candidate B | Data needed / selection boundary |
| --- | --- | --- | --- |
| AC-03 Granularity and horizon | Daily buckets; next 7 days | Weekly buckets; next 4 weeks | Compare sparsity, business need and actual observation span; no automatic user-selected arbitrary horizon |
| AC-04 Simple baseline | Trailing arithmetic mean of k training buckets; constant forecast | Last observed bucket; seasonal naive only with supported seasonal lag | Approve k or lag, enough complete training buckets, forecast aggregation and handling of all-zero history |
| AC-05 Sufficiency | Candidate daily gate: 56 consecutive complete days, ≥14 nonzero-sale days; reserve last 7 for evaluation | Candidate weekly gate: 16 complete weeks, ≥8 nonzero-sale weeks; reserve last 4 for evaluation | These are review examples, not statistical guarantees or approved minimums. Method-specific gates must include validation length, stability, missing buckets and stockout treatment |
| AC-06 Evaluation/model | Past-only baseline evaluation with MAE | MAE plus RMSE, expanding-window evaluation; a simple lag regression if justified | Select folds, cutoff, horizon-aligned error aggregation and model features; never random-shuffle time series. XGBoost not a default |

MAE candidate = mean(abs(actual − prediction)); RMSE candidate = sqrt(mean((actual − prediction)^2)). Both require held-out actual quantities in the same unit and horizon. MAPE is not a default because zero-sales denominators need a separately defined policy. No acceptable-error threshold or claim of improvement is assumed. Record actual baseline and candidate scores, split dates, dataset/version and limitations only after tests run; do not select a worse model merely because it is more complex.

All transformations, feature selection and tuning use training periods only. Do not leak future returns, future price changes, full-dataset normalization or validation results into fitted features. Quantity history cannot be negative without an explicitly approved return-series design; do not feed refund accounting adjustments directly as negative customer demand. Stockouts censor observed sales; annotate or exclude/model them only under an approved policy, never impute lost demand as known sales.

## 5. Segmentation and metric decisions

**[DECISION REQUIRED] AC-01:** count/quantity net-of-return semantics; whether to report event-period adjustments or restate original delivery; treatment of zero/negative net periods; optional average order value denominator. Align with PLAN-03 DR-06/07, including final expense aggregation and margin completeness.

**[DECISION REQUIRED] AC-02:** purchase-behavior window, recency/frequency/spend thresholds, new/repeat/high-value/inactive label overlap/precedence and full-return effects. Candidate simple rules distinguish first versus repeat purchases and a chosen inactivity window; no day/spend cutoff is approved. Display actual criteria beside each label. Start with interpretable rules; clustering remains optional only if data/value/explanation justify it. Customer names/contact details and sensitive traits are not model features.

## 6. Scenario candidates and assumptions

**[DECISION REQUIRED] AC-07:** select supported variables (new selling price or discount), allowable range, order-level versus single-product scenario representation, historical baseline period/quantity, whether quantity is entered by the seller or derived from verified history, and exact cost/expense completeness contract. Preserve PLAN-03 order-level discount; do not silently invent production line-level discounts for the simulator.

Recommended candidate is fixed-quantity arithmetic with disclosed baseline. Changing price while holding quantity constant explores arithmetic sensitivity; it does not predict that sales volume stays constant. A demand-response model or elasticity coefficient is not approved and must not be inferred from correlation. A forecast-based baseline quantity requires the approved forecast gate and must carry its limitations into the scenario. Price/discount changes never mutate the product/order or send messages.

Illustrative synthetic, currency-free case: baseline quantity 10, price 20, known unit cost 12, explicit delivery cost 0, no discount, explicit applicable expenses 0. Revenue 200 and estimated profit 80. Scenario price 18 at the same quantity gives revenue 180, estimated profit 60 and delta −20. This is hand arithmetic, not an observed business/model result or approval of omitted expenses as zero. Missing cost cannot be substituted with the example's known values.

## 7. Fallback and disclosure rules

Preserve FR-16/AIR-09: insufficient forecast history produces “A reliable forecast cannot be generated from the available history,” with missing condition, available period/count and descriptive eligible history if valid. No numeric forecast, accuracy badge, invented confidence interval or blank success chart. An all-zero but complete series is distinguishable from absent data; its forecast eligibility remains AC-05, not automatically sufficient.

Unresolved policy yields a distinct decision-blocked output, not a claim that data alone is insufficient. Invalid data identifies the inconsistency. Missing costs retain explicit unknown fields/coverage and suppress unsupported complete profit/margin. Missing scenario inputs prevent the numerical estimate and identify what is needed. Genuine zero totals are displayed only for complete eligible observations. LLM outage/timeout cannot become fabricated AI text; show service limitation and permitted deterministic data. Specific transport/error JSON is for BACKEND-05; provider behavior/retention/budget for PLAN-06.

Each result exposes method version, authorized data period/cutoff, selected horizon or scenario change, material assumptions and review limitation. Numerical uncertainty intervals are optional and require a justified evaluated method; never invent “95% confidence.” Real external actions remain with the seller. No guarantee of profit, growth, forecast accuracy or causal outcome.

## 8. Planned verification matrix

Cases are not implemented/executed. Proposed locations: future `backend/apps/analytics/tests/`, `profit/tests/`, `segmentation/tests/`, `forecast/tests/`, `simulator/tests/`, `advisor/tests/`, `assistant/tests/`; frontend feature tests for disclosures; future `docs/evidence/` for observed arithmetic and AI/model evaluation. Paths may follow later agreed structure without losing coverage.

| ID | Planned case | Expected verification |
| --- | --- | --- |
| V-01 | Delivered, pending, cancelled and shipped-origin return-request fixtures | Only actual eligible delivered sales contribute; no invented recognition |
| V-02 | Gross 60/40, order discount 10, full accepted return then REFUNDED | Initial net 90; reversal once; no second deduction at refund; DR-06 amount gate |
| V-03 | Delivery/return in different periods and timezone boundary | Follow selected DR-07/AC-01 policy; preserve original events; unresolved policy blocks aggregate |
| V-04 | Known costs versus missing snapshot/delivery/expense inputs | Hand formula agrees for complete case; incomplete profit clearly disclosed |
| V-05 | Zero/unknown revenue, no arbitrary general expense allocation | Margin unavailable when undefined; no double counted expenses or misleading complete profit |
| V-06 | Stock below/equal/above configured threshold and missing threshold | Correct inclusive boundary; missing gives not configured |
| V-07 | First/repeat/inactive/high-spend/no-history customers | Approved thresholds/precedence and as-of cutoff applied; no-history recency unknown |
| V-08 | Customer sensitive attributes and future purchase data | Excluded from features; no temporal leakage or sensitive labels |
| V-09 | History below/at approved gate, missing bucket versus observed zero | No number below gate; selected boundary honored; missing not silently filled |
| V-10 | Complete all-zero, sparse and stockout histories | Approved sufficiency/censoring policy; limits disclosed, no lost-demand invention |
| V-11 | Selected baseline on hand-checkable training buckets | Formula/window/horizon match; predictions use past data only |
| V-12 | Held-out time sequence with obvious hand-calculated errors | MAE/RMSE agree with selected contract; no random split or future preprocessing |
| V-13 | Candidate worse than baseline or no held-out data | Report observed comparison honestly; retain simpler eligible method or no evaluable forecast; no fabricated score |
| V-14 | Section 6 fixed-quantity illustrative case | Revenue/profit/delta 180/60/−20 with disclosed assumptions |
| V-15 | Negative/excess discount, invalid price, missing costs/baseline | Apply approved input bounds; no negative-net or invented complete estimate |
| V-16 | Multi-item discount allocation and rounding residual | Preserve order discount contract; selected rounding reconciles sums; DR-04 gate |
| V-17 | Scenario output versus production records | No price/order/stock changes; estimate label, selected variable and baseline visible |
| V-18 | Owner, active staff, revoked staff and foreign store | PLAN-04 permissions; no foreign context, records, cached results or provider calls |
| V-19 | Advisor metrics complete/incomplete; provider unavailable | Summary matches period/verified metrics; unsupported claims rejected; outage disclosed |
| V-20 | Assistant known/unknown product, changed stock and provider error | Current same-store grounding; no unsupported verified price/availability; draft review only |
| V-21 | No records versus incomplete imported history | Known-empty descriptors distinct from unavailable/incomplete inputs |
| V-22 | UI result rendering and future saved evaluation record | Inputs/period/method/limitations visible; minimized retention follows PLAN-06; no claimed results before execution |

## 9. Open decisions and dependency gates

AC-01–07 remain **[DECISION REQUIRED]**: metric return/date/count contracts; segmentation criteria; forecast bucket/horizon; baseline/window; numerical sufficiency gates; evaluation/model selection; simulator variables/baselines/assumptions. Candidate examples are for selection, not defaults for later coding. Earlier DR-01–08 and AD-02–04 remain unchanged. Provider, authorized evaluation dataset, retention and LLM fallback choice belong to PLAN-06. No unresolved forecast threshold or simulator demand assumption is silently approved.

Traceability: O-01–04 cover FR-03–04/08–10 and AIR-07; O-05 covers FR-14/AIR-04; O-06 FR-15–16/AIR-05–06; O-07 FR-17–18/AIR-08/10; O-08 FR-13/AIR-03; O-09 FR-11–12/AIR-01–02/10. FR-19–20, AIR-09 and NFR-01–02/04/06/10 apply across outputs. No changes to source requirements are needed to document these candidates. Definitions must be finalized before dependent schemas/API/calculation/model tasks; selecting a model does not bypass data sufficiency or evaluation.

Next dependency: **PLAN-06 — approve data, LLM provider and evaluation policy**. No setup, analytics, forecast or scenario implementation is started. This document satisfies PLAN-05's allowed candidate-recording scope; it does not claim that open business decisions are resolved or the whole architecture is ready to implement.

## 10. Verification evidence

Inspection commands: `git status --short --branch`; `rg --files --hidden -g '!.git'`; `Get-Content docs/decisions/auth-and-store.md`; selected financial/date sections of `Get-Content docs/decisions/order-and-inventory.md`; selected scope/decision sections of `Get-Content docs/requirements/scope.md`. Outcomes: clean tree on docs; prerequisite documents present; no data/application/model to evaluate. No source file modified.

PowerShell assertions using `Get-Content -Raw`, `[regex]::Matches` and `Compare-Object` printed `PASS: 9 output definitions, 22 planned verifications, 10 sections, AC-01–07 referenced`, exit 0. Manual review confirmed every output row has inputs, formula/method, limitations/fallback and verification references; scenario example arithmetic is correct; missing-versus-zero handling, no duplicate reversals, tenant scope and candidate/approved distinctions are preserved. Structural checks do not prove future application behavior or model quality.

Final commands: `git diff --check`, `git diff --stat`, `git diff` (all empty for tracked files); `git diff --no-index --stat -- NUL docs/decisions/analytics-and-ai.md` (new-file summary); `git diff --no-index --check -- NUL docs/decisions/analytics-and-ai.md` (no whitespace errors); `git status --porcelain=v1 --untracked-files=all` (only this new document). Git warned that LF may be converted to CRLF. No-index diff reports exit 1 for a file difference, not an application failure. Final line count is reported in chat.

No application tests/builds or model benchmarks apply. Only this file is created; no commit, package installation, secret, customer dataset, autonomous action or unrelated implementation.
