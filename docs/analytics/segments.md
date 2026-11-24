# SEGMENT-01 — Customer Behavior Segment Criteria

**Status:** approved deterministic prototype policy. This document defines explainable labels from recorded, same-store order history. It creates no clustering model, customer API, scheduled job, recommendation, or automated contact.

## 1. Purpose and safe interpretation

SellerOS groups customers only to help a seller review recorded purchase behavior. A label is not a prediction, customer value judgement, eligibility decision, marketing instruction, demographic profile, or proof that the store has a complete customer history.

All features are calculated server-side after the requester is authorized for one store. A caller must not provide another store ID or a precomputed feature value. The output carries the `segment_rule_version` (`segment-v1`) and the selected `as_of` time so it remains explainable.

## 2. Evidence and feature basis

### 2.1 Eligible purchases

Use the existing CUSTOMER-03 purchase-history rule, restricted to the selected store and to orders delivered on or before the required `as_of` timestamp:

- include an order only when `delivered_at` is non-null and its current status is `DELIVERED` or `RETURN_REQUESTED`;
- exclude `DRAFT`, `PENDING`, `CONFIRMED`, `PROCESSING`, `SHIPPED`, `CANCELLED`, `RETURNED`, and `REFUNDED`; and
- calculate per-order merchandise spend as `sum(quantity × selling_price_snapshot) − order_discount`, in BDT. Do not use current product price, seller delivery cost, tax, payment state, general expenses, or profile fields.

A `RETURN_REQUESTED` record remains eligible because a request is not an accepted reversal. A fully `RETURNED` or `REFUNDED` record is excluded under the current CUSTOMER-03 rule. This is a current-ledger prototype basis, not an historical restatement of a segment after later status changes.

### 2.2 Required inputs

| Feature | Definition | Unit / period |
| --- | --- | --- |
| `as_of` | Required timezone-aware timestamp supplied server-side or validated by the API. Convert it and delivery timestamps to the configured store timezone before calendar-day comparison. | One explicit instant; no browser-timezone fallback. |
| `recorded_purchase_count` | Count of all eligible recorded purchases with `delivered_at <= as_of`. | Integer; retained-ledger history through `as_of`, not verified lifetime history. |
| `last_recorded_purchase_at` | Latest eligible `delivered_at <= as_of`. | Timestamp; null when count is zero. |
| `recency_days` | Store-local calendar days from `last_recorded_purchase_at` to `as_of`. | Integer. Same local date is `0`; future delivery evidence is excluded. |
| `trailing_365_day_spend_bdt` | Sum of eligible order merchandise spend whose local delivery date is within the inclusive 365 calendar days ending on the `as_of` local date. | BDT decimal; includes neither delivery cost nor non-merchandise costs. |

The feature query must use immutable order-line selling-price snapshots and order discounts. It must not infer missing history from zero rows. A customer with no eligible recorded purchase is `NO_RECORDED_ELIGIBLE_PURCHASE`, not a proven new customer.

## 3. Fixed prototype thresholds

The following simple, reviewable values are chosen for the capstone prototype. They are not learned from data and must be returned with any future segment result.

| Parameter | Value | Reason for prototype use |
| --- | --- | --- |
| New-customer recency | 0–30 days inclusive | Clearly separates a first recorded purchase in the most recent month. |
| Active-recency ceiling | 90 days inclusive | Gives a consistent active/inactive boundary without a hidden model. |
| Inactive boundary | 91 or more days | Starts on the calendar day after the active ceiling. |
| High-value lookback | 365 local calendar days inclusive | Keeps the spend threshold recent and explicit. |
| High-value spend | BDT 10,000.00 or more | Fixed BDT capstone threshold; never inferred from personal traits. |
| High-value frequency | At least 2 eligible recorded purchases | Prevents one unusually large first purchase from receiving the high-value label. |

## 4. Segments and precedence

Exactly one label is assigned. Evaluate this table in order; the first matching rule wins.

| Priority | Segment | Rule | Explanation returned to seller |
| ---: | --- | --- | --- |
| 1 | `NO_RECORDED_ELIGIBLE_PURCHASE` | `recorded_purchase_count = 0` | No eligible purchase is recorded under the current store ledger rule; this does not prove the customer is new. |
| 2 | `INACTIVE` | Count is at least 1 and `recency_days >= 91` | The most recent eligible recorded purchase is outside the 90-day active window. This takes precedence over past spend. |
| 3 | `HIGH_VALUE` | `recency_days <= 90`, count is at least 2, and `trailing_365_day_spend_bdt >= 10000.00` | Active repeat recorded behavior meets the fixed recent-spend threshold. |
| 4 | `REPEAT` | `recency_days <= 90` and count is at least 2 | Active customer has two or more eligible recorded purchases but did not meet the high-value rule. |
| 5 | `NEW` | `recency_days <= 30` and count is exactly 1 | One eligible recorded purchase occurred in the latest 30 local calendar days. |
| 6 | `ACTIVE_ONE_TIME` | Count is exactly 1 and `31 <= recency_days <= 90` | One eligible recorded purchase is still inside the active window but is not new. |

`INACTIVE` intentionally overrides a historical high spend. `HIGH_VALUE` intentionally overrides `REPEAT`. `NEW` and `ACTIVE_ONE_TIME` only apply to exactly one recorded eligible purchase, so every record has one explainable outcome.

## 5. Data quality, privacy, and exclusions

- The segment query must use only the authorized store's orders and customer ID; it must not reveal another store's history.
- A label must not include customer email, phone, address, age, gender, inferred trait, message content, or private provider context.
- If the store timezone, `as_of`, or required order evidence is invalid, return a validation/error state rather than substitute UTC, the browser timezone, or zero values.
- A zero trailing spend is not enough to conclude data coverage is complete. The label describes the recorded ledger basis only.
- Clustering, RFM scoring, trends, churn probability, forecast, discounts, customer ranking, and automated messaging are out of scope. No AI/LLM calculation is allowed for this segmentation rule.

## 6. Synthetic worked examples

The versioned examples are in `backend/tests/segment_cases/v1.json`. Each uses `as_of = 2026-07-01` in the store timezone and is validated by `backend/tests/test_segment_case_set.py`.

| Example | Recorded features | Expected segment | Why |
| --- | --- | --- | --- |
| New boundary | 1 purchase, recency 30 days, BDT 500.00 trailing spend | `NEW` | Latest 30-day first recorded purchase. |
| Active one-time boundary | 1 purchase, recency 31 days, BDT 500.00 trailing spend | `ACTIVE_ONE_TIME` | First day after new window, still active. |
| Repeat | 3 purchases, recency 2 days, BDT 9,999.99 trailing spend | `REPEAT` | Active repeat behavior remains below high-value spend threshold. |
| High value | 2 purchases, recency 10 days, BDT 10,000.00 trailing spend | `HIGH_VALUE` | Meets both repeat and threshold rules. |
| Inactive precedence | 3 purchases, recency 91 days, BDT 12,000.00 trailing spend | `INACTIVE` | Inactivity overrides historical recent-window spend. |
| No-recorded boundary | 0 purchases, no last purchase, BDT 0.00 trailing spend | `NO_RECORDED_ELIGIBLE_PURCHASE` | Absence of a ledger purchase is not labelled new. |

## 7. Implementation/test handoff

A later SEGMENT-02 service must centralize these constants, calculate the listed features from same-store order records, return the label plus features/thresholds/basis version, and use the manifest examples without duplicating eligibility arithmetic. It must preserve the customer-history rule until an approved order-return historical-restatement policy replaces it.
