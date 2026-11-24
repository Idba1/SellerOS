# FORECAST-01 — Historical Sales Data Audit

**Status:** reproducible delivery-history audit only. No model, forecast, accuracy score, horizon, recommendation, or automated action is implemented.

## 1. Audit source and scope

`backend/apps/forecast/audit.py` inspects one server-resolved store using immutable `OrderStatusEvent` rows whose `to_status` is `DELIVERED`. It reports the original delivery-event timestamp in the store's configured IANA timezone. It never accepts a client store ID and returns no customer names, contacts, addresses, or message data.

The audit is deliberately separate from a forecast series. It identifies whether delivery evidence is usable enough for later policy review; it does not select daily/weekly buckets, impute missing observations, calculate demand, normalize data, train a model, or emit a number that represents future sales.

## 2. Reproducible output

For a server-authorized store, `audit_store_delivery_history(store=store)` returns:

| Audit field | Meaning |
| --- | --- |
| `raw_delivery_event_count`, `unique_delivery_order_count` | All original `DELIVERED` events and their order identities before validation. |
| `valid_delivery_event_count`, `duplicate_delivery_order_count` | Events usable for the date series after excluding every order with duplicate delivery evidence; duplicates are not silently selected. |
| `date_span_start`, `date_span_end`, `calendar_day_count` | Store-local span of valid original delivery events. Empty history is explicitly null/zero. |
| `days_with_valid_deliveries`, `gap_day_count`, `gap_ranges` | Observed local calendar coverage and missing date ranges inside the span. A gap is not treated as known zero demand. |
| `products_with_valid_delivery_count`, `valid_delivery_orders_without_items_count` | Product coverage from immutable order lines and missing-line anomalies. |
| `return_requested_order_count`, `returned_or_refunded_order_count` | Current return-related statuses among valid original deliveries; these identify records needing an approved return-series policy. |
| `observed_granularity` | Event timestamps with a store-local daily-coverage audit; it is not a selected forecast bucket. |
| `forecast_training_permitted`, `limitation_codes` | Always `false` in FORECAST-01 plus explicit limitations; this audit cannot authorize a model. |

The source is intentionally the original delivery event, matching existing analytics. Current order status is used only to count return-related records; it does not remove original delivery evidence or create a negative demand event.

## 3. Repository synthetic-data audit

The reviewed static source [synthetic time-series manifest](../data/sample/synthetic-orders-expenses-timeseries.v1.json) is labeled **SYNTHETIC DATA — NOT SELLER PERFORMANCE**. It contains four original delivered events across two isolated stores:

| Store fixture | Original delivery dates | Product coverage | Return evidence | Observed limitation |
| --- | --- | --- | --- | --- |
| `synthetic-store-a` | 2026-01-07, 2026-02-06, 2026-03-04 | Three product records, one delivery each | One later accepted return on 2026-03-10 | 57-day span with 54 unobserved dates; no coverage flag, stockout annotation, or approved return-series handling. |
| `synthetic-store-b` | 2025-10-04 | One product record | None in the manifest | One observed date only; no span for a time-series evaluation. |

The manifest has no repeated delivered `fixture_key`/source-order combination. This is a static-manifest observation, not a production database integrity guarantee. The seeded demo command loads only its supported delivered-order subset, so it must not be represented as a complete return/refund or demand history.

## 4. Approved current-prototype forecast decision

**Decision:** SellerOS will not generate, display, or evaluate a numerical demand forecast from the currently audited history. Every FORECAST-01 audit result has `forecast_training_permitted: false` and the limitation `current_audit_does_not_authorize_forecast_training`.

This is a data-quality decision, not a claim that zero observations equal zero demand. The available repository fixtures are synthetic, sparse, have unobserved calendar gaps, have no universal coverage/stockout marker, and include a return-related record. Calling a forecast reliable under these conditions would be misleading.

The audit always retains `history_coverage_unknown` because current records have no universal ingestion/observation-coverage flag. It additionally reports duplicate delivery evidence, within-span calendar gaps, empty item records, and return-related records when found.

Any future numerical forecasting work requires a separately authorized task to introduce a reviewed coverage source, return-series treatment, granularity/horizon, sufficiency gate, and past-only evaluation method. FORECAST-01 makes none of those calculations and does not infer them from the current sparse data.

FORECAST-02 documents unapproved candidate gates and explicit insufficient-history disclosures in [forecast-method.md](forecast-method.md). It does not change FORECAST-01's current no-training outcome.

## 5. Verification evidence

```powershell
& .\backend\.venv\Scripts\python.exe .\backend\manage.py test apps.forecast.tests apps.analytics.tests.test_sales tests.test_sample_synthetic_time_series --verbosity 2
```

Observed result: **8 tests passed**. Django created and destroyed a disposable PostgreSQL test database and reported no system-check issues. The focused test builds only synthetic records and verifies store isolation, date span, two single-day gaps, product coverage, duplicate-event exclusion, current return counts, empty history, and the no-training gate. It does not modify a real store dataset or call a provider.
