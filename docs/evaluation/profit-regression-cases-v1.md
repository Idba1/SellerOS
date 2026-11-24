# Profit regression cases v1

This versioned, synthetic case set independently checks the public profit API against the approved `PROFIT-01` formula. It is not seller performance, accounting advice, an AI/ML evaluation, or a production data export.

Implementation source: `backend/apps/profit/tests/profit_cases.py` (`profit-regression-v1`). The executable regression test creates records in Django's isolated PostgreSQL test database, calls `GET /api/v1/profit/summary/`, and compares the returned totals with the hand-calculated values below.

## Fixed context

- Store timezone: `Asia/Dhaka`
- API period: 1–31 January 2026, inclusive store-local dates
- Currency: BDT, two decimal places, `ROUND_HALF_UP`
- All records are synthetic and same-store.
- Formula: `net revenue − product cost − seller delivery cost − recorded operating cost`

## Cases

| Case ID | Inputs | Independent calculation | Expected API outcome |
| --- | --- | --- | --- |
| `discount-delivery-expense` | 2 × 100.00; cost 40.00 each; saved discount 10.00; delivery 15.00; expense 20.00 | Revenue `(200 − 10) = 190.00`; COGS `2 × 40 = 80.00`; profit `190 − 80 − 15 − 20 = 75.00`; margin `75 / 190 × 100 = 39.47%` | Complete; BDT 75.00 estimated profit and 39.47% margin. |
| `missing-product-cost` | 1 × 100.00; product cost `NULL`; delivery 0.00; expense 12.00 | Revenue is 100.00, but COGS is unknown. It is not BDT 0.00. | `unavailable_missing_product_cost`; product cost, profit, and margin are `null`. |
| `missing-delivery-cost` | 1 × 100.00; cost 40.00; delivery cost `NULL`; expense 12.00 | Revenue and COGS are known, but delivery cost is unknown. It is not BDT 0.00. | `unavailable_missing_delivery_cost`; delivery cost, profit, and margin are `null`. |
| `zero-sales-with-expense` | No delivery event; expense 25.00 | Revenue, COGS, and delivery cost are 0.00; profit `0 − 0 − 0 − 25 = -25.00`; margin has a zero denominator. | Complete BDT -25.00 estimated profit; margin is `null`. |

## Audit rules

1. A regression case must use immutable price/cost snapshots and saved discount allocation; it must not use a current product price or cost.
2. Missing costs must produce an unavailable numeric profit, not a fabricated zero-cost value.
3. Zero sales is distinct from missing data: it has zero known sales components and may have a negative result from recorded expenses.
4. Each test calls the authenticated, store-scoped API and verifies its documented formula string as well as numeric totals.
5. The case set contains no customer contact details, secrets, real seller data, provider interaction, forecast, recommendation, tax, or formal accounting output.

## Reproduction

From the repository root:

```powershell
& .\backend\.venv\Scripts\python.exe .\backend\manage.py test apps.profit.tests.test_profit_regression_cases --noinput --verbosity 1
```

Expected result: one test method with four synthetic subcases passes. Record any future change to case values, formula, expected status, or rounding as a new case-set version rather than silently editing `v1`.
