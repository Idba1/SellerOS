# FORECAST-03 through FORECAST-10 — Method, Evaluation, and Limits

**Implemented policy:** `forecast-v1-daily` is a deterministic, product-specific daily demand prototype. It uses immutable original delivery events, store-local dates, an explicit 56-day complete-history / 14-nonzero-day gate, and a next-7-day horizon. No random split is used.

## Dataset and leakage boundary

`build_daily_product_series` preserves product ID and chronological dates. It fills a missing daily bucket with zero only when server-owned coverage metadata says the period is complete. Unknown coverage, duplicate delivery evidence, terminal returns/refunds, or missing item rows block the output. No current price, cost, customer data, future order field, or future normalization enters the series.

## Methods and evaluation

- Baseline: trailing seven-day arithmetic mean.
- Candidate: seven-day seasonal-naive replay.
- Evaluation: expanding chronological cutoffs beginning after 56 days, each predicting the following seven days. MAE and RMSE aggregate all held-out predictions; no random shuffle, final-test tuning, or accuracy threshold is claimed.
- Selection: use seasonal naive only when its observed MAE is strictly lower than the baseline's on the eligible chronological folds; otherwise use the baseline.

## Current data and service states

The repository's reviewed sample fixtures fail coverage, volume, gap, and return-treatment gates. `forecast_product_demand` therefore returns `insufficient_history`, no method, and no estimates for that data. A complete synthetic 70-day series is used only to verify reproducibility and leakage boundaries; it is not seller performance or real-world accuracy evidence.

## Observed verification

The forecast pipeline tests verify insufficient history, chronological reproducibility, non-negative outputs, duplicate/return blocking, and rolling-fold evaluation. No scikit-learn/XGBoost dependency, LLM, external provider, browser key, autonomous action, or production forecast is used.
