# DATA-03 synthetic order, expense, and time-series fixture

The [DATA-03 manifest](../../data/sample/synthetic-orders-expenses-timeseries.v1.json) is a fully fictional, fixed fixture set labeled `SYNTHETIC DATA — NOT SELLER PERFORMANCE`. It extends the DATA-02 catalog/customer manifest through fixture keys only; it does not seed the database, create an API resource, or constitute seller performance evidence.

## Included cases

| Case | Approved behavior exercised | Boundary preserved |
| --- | --- | --- |
| Delivered normal order | Confirmation deducts once; delivery recognizes the exact recorded sale/cost once | Zero discount avoids unapproved rounding/allocation rules |
| Delivered missing-cost order | Delivery is present while cost remains unknown | No COGS or profit total is fabricated |
| Confirmed then cancelled order | Deduction is restored once; no completed-sale revenue/COGS | No cancellation refund is claimed |
| Delivered then accepted return | Accepted return restores stock and reverses delivery recognition once | No `REFUNDED` event or non-merchandise refund treatment is claimed |
| Sparse delivered order | An isolated chronological delivery exists for a second store | It is not a forecast or demand conclusion |
| General expenses | Positive standalone operating expenses are recorded | They are not allocated to orders/products or summed into profit |

`chronological_series_stubs` reference event times with explicit offsets. They are intentionally not bucketed by day/week/month and do not calculate a forecast, baseline, return adjustment, or store-local period total. DATA-03 therefore preserves PLAN-03 DR-07 and PLAN-05 forecast/segmentation decisions.

## Reconciliation scope

Each `reconciliation` block contains known expected amounts for that single synthetic case. Validation recomputes order gross from item snapshots and verifies the approved zero-discount totals, exactly-once deduction/restoration quantities, and visible missing-cost state. The normal delivered case reconciles to BDT 1,700.00 net and BDT 860.00 completed-sale COGS; the accepted full-return case reconciles to zero final recognized merchandise net/COGS after one reversal.

These are fixture-case checks only. They do not establish an aggregate profit figure, refund liability, financial statement, forecast accuracy, or real-world business result.

## Deferred decisions

The manifest deliberately avoids or defers:

- DR-01 New/PENDING naming choice;
- DR-03 cancellation refund representation;
- DR-04 Decimal precision, rounding, and discount allocation;
- DR-06 non-merchandise refund/delivery-cost treatment;
- DR-07 period grouping and return-period reporting;
- DR-08 snapshot-edit timing; and
- DATA-01-R1 persistent demo retention/reset approval.

The only executable check is the database-independent fixture validation test. A later product/order/inventory implementation must add its own PostgreSQL/API seed and cross-store tests before loading these values into a database.
