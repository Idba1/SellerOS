# Backend health and readiness — BACKEND-03

9 October 2026. Both public probe routes support GET/HEAD only; writes return 405. They expose no seller records, credentials, database names/hosts or exception text. Responses have no-store cache directives. No authentication defaults for business APIs are changed.

| Route | Meaning | Response |
| --- | --- | --- |
| `/health/` | Process liveness; no dependency access | 200 `{"status":"ok"}` (existing payload preserved) |
| `/ready/` | Process plus configured default DB query | 200 `{"status":"ready","checks":{"app":"ok","database":"ok"}}` |
| `/ready/` | Missing/dummy DB configuration | 503 `{"status":"not_ready","checks":{"app":"ok","database":"not_configured"}}` |
| `/ready/` | Query failure or unexpected result | 503 `{"status":"not_ready","checks":{"app":"ok","database":"unavailable"}}` |

Readiness runs read-only `SELECT 1` and expects `(1,)`. It verifies a query, not migrations, schemas, permissions for business tables, provider availability or deployment security. Only default database is probed. No driver, database settings, migrations or provider calls are added. Backend currently has no database configuration, so 503/not_configured is expected. Connection/query timeout policy must be configured with the later PostgreSQL task; this route does not promise bounded latency for an unconfigured future driver. Liveness does not fail merely because the database is unavailable.

Implementation lives in `core/health.py`; `core/views.py` keeps its former health import compatible; URL names are health/readiness. Existing Django JSON probes are not DRF error envelopes. Dependency exceptions become generic status, never response traces, including when DEBUG is enabled.

## Verification

Initial `git status --short --branch`: clean main tracking origin/main. Inspected views, URL configuration, settings and health tests. No AGENTS.md was found by the scoped file search.

Commands: `backend/.venv/Scripts/python.exe backend/manage.py check` and `... check --settings=config.settings.test`: both no issues (process-only generated test secret cleared afterward). `... test core --settings=config.settings.test`: first run hit sandbox TEMP permissions in three pre-existing env-reader tests. Reran with TEMP/TMP set for that command to workspace `backend/.venv/test-temp`: **17 tests passed**. The four new readiness tests cover unconfigured DB, simulated successful SELECT, sanitized operational/unexpected failures with independent liveness, unexpected results and methods/cache behavior. Configured-DB cases are mocked; no live PostgreSQL readiness claim.

Live attempts inside the sandbox could not reliably access loopback sockets (socket access denied). Authorized elevated verification ran `manage.py runserver 127.0.0.1:18766 --noreload` with explicit local settings and a generated process-only secret: exact health HTTP 200 and readiness HTTP 503/not_configured JSON assertions passed. The server was terminated and waited for in finally. No secret values printed. `git diff --check` and no-index checks for new files reported no whitespace errors. Final working branch was backend; the agent did not switch branches. Only health/routes/tests and related documentation changed; no commit made. Next dependency: BACKEND-04 — PostgreSQL development/test database configuration, only when authorized.
