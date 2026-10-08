# Django REST Framework baseline — BACKEND-02

8 October 2026. DRF 3.18.3 is pinned in backend/requirements.txt. Package metadata requires Django >=5.2, satisfied by installed 5.2.17; pip resolved it with Python 3.12.14 and pip check reported no broken requirements. No other new dependency or business endpoint is added.

## Current convention

Future DRF views return a `rest_framework.response.Response` containing their JSON resource/result directly, with an appropriate HTTP status; no success envelope is imposed. JSON parser/renderer are the baseline. The existing Django `/health/` response remains `{"status":"ok"}`.

DRF-handled exceptions use:

```json
{"error":{"code":"validation_error","details":{"quantity":["Validation message"]}}}
```

Validation gives HTTP 400/code validation_error and retains nested serializer field/non-field/list details. NotFound/Http404 inside DRF gives HTTP 404/code not_found and details containing detail. Other handled exceptions use their DRF default code or api_error. Status codes and headers such as Retry-After/WWW-Authenticate survive wrapping. Messages must be safe: never construct a validation error containing credentials or raw private inputs. This handler cannot sanitize secrets deliberately put into application error messages.

Unexpected errors return None from the handler and follow Django's existing behavior; internal exception text is not serialized. JSON wrapping applies to errors within DRF views, not URL resolver 404s, middleware failures, arbitrary Django views or debug pages. BACKEND-05 will finalize wider API/error contracts; this task introduces no catch-all route or global failure response. DEBUG remains off by default.

## Authorization boundary

Default permission is IsAuthenticated. Authentication classes are intentionally empty until the later AUTH tasks; unauthenticated user is None because the auth app/database is not installed. Therefore future DRF views fail closed (currently HTTP 403) unless deliberately marked public. No seller access is granted and authentication transport is not selected here. Successful future authentication still needs server-side same-store checks per PLAN-04; this baseline does not implement them. Public test fixtures exist only in tests, not live URL routes. The health endpoint is the existing explicit public liveness endpoint.

## Verified commands and outcomes

- Initial `git status --short --branch`: clean branch backend. Settings, requirements and existing docs were inspected; no previous response contract existed.
- `backend/.venv/Scripts/python.exe -m pip index versions djangorestframework`: 3.18.3 available; pip index/self-update warnings did not prevent lookup.
- `backend/.venv/Scripts/python.exe -m pip install --disable-pip-version-check djangorestframework==3.18.3`: successful; existing Django satisfied dependency.
- `backend/.venv/Scripts/python.exe backend/manage.py check`: local .env-backed check passed, no issues.
- `backend/.venv/Scripts/python.exe backend/manage.py check --settings=config.settings.test`: passed with process-only generated secret, later cleared.
- `backend/.venv/Scripts/python.exe backend/manage.py test core --settings=config.settings.test`: 13 tests passed, including validation/not-found shape, anonymous denial, retained retry headers, unexpected-error handling, earlier health/settings/env cases. No database required.
- `backend/.venv/Scripts/python.exe -m pip check`: no broken requirements.
- `git diff --check`: no whitespace errors; new source/doc files also checked using `git diff --no-index --check -- NUL <file>`.

No credentials displayed, provider/database calls, serializers for business records, DRF auth bypass, frontend changes, commit or push. Next dependency: BACKEND-03, only when authorized.
