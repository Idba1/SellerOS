# PostgreSQL development and tests — BACKEND-04

9 October 2026. PostgreSQL only; no SQLite fallback. Required variables: DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_TEST_NAME. Local settings read private backend/.env; explicit process values win. Test settings never read that file and need those values plus DJANGO_SECRET_KEY exported securely. Missing/blank/example-marker values fail with variable names only. No real credentials are included in templates or this document.

## Provisioning prerequisites

Use dedicated local development resources and a role without superuser privileges. The development database must exist and permit schema/migration work. Django test setup needs a role permitted to CREATE DATABASE (or a separately approved pre-provisioned test-database workflow). DB_TEST_NAME must start with test_, contain ASCII letters/digits/underscores, be at most 63 characters and differ from DB_NAME. Never point the test name at a valuable existing database: this naming guard is not proof that a database is disposable. No automatic database/user creation, deletion or privilege changes occur in this task.

Set the six required values in ignored backend/.env through your local editor; do not send passwords in chat. DB_CONNECT_TIMEOUT defaults to 5 seconds (validated 1–30); PostgreSQL statement_timeout is 5000 ms. Port range 1–65535. Persistent connections are disabled (CONN_MAX_AGE=0). SSL/remote deployment policy remains a later environment decision; these are local development instructions.

## Commands after credentials are configured

From root with local settings:

```powershell
& backend/.venv/Scripts/python.exe backend/manage.py check
& backend/.venv/Scripts/python.exe backend/manage.py shell -c "from django.db import connection; c=connection.cursor(); c.execute('SELECT 1'); assert c.fetchone() == (1,); c.close(); print('PostgreSQL connection OK')"
& backend/.venv/Scripts/python.exe backend/manage.py showmigrations
& backend/.venv/Scripts/python.exe backend/manage.py migrate --plan
& backend/.venv/Scripts/python.exe backend/manage.py migrate
```

Inspect plan before migration. No business/auth models are installed yet, so migration smoke may report no pending application migrations; Django's migration recorder can still be created. Successful system check alone does not prove a connection. Readiness /ready/ becomes 200 only when its SELECT succeeds; /health/ remains liveness.

For explicit test mode, securely export DJANGO_SECRET_KEY and all six DB variables in the current process (do not dot-source arbitrary .env text). Then:

```powershell
& backend/.venv/Scripts/python.exe backend/manage.py check --settings=config.settings.test
& backend/.venv/Scripts/python.exe backend/manage.py test core --settings=config.settings.test
```

Django creates the named test database, runs test setup, and destroys it afterward. Leave interactive confirmation enabled; do not use --noinput to automatically replace an existing database. PostgreSQLSmokeTests asserts the test database's vendor/name and executes SELECT 1. --keepdb is an optional reviewed local workflow, not used here. Clear exported credentials after the session. Test isolation also requires same-store fixtures in later data tasks; database separation does not implement store authorization.

## Observed verification and limitation

Initial clean branch backend. Inspected settings/test settings, requirements and existing probe tests; private env inspection printed only configured/missing flags. All DB fields were blank. Service inspection was denied by sandbox permissions; no service-state claim is made. Sandbox registry DNS failed; approved elevated driver installation succeeded: psycopg/binary 3.3.6 and typing_extensions 4.16.0. pip check passed.

An inline Python subprocess exported synthetic configuration values (not real connection credentials), set writable TEMP/TMP, ran `manage.py check --settings=config.settings.test` and the selected database-free labels `core.tests core.test_settings core.test_environment core.test_api core.test_health core.test_database.DatabaseConfigurationTests`: **20 tests passed**. Health's unconfigured path is now explicitly mocked so it does not assume global DATABASES is empty. New validation tests cover backend identity/timeouts, sanitized missing config and unsafe name/port/timeout rejection.

**BLOCKED — live verification:** user has been asked to configure local credentials. No live connection/migration/test-database pass is claimed. PostgreSQLSmokeTests is written but not run. Do not mark BACKEND-04 acceptance complete until those checks pass against provisioned PostgreSQL. No business decision is changed; no keys printed, real data used, database provisioned or commit made. BACKEND-05 waits for this prerequisite's live checks.
