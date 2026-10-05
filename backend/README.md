# Backend

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

Python is currently available via the bundled absolute path recorded in the root README rather than PATH; substitute that executable for `python` when creating the environment. A missing/blank `DJANGO_SECRET_KEY` fails startup. No secret fallback, `.env` file or automatic dotenv loader is supplied. Clear the temporary variable after stopping the server with `Remove-Item Env:DJANGO_SECRET_KEY`.

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

No commit or push performed. Next task: SETUP-05 — React TypeScript frontend skeleton, only when authorized.
