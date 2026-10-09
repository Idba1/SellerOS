# Backend

## Health and readiness — BACKEND-03

`GET /health/` retains process liveness (200/status ok). `GET /ready/` separately probes database readiness; the current unconfigured database returns 503/not_configured. See [route payloads, limits and verification](../docs/setup/health-readiness.md). The suite now has 17 tests; database success/failure cases are mocked. No database configuration or provider check is implemented. Next task: BACKEND-04.

## DRF baseline — BACKEND-02

DRF is now installed with JSON-only parsing/rendering, fail-closed permission defaults and a small shared error handler. See [response/error convention and exact checks](../docs/setup/drf-baseline.md). Existing health behavior is unchanged. The core suite now has 13 tests; older counts below are historical. Authentication, store permission enforcement, database and business APIs remain later tasks.

## Current settings — BACKEND-01

Environment-specific settings now live under `config/settings/`: shared base, local and test modules. Entry points default to `config.settings.local`; explicitly use `.local` or `.test`, not the bare namespace. See [environment configuration](../docs/setup/environment.md#current-behavior) for flag validation, timezone/static/media policy and exact mode checks. Use `--settings=config.settings.test` for explicit test-mode runs. All modes require the process secret. The current suite has **six** passing tests in both local and test modes; historical test counts below refer to earlier tasks. Database configuration remains absent. Next task: BACKEND-02, only when authorized.

SETUP-04 minimal Django 5.2.17 skeleton using Python 3.12.14. `config/` contains settings/URLs/ASGI/WSGI; `core/` exposes only public process liveness at `GET /health/` (HEAD also supported). Response: HTTP 200, `{"status":"ok"}`. Writes return 405. This is not database/provider readiness or authentication; no seller records exist or are exposed.

From repository root, use the pinned Python to create `backend/.venv`, then install `backend/requirements.txt`:

```powershell
python -m venv backend/.venv
& backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
# Generate a temporary process secret without printing or saving it.
$env:DJANGO_SECRET_KEY = (& backend/.venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(64))")
& backend/.venv/Scripts/python.exe backend/manage.py check
& backend/.venv/Scripts/python.exe backend/manage.py test core
& backend/.venv/Scripts/python.exe backend/manage.py runserver 127.0.0.1:8000 --noreload
```

Python is currently available via the bundled absolute path recorded in the root README rather than PATH; substitute that executable for `python` when creating the environment. A missing/blank `DJANGO_SECRET_KEY` fails startup. Local settings load private backend/.env without a dependency; exported values take precedence. Test settings do not load it. Clear the temporary variable after stopping the server with `Remove-Item Env:DJANGO_SECRET_KEY`.

Settings keep DEBUG off and allow loopback hosts only. No database is configured, migrations run, admin/session/auth app added, or business timezone selected. DRF baseline, environment-specific settings and PostgreSQL configuration belong to later tasks. This local skeleton is not deployment-ready. No business-rule decisions are resolved here.

## SETUP-04 verification — 6 October 2026

- Inspected `git status --short --branch`, `.python-version` and `rg --files backend`: clean `setup` branch, Python pin 3.12.14, only the backend placeholder.
- Bundled Python `-m pip index versions Django` confirmed 5.2.17 available in the compatible 5.2 series; a pip self-update-check warning did not prevent the query.
- Created isolated `backend/.venv` using the verified bundled Python; `-m pip install --disable-pip-version-check Django==5.2.17` succeeded. `pip freeze` matches all four exact requirements. No global/bundled packages were modified.
- `backend/.venv/Scripts/python.exe backend/manage.py check`: no issues.
- `backend/.venv/Scripts/python.exe backend/manage.py test core`: 3 tests passed, no database required.
- `backend/.venv/Scripts/python.exe -m pip check`: no broken requirements.
- Inline Python launched `runserver 127.0.0.1:18764 --noreload`, requested `/health/` with urllib and asserted HTTP 200 and exact JSON; passed. It terminated the server in `finally`; its random environment secret was neither printed nor saved.
- `git diff --check`: no tracked whitespace errors. `git check-ignore backend/.venv/Scripts/python.exe`: ignored as expected. Status shows only backend skeleton files/README changes; no database, secrets, frontend changes or business modules created. New source files were separately checked with `git diff --no-index --check -- NUL <file>`.

No commit or push performed during SETUP-04.

## Current local workflow — SETUP-07

Follow the [root setup/run guide](../README.md#local-setup-and-run--setup-07) for pinned Python provisioning, isolated install, tests, two-terminal startup and shutdown. The current core suite has **four** tests (including missing and example-secret rejection). No migration command is applicable while `DATABASES = {}`; the root guide lists future showmigrations/migrate commands and their PostgreSQL prerequisites without claiming database readiness.

6 October 2026 clean rehearsal: created a separate `backend/.venv-rehearsal` using pinned Python; installed `-r backend/requirements.txt`; ran `manage.py check` (no issues), `manage.py test core` (4 passed) and `pip check` (no broken requirements). An inline Python process supervisor ran that environment's `manage.py runserver 127.0.0.1:8000 --noreload`, verified exact HTTP 200 health JSON, then terminated/waited for the process in `finally`. The temporary secret was process-only. The separate environment was removed afterward; existing `.venv` preserved. No migration, database/provider call, or real data was used. Shutdown must stop the actual server process, not just its terminal wrapper.

Local env-loading fix: nine tests passed in test mode. `manage.py check` and live `runserver` health request passed without an exported secret after replacing the private file's example marker with a generated local value. The ignored file was not displayed or committed; verification server stopped.
