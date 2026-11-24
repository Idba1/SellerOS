# SellerOS test-only synthetic demo data

`seed_demo_data --reset` creates a repeatable, fully fictional demo graph from the reviewed DATA-02 and DATA-03 manifests. Every run is labeled `SYNTHETIC DATA — NOT SELLER PERFORMANCE` and creates two isolated stores, five products, four customers without contacts, three supported delivered orders, and three categorized expenses. It deliberately excludes cancellation, return, refund, forecast, analytics, and any real customer data.

## Safety boundary

The command requires the explicit `--reset` flag and refuses to run unless both conditions hold:

1. Django `DEBUG` is `True`.
2. The selected PostgreSQL database name begins with `test_`.

It removes and rebuilds only the graph generated for the fixed synthetic demo owner accounts. It cannot reset a local, shared, or production database. Run it only in an isolated Django test workflow; the command is exercised by:

```powershell
backend\.venv\Scripts\python.exe backend\manage.py test core.test_demo_seed --noinput --verbosity 1
```

The test executes the command twice and verifies the same expected record counts, 12 status events, and BDT 520.00 total expenses. It also proves the production/debug and non-test-database guards.

## Remaining boundary

**[DECISION REQUIRED] DATA-01-R1:** persistent local-demo reset, retention, operator authorization, backups, and deletion procedure remain unapproved. Do not weaken the test-only guard or use this command against a persistent database.
