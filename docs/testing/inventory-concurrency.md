# Inventory concurrency test limits — INV-06

`backend/apps/inventory/tests/test_concurrency.py` runs against the configured PostgreSQL test database. It uses two Django worker threads with separate database connections and a start barrier. The tests verify these covered outcomes:

- two concurrent positive manual adjustments retain both ledger rows and both balance changes;
- two concurrent deductions that each fit the original balance allow only one deduction when their combined effect would overdraw stock;
- an injected failure after movement creation but before cached-balance persistence rolls back the movement and leaves the balance unchanged.

Run the focused suite with:

```powershell
.\backend\.venv\Scripts\python.exe .\backend\manage.py test apps.inventory.tests --verbosity 2
```

These tests provide evidence for the local PostgreSQL configuration and the service's `select_for_update` transaction boundary. They do not prove behavior under production connection-pool settings, multiple application hosts, database failover, process termination, long-running lock contention, or order-item workflows that do not exist yet. They also do not replace an operational load/concurrency test before production deployment.

The expected implementation contract remains: all stock writes use `apply_stock_adjustment`; direct ORM updates and future order deductions must not bypass this service. No new business rule is selected by INV-06.
