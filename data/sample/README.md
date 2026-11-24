# Sample synthetic data

This directory contains reviewed, static fixtures only. It is not a production dataset, database dump, or automatic seed mechanism. The guarded `seed_demo_data --reset` command may read the supported subset only inside a disposable Django test database; it never loads these fixtures into a local, shared, or production database.

- [Synthetic catalog and customer manifest](synthetic-catalog-customers.v1.json) is fully fictional, repeatable, and labeled `SYNTHETIC DATA — NOT SELLER PERFORMANCE`.
- It provides product/variant and customer-history **fixture references**. The test-only command loads its product/customer rows, while customer-history stubs remain non-persisted references.
- [Synthetic orders, expenses, and time-series manifest](synthetic-orders-expenses-timeseries.v1.json) supplies chronological fixture references for approved delivered, missing-cost, cancellation, accepted-return, expense, and sparse-history cases. The test-only command loads only the supported delivered-order and categorized-expense subset; cancellation, return, refund, inventory-restoration, and analytics cases remain fixture-only.
- All customer contact fields are null. Do not add real customer records, credentials, provider keys, addresses, payment details, or production exports.

Follow the [synthetic data policy](../../docs/test-data-policy.md) before adding or loading any fixture.
