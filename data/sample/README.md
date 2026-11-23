# Sample synthetic data

This directory contains reviewed, static fixtures only. It is not an import source, production dataset, database dump, or automatic seed mechanism.

- [Synthetic catalog and customer manifest](synthetic-catalog-customers.v1.json) is fully fictional, repeatable, and labeled `SYNTHETIC DATA — NOT SELLER PERFORMANCE`.
- It provides product/variant and customer-history **fixture references** for future approved product/customer/order work. The Product, ProductVariant, Customer, and SalesOrder models/API routes do not exist yet, so this manifest must not be loaded into the current database.
- [Synthetic orders, expenses, and time-series manifest](synthetic-orders-expenses-timeseries.v1.json) supplies chronological fixture references for approved delivered, missing-cost, cancellation, accepted-return, expense, and sparse-history cases. It is not an order/expense/inventory database seed or analytics output.
- All customer contact fields are null. Do not add real customer records, credentials, provider keys, addresses, payment details, or production exports.

Follow the [synthetic data policy](../../docs/test-data-policy.md) before adding or loading any fixture.
