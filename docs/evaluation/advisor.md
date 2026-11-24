# ADVISOR-05 Evaluation Report — Deterministic Factuality and Usefulness

**Report revision:** 1

**Observed on:** 24 November 2026

**Repository baseline:** `0b5bc63` on `main` (ADVISOR-03)

**Data classification:** synthetic-only

**Provider state:** disabled; no external provider/model request was made.

## Scope and evaluation boundary

This report evaluates the deterministic advisor boundary implemented in ADVISOR-01 through ADVISOR-03: same-store context construction, bounded metric prompting, structured insight selection, deterministic template rendering, and disabled/provider-error fallback. The versioned rubric and case-to-test traceability manifest is `backend/tests/advisor_cases/evaluation-v1.json`.

It is a qualitative engineering review of evidence consistency and reviewer-facing clarity. It does **not** use subjective ratings as proof of seller usefulness, business impact, model quality, or financial outcome.

ADVISOR-04 was not present in the inspected repository history at this evaluation baseline. Therefore no advisor API, browser workflow, authenticated endpoint response, or provider-backed generation is claimed here.

## Rubric

| Dimension | Reviewed requirement | Evidence boundary |
| --- | --- | --- |
| Evidence consistency | Rendered values, source endpoints, periods, and warnings come from the authorized deterministic context. | Fixed synthetic context and response metadata only. |
| Scope and clarity | A reviewer can see the selected metric's period/scope and limitation. | Template and warning wording only; not a human-comprehension study. |
| Unsupported-claim safety | Free text or unsupported/context-incompatible selections abstain. | Validator adversarial cases only; not all live-model attacks. |
| Missing-data disclosure | Incomplete profit evidence suppresses numeric profit/margin and exposes completeness. | Synthetic missing-cost context only. |
| Failure and privacy boundary | Disabled/provider failure stays unavailable; bounded prompt excludes customer identifiers. | Mock provider and in-process prompt inspection only. |

## Observed execution evidence

Environment observed: Windows local development environment, Python `3.12.14`, PostgreSQL disposable Django test database.

```powershell
& .\backend\.venv\Scripts\python.exe .\backend\manage.py test apps.advisor.tests tests.test_advisor_case_set tests.test_advisor_evaluation_manifest --verbosity 2
```

Observed result: **12 tests passed**. Django created and destroyed the disposable `test_selleros_dev` database and reported no system-check issues.

## Observed case results

| Evaluation case | Observation | Result |
| --- | --- | --- |
| ADVISOR-EVAL-001 Evidence consistency | Selected sales/profit/stock templates rendered fixed synthetic values and supplied source, period, timezone, and warning metadata. | PASS |
| ADVISOR-EVAL-002 Scope and clarity | Sales used an explicit half-open delivery-event interval, profit used an inclusive store-local range, and stock was marked current state. | PASS |
| ADVISOR-EVAL-003 Unsupported claim safety | Candidate output containing a free-text profit/discount claim became `abstain`; it retained no explanation or evidence. | PASS |
| ADVISOR-EVAL-004 Missing data disclosure | A synthetic unavailable-profit context emitted no numeric profit/margin and retained its completeness status. | PASS |
| ADVISOR-EVAL-005 Failure safety | Disabled and mocked transport-error states returned generic `unavailable`; the simulated transport detail was not returned. | PASS |
| ADVISOR-EVAL-006 Privacy boundary | The bounded prompt retained approved metrics but excluded customer ID and purchase-history fields. | PASS |
| ADVISOR-EVAL-007 Store isolation | Foreign optional product/customer evidence was rejected before context construction. | PASS |

## Qualitative usefulness finding

For the tested deterministic templates, the response is concise enough for seller review because each statement identifies its metric, period/state, and limitation rather than implying a forecast or recommendation. This is a design observation from template inspection, **not** a user-study score or proof that sellers make better decisions.

## Limitations and non-evaluated claims

- No provider/model is approved or enabled under PLAN-06. Live-provider factuality, instruction-following, latency, token use, cost, retention, and provider error rate are **NOT EVALUATED**.
- The test contexts are synthetic and do not establish accuracy, usefulness, or impact on real seller data.
- No ADVISOR-04 API or browser end-to-end implementation was found at the baseline, so authentication-to-response behavior is **NOT EVALUATED** here.
- This review does not evaluate forecasts, recommendations, rankings, causal claims, or formal financial/accounting assertions; the specification forbids them.
- The in-process prompt check demonstrates the covered customer fields are absent; it is not a complete privacy audit.

## Conclusion

**Deterministic evidence-bound advisor behavior: PASS for the listed synthetic cases.** The implementation demonstrated safe explanations, abstention, and disabled-provider fallback under the covered conditions. **Live AI quality and business usefulness: NOT EVALUATED.**
