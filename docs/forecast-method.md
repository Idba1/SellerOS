# FORECAST-02 — Minimum-Data and Eligibility Policy

**Status:** eligibility-policy specification only. No bucket series, baseline, trained model, numerical forecast, accuracy result, API, or frontend output is implemented.

## 1. Purpose and current disposition

Before SellerOS can calculate any numerical demand forecast, it must distinguish insufficient, invalid, and policy-blocked history from a valid series. This policy consumes the store-scoped FORECAST-01 audit; it does not replace its authorization, duplicate its delivery-evidence checks, or convert missing observations into zero demand.

The current reviewed synthetic data is **not eligible** under either candidate below. Therefore the current product state remains unavailable: no forecast value, confidence interval, accuracy score, or model-selection claim is permitted.

## 2. Common non-negotiable eligibility conditions

Every future forecast request must begin with a server-authorized single store and an explicit data cutoff. It must satisfy all of these conditions before any volume threshold is considered:

1. Original immutable `DELIVERED` status-event evidence is the source; store timezone is used for calendar grouping.
2. There are no duplicate delivery events for an order, no delivery order with missing items, and no invalid/non-positive quantity or timestamp evidence.
3. Observation coverage is explicitly known for every proposed bucket. A missing delivery record cannot be interpreted as a zero-demand bucket.
4. Stockout/censoring periods are annotated or excluded under an approved policy; observed fulfilled sales are not assumed to equal unconstrained demand.
5. A terminal returned/refunded record is handled under an approved return-series policy. It must not be transformed into invented negative demand.
6. Training and later evaluation windows remain time-ordered; future observations cannot enter a feature, normalization, or model choice.

If a condition is false, return one of these safe states instead of a number:

| State | Meaning | Required disclosure |
| --- | --- | --- |
| `insufficient_history` | Valid evidence exists but does not meet the eventually approved amount/coverage rule. | Available span, observed bucket count, missing condition, and that no numerical forecast was generated. |
| `invalid_history` | Duplicate, missing-item, invalid timestamp/quantity, or other integrity failure exists. | Data-quality condition only; do not calculate a partial forecast. |
| `decision_blocked` | Coverage, stockout, return-series, or threshold policy is not approved. | Which policy is missing; do not substitute a zero/negative bucket or estimate. |

## 3. Approved v1 minimum-data gate

Following the team's explicit implementation authorization, SellerOS v1 selects the daily candidate below. It is a conservative prototype gate, not a guarantee of accuracy or business benefit.

| Candidate | Proposed granularity/horizon | Candidate valid-history gate | Why it is only a candidate |
| --- | --- | --- | --- |
| **Selected: daily v1** | Next 7 days | 56 consecutive **complete** daily buckets, at least 14 nonzero-sale days, and 7 later complete days reserved for past-only evaluation. | Preserves short-cycle seller operations while refusing sparse/unknown coverage. |
| Not selected | Weekly / next 4 weeks | 16 consecutive complete weeks, at least 8 nonzero-sale weeks, and 4 holdout weeks. | Kept only as a non-active alternative; no weekly output is implemented. |

The selected v1 policy uses store-local calendar-day boundaries, an explicit data cutoff, and a seven-day past-only holdout. A terminal returned/refunded delivery, duplicate delivery evidence, unknown coverage, missing order items, or unannotated stockout blocks the forecast; it is not converted to a negative/zero demand observation.

## 4. Current-data assessment

FORECAST-01 found only three delivery dates over a 57-day span for `synthetic-store-a` (54 unobserved dates, one accepted-return record) and one delivery date for `synthetic-store-b`. The repository has no universal history-coverage or stockout marker. Therefore:

- neither store meets either candidate's consecutive complete-bucket or nonzero-observation candidate;
- the return-series condition is not approved; and
- the correct current outcome is `decision_blocked` with no numerical result, not a failed/zero forecast.

This is a limitation of the synthetic fixture and current ingestion evidence, not evidence about real seller demand or forecast accuracy.

## 5. Versioned insufficient-data examples

`backend/tests/forecast_cases/eligibility-v1.json` records synthetic cases for empty, sparse, gapped, duplicate, return-related, and candidate-threshold-boundary histories. Its structural test verifies that each case has a safe expected state and disclosure and that the numeric candidates retain `decision_required` status.

## 6. Handoff

A future authorized task may implement a bucket builder only after F-02 is selected. It must reuse the FORECAST-01 store audit and emit its exact period, data cutoff, coverage evidence, selected policy version, and limitation state. It must not train or compare a model until a separate method/evaluation task defines past-only validation.
