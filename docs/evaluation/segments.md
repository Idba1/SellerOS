# SEGMENT-05 Evaluation Report — Edge Cases and Stability

**Report revision:** 1

**Observed on:** 24 November 2026

**Repository baseline:** `58d6884` on `main` (SEGMENT-03)

**Data classification:** synthetic-only

## Scope and boundary

This report evaluates the deterministic, same-store segment implementation from SEGMENT-01 through SEGMENT-03. It tests purchase-derived feature calculation, fixed rule precedence, explanations, threshold equality, and repeatability for tied delivery timestamps. It does not evaluate customer worth, future purchasing behavior, churn, recommendation effectiveness, clustering, or a predictive model.

SEGMENT-04 was not present in the inspected repository history at this baseline. No frontend workflow, browser test, or additional segmentation integration is claimed by this report.

## Covered regression cases

| Case | Synthetic recorded history | Expected assignment and explanation behavior | Observed result |
| --- | --- | --- | --- |
| No orders | No eligible order | `NO_RECORDED_ELIGIBLE_PURCHASE`; explanation says absence in the current ledger does not establish lifetime/new status. | PASS |
| New boundary | One delivery exactly 30 local calendar days before `as_of` | `NEW`; explanation retains the 30-day boundary. | PASS |
| Repeat below threshold | Two active deliveries totaling BDT 9,999.99 | `REPEAT`; explanation states the exact spend is below high-value threshold. | PASS |
| High-value equality/tie | Two deliveries at the same timestamp totaling exactly BDT 10,000.00 | `HIGH_VALUE`; equal threshold is inclusive and the explanation states exact spend. | PASS |
| Inactive precedence | Two historical deliveries totaling BDT 12,000.00; latest is 91 days old | `INACTIVE`; inactivity overrides historic spend. | PASS |
| Tied-history stability | Same two-timestamp history evaluated twice | Identical assignment/features/explanation; local-date recency is stable. | PASS |

## Observed execution evidence

Environment observed: Windows local development environment, Python `3.12.14`, PostgreSQL disposable Django test database.

```powershell
& .\backend\.venv\Scripts\python.exe .\backend\manage.py test apps.segmentation.tests tests.test_segment_case_set --verbosity 2
```

Observed result: **13 tests passed**. Django created and destroyed the disposable `test_selleros_dev` database and reported no system-check issues.

The suite includes SEGMENT-03 API/auth/store-isolation tests, SEGMENT-02 feature tests, SEGMENT-03 rule-boundary tests, this SEGMENT-05 regression suite, and the SEGMENT-01 synthetic case-manifest test.

## Limitations

- All observed records are synthetic; the results are not evidence of real customer value, retention, business impact, or predictive accuracy.
- The current rule uses the CUSTOMER-03 current-status eligibility basis. It is not a historical restatement after later return/refund changes.
- No clustering, score, model, forecast, recommendation, automated contact, or customer treatment decision is implemented or evaluated.
- SEGMENT-04 was not found at the baseline, so frontend/end-to-end evidence is **NOT EVALUATED**.
- The fixed BDT thresholds are explainable prototype parameters, not learned or validated market thresholds.

## Conclusion

**Deterministic assignment stability: PASS for the listed synthetic edge cases.** Each covered case returned one documented assignment and its expected explanation. This result does not establish predictive customer value or business benefit.
