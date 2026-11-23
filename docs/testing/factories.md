# Shared backend test factories — DB-05

## Purpose

`backend/tests/factories/` provides dependency-free, deterministic builders for the only implemented tenant graph: `Account` → `Store` → optional `StoreMembership`. They reduce duplicated setup while preserving the approved one-store owner/staff model.

Factories use synthetic `@example.test` identities and the constant test-only password `synthetic-test-password-not-a-real-credential`. They must never receive or embed a real email, customer record, credential, provider key, address, message, payment detail, or production export.

## Usage convention

Create a fresh `FactoryContext` inside every test. Its namespace and counters make generated values reproducible without random generators or global state.

```python
from tests.factories import FactoryContext, create_store_graph


def test_example(self):
    graph = create_store_graph(FactoryContext(namespace="orders"))
    owner = graph.owner
    store = graph.store
    staff = graph.staff
```

`create_store_graph()` creates one owner, one BDT/`Asia/Dhaka` store, and one active staff membership by default. Set `include_staff=False` for an owner-only graph or `staff_active=False` for a revoked-staff case. `create_account`, `create_store`, and `create_staff_membership` remain available for focused tests.

## Boundaries and future additions

Only implemented models belong in this factory package. Product, inventory, customer, order, expense, analytics, API, and frontend factories must be added with their own approved model/API tasks; do not simulate missing endpoints or fabricate business outcomes here.

Every test must use a unique namespace when it creates multiple graphs in one database transaction. The factories do not bypass `full_clean`, PostgreSQL uniqueness/check constraints, store ownership, or membership constraints. They are test setup helpers, not a production registration, authorization, or fixture-import mechanism.
