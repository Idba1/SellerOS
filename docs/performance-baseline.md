# Analytics query-budget baseline

## Purpose and boundary

This is a regression baseline for the authenticated `GET /api/v1/analytics/product-performance/` request path.  It measures one narrowly defined synthetic scenario; it is not a production capacity claim, an API latency SLA, or a forecast of performance with a larger dataset.

## Baseline scenario

The automated query-budget test creates the following entirely synthetic graph in the isolated Django PostgreSQL test database:

- one store, one active staff member, and token authentication;
- one product;
- one delivered order with one order item (quantity 2 at BDT 100.00); and
- an `Asia/Dhaka` period of `2026-01-01T00:00:00+06:00` through `2026-02-01T00:00:00+06:00`.

`backend/apps/analytics/tests/test_query_budget.py` captures SQL only around the HTTP request.  The baseline budget is **at most six SQL queries**: token authentication, store resolution, delivery evidence, prefetched order lines, duplicate-delivery validation, and the staff-membership lookup.  An implementation that uses fewer queries still satisfies the budget.

The test intentionally does not assert a wall-clock maximum because a local test runner's time includes machine load, database startup, and debug tooling.  The measurement command below records the repeatable test-harness duration without turning ordinary local variation into a false failure.

## Recorded execution environment

Measurement date: 2026-11-24 (Asia/Dhaka).

| Component | Verified value |
| --- | --- |
| Runtime | Python 3.12.14 |
| Framework | Django 5.2.17; Django REST Framework 3.18.3 |
| Database mode | Django isolated PostgreSQL test database |
| PostgreSQL client | psql 17.4 |
| Data source | Test-created synthetic records only |

Recorded result: the command below completed in **2,619 ms** wall-clock time; Django reported **0.770 s** for the single test.  The run created and destroyed a fresh test database.  This is a local harness measurement, not endpoint latency or a production target.

## Repeatable measurement command

From the repository root in PowerShell, run the query budget test and capture the harness duration:

```powershell
$measurement = Measure-Command {
  & .\backend\.venv\Scripts\python.exe .\backend\manage.py test apps.analytics.tests.test_query_budget --noinput --verbosity 1
}
$measurement.TotalMilliseconds
```

Use the result only to compare like-for-like local executions: same command, virtual environment, PostgreSQL configuration, and synthetic test shape.  Record a new measured value only after running this command, with the date and environment values above (or their verified replacements).  Do not compare it to a production SLA.

## [DECISION REQUIRED]

- Define an approved representative data volume and a production-like environment before establishing a latency target.
- Decide whether analytics endpoints need pagination or database indexes after measured growth demonstrates a need; no index or response-shape change is implied by this small baseline.
