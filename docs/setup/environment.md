# SellerOS environment templates and secret handling

SETUP-06, 6 October 2026. Placeholder-only [backend template](../../backend/.env.example) and [frontend template](../../frontend/.env.example). No real key, database account, customer data or provider connection is added. Templates document future configuration names, not a finalized database/provider integration contract.

## Current behavior

Django reads `DJANGO_SECRET_KEY` from the process environment. Missing/blank values fail with `DJANGO_SECRET_KEY must be supplied in the environment.` The exact example marker `REPLACE_ME` fails with `DJANGO_SECRET_KEY must not use the example placeholder.` No insecure fallback secret exists. Other weak/arbitrary values are not guaranteed detectable; use a randomly generated secret and reviewed secret storage. Do not log or paste it.

The backend does **not** load `.env` automatically. Copying the template alone does not configure Django. No dotenv dependency or loader is added by this task. For local checks from repository root, generate a temporary environment value without displaying/saving it:

```powershell
$env:DJANGO_SECRET_KEY = (& backend/.venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(64))")
try {
    & backend/.venv/Scripts/python.exe backend/manage.py check
    & backend/.venv/Scripts/python.exe backend/manage.py test core
} finally {
    Remove-Item Env:DJANGO_SECRET_KEY
}
```

Use a private durable server secret for persistent environments when those are introduced; do not rotate it every request. This task creates no private `.env` file. If one is maintained later, provision/export it through a reviewed local mechanism; do not dot-source arbitrary untrusted files or print their contents.

PostgreSQL variables and LLM variables are intentionally blank and unused today. The liveness endpoint must remain available without database/provider configuration. Required PostgreSQL connection validation belongs to the later database task; provider key validation belongs to explicitly approved integration. Do not fail today's database-free shell for reserved values, or interpret them as permission to create a database/connect to a provider. Provider/model, budget/retention and business decisions remain pending.

The frontend shell does not use an API URL yet. Vite reads frontend `.env` files under its usual mode rules, and every `VITE_*` value is public build-time browser configuration. Never place a Django secret, database password or LLM key there, even in a private `.env`. An API base URL must contain no embedded credentials or secret query tokens. Later API-client work must validate required URL/config then; no API feature is added here.

## Repository and evidence rules

Existing `.gitignore` already excludes `.env` and `.env.*` at every level, with exceptions for reviewed `.env.example` and `.env.*.example` templates. It therefore needs no change. Ignore rules do not remove tracked/history secrets or protect forced staging. Never commit keys, raw authorization headers, local environment files, real customer exports or logs containing prompts/identifiers. Backend secrets must not appear in browser bundles, debug output or screenshots. Record reproducible synthetic input references and sanitized results per PLAN-06 instead of raw sensitive context.

If a credential is accidentally disclosed: revoke/rotate it first, restrict access and investigate exposed artifacts/history; removing a current file alone is not remediation. Repository history rewriting is not authorized by this task.

## Verification scope

Check hypothetical ignore paths without creating secrets:

```powershell
git check-ignore -v --no-index -- backend/.env frontend/.env.local
git ls-files -- '*env*'
git status --short --branch
git diff --check
```

Review example values explicitly and scan tracked/untracked source text for recognizable private-key/provider-token/credential-URL patterns with filename-only reporting. Exclude ignored virtual environments/dependencies/build artifacts from this source review. A pattern scan cannot prove absence of every credential or audit full Git history; documentation author contact information is not customer test data. Inspect browser-build configuration separately before real integration.

Exact check outcomes are recorded in the task response. No application behavior beyond required secret validation changes. Future setup/run documentation is SETUP-07; database/provider wiring remains later work.
