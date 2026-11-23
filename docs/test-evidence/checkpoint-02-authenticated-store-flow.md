# Checkpoint 02 — Authenticated store flow

## Scope and evidence

AUTH-06 verifies the implemented token API against Django's PostgreSQL test database. The executable evidence is `backend/tests/integration/test_authenticated_store_flow.py`, which uses only synthetic `@example.test` identities and no real credentials.

The flow asserts all of these checkpoints in one request sequence:

1. Register seller A and authenticate with its returned token.
2. Confirm that seller A has no store profile before onboarding (`404 not_found`).
3. Create seller A's first store through `POST /api/v1/stores/current/`.
4. Sign seller A in again with `POST /api/v1/auth/login/`, then verify `/api/v1/auth/me/` and `/api/v1/stores/current/` identify seller A and its store.
5. Register/onboard seller B as an independent seller.
6. Reuse seller A's signed-in token: its current-store read remains seller A's store; a foreign `store_id` selector returns `400 validation_error` and contains neither seller B's store ID nor name.

This is API end-to-end verification of the available implementation, not browser evidence. The frontend currently has no registration/login/store-onboarding screen or browser E2E runner, so this checkpoint does not claim a completed UI authentication journey. Store switching is out of scope under the approved one-store-per-account model; rejection of a selector is the expected behavior.

## Reproduction

From the repository root, with the configured PostgreSQL service available:

```powershell
& .\backend\.venv\Scripts\python.exe .\backend\manage.py test tests.integration.test_authenticated_store_flow --verbosity 2
```

Expected result: one test passes using a disposable PostgreSQL test database, and the test database is destroyed afterward. Run `python manage.py check` before the suite when validating a local environment.

## Limits and follow-up

AUTH-04 already covers unauthenticated, active-staff, and generic scoped-object negative cases. When product, order, inventory, customer, expense, or analytics APIs are introduced, add a corresponding two-store integration flow for each mutation and lookup path. No tenant switching endpoint should be added without a separately approved multi-store policy.
