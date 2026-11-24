# FORECAST-10 Evaluation Report — Daily Prototype

**Data:** synthetic-only. **Policy:** `forecast-v1-daily`. **Environment:** local Python 3.12 / Django test suite. No provider, LLM, browser key, or external action was used.

## Method and observed evidence

The implemented prototype builds chronological product/day points only from immutable original delivery events. It requires 56 complete daily buckets, 14 nonzero days, no duplicate delivery evidence, and no terminal return/refund records. Baseline is a trailing seven-day mean; candidate is a seven-day seasonal-naive replay. Expanding chronological folds evaluate only future seven-day blocks using MAE/RMSE; random splitting is prohibited.

The current reviewed repository fixture is insufficient and correctly returns `insufficient_history` with no estimate. A separate fixed 70-day synthetic series verifies the pipeline mechanics only; it is not seller performance and no real-world accuracy score is claimed.

## Observed checks

`python backend\manage.py test apps.forecast.tests.test_pipeline tests.test_forecast_eligibility_policy --verbosity 2` passed 5 tests: insufficient-data refusal, chronological reproducibility, non-negative outputs, duplicate/return blocking, and policy-manifest consistency.

## Limitations

- No real seller history or forecast accuracy is evaluated.
- No model is trained, tuned, or compared on a final test set.
- Current repository fixture coverage is unknown/sparse and includes a return; it remains unavailable for numerical output.
- The prototype's daily thresholds/method are an explicit engineering policy, not a guarantee of demand, growth, profit, or customer behavior.
