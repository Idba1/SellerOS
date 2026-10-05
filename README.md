# SellerOS

## Local setup and run — SETUP-07

Verified 6 October 2026 on Windows 11 25H2 x64, PowerShell 7.6.5, Python 3.12.14, Node 22.14.0, npm 10.9.2 and PostgreSQL binaries 17.4. Historical task notes below remain as evidence; this section is the current run guide. Both members should run these steps individually and record their own results; no independent member rehearsal is claimed here.

### Install and check (repository root)

Open PowerShell at your checkout (`Set-Location E:\SellerOS` on the verified machine). Internet/registry access is needed for installs. Use a separately provisioned pinned Python on another machine; the bundled path below is specific to this computer:

```powershell
$sellerosPython = 'C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $sellerosPython --version
node --version
npm --version
# Create only when backend/.venv does not already exist.
if (-not (Test-Path backend/.venv)) { & $sellerosPython -m venv backend/.venv }
& backend/.venv/Scripts/python.exe --version
& backend/.venv/Scripts/python.exe -m pip install --disable-pip-version-check -r backend/requirements.txt
& backend/.venv/Scripts/python.exe -m pip check
# Writable temporary cache avoids this machine's default-cache permission error.
$env:npm_config_cache = Join-Path $env:TEMP 'selleros-npm-cache'
npm ci --prefix frontend
npm run typecheck --prefix frontend
npm run build --prefix frontend
```

Stop if a command fails or the interpreter does not match `.python-version`; PowerShell does not automatically stop after every native command error. Do not reuse a mismatched environment or overwrite someone else's environment. npm ci replaces generated frontend node_modules using the committed lockfile; do not mix npm and pnpm. No globally installed Django, active virtualenv, or provider key is required.

### Backend terminal (repository root)

```powershell
$env:DJANGO_SECRET_KEY = (& backend/.venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(64))")
try {
    & backend/.venv/Scripts/python.exe backend/manage.py check
    & backend/.venv/Scripts/python.exe backend/manage.py test core
    & backend/.venv/Scripts/python.exe backend/manage.py runserver 127.0.0.1:8000 --noreload
} finally {
    Remove-Item Env:DJANGO_SECRET_KEY -ErrorAction SilentlyContinue
}
```

Expected: system check has no issues, four tests pass, server prints its loopback URL. In a separate terminal: `Invoke-RestMethod http://127.0.0.1:8000/health/` returns status `ok`. It is process liveness only, not database/provider readiness. `.env.example` is reference-only for Django: no automatic dotenv loading. Never use `REPLACE_ME` or print a private environment file. The temporary secret is appropriate only for this stateless local skeleton; persistent environments need managed stable secrets.

### Frontend terminal

```powershell
Set-Location E:\SellerOS\frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open http://127.0.0.1:5173/ and expect SellerOS / Your business workspace with no browser-console errors. Use the checkout path appropriate to your machine. This shell makes no backend requests yet. There is no frontend `test` or `lint` script; current client verification is typecheck, build and browser rendering. Optional production-output check: `npm run preview -- --host 127.0.0.1 --port 4173 --strictPort`, then open the printed URL. Preview is not production hosting.

### PostgreSQL and migrations

`psql --version` and `postgres --version` identify installed binaries; `Get-Service -Name 'postgresql*'` checks local service state where authorized. Database readiness needs a provisioned approved development/test database, least-privilege credentials and later Django settings/driver configuration. Templates currently reserve blank DB variables; they are not used. Django has `DATABASES = {}`, no business models and no migrations, so **do not run migrations for this skeleton**.

After the later database task establishes and verifies those prerequisites, the commands will be `backend/.venv/Scripts/python.exe backend/manage.py showmigrations` and `backend/.venv/Scripts/python.exe backend/manage.py migrate`. They are deferred, not claimed passing today. Do not initialize SQLite as a workaround or create a PostgreSQL database in SETUP-07. Financial/timezone/provider decisions remain open.

### Shutdown and troubleshooting

Press Ctrl+C in each server terminal; backend `finally` clears its temporary secret. Frontend shutdown needs no secret cleanup. If a strict port is occupied, stop your own prior server or choose another explicitly; do not kill unrelated processes. Missing Django secret: set it in the *same* backend terminal. npm engine error: verify exact Node/npm pins. Cache EPERM: use the temporary cache variable above. Health 404: request `/health/` with trailing slash. A frontend page does not prove backend/database integration.

### Rehearsal evidence

A fresh separate backend virtual environment was created and installed from requirements without touching the existing environment. Checks, four tests and pip dependency check passed. `npm ci`, typecheck and production build passed using the lockfile. Live backend HTTP and frontend browser/shutdown results are documented in the component READMEs. This is a clean dependency rehearsal on this machine, not a clean OS install or independent runs by both students. No migrations, provider requests or real customer data were used. Only documentation changes are part of SETUP-07; temporary rehearsal artifacts are removed after verification. Next dependency: BACKEND-01 — environment-specific Django settings, only when authorized.

SE-331 standalone social-commerce seller business intelligence and decision-support capstone. SellerOS will connect seller-entered operational records with grounded reply drafts, business summaries, behavior segmentation, demand estimates, deterministic profit analysis and transparent what-if scenarios.

## Current repository baseline

SETUP-01 verification, 5 October 2026. Git is already initialized; do not initialize it again. **Agreed default branch: `main`, explicitly selected by the user; keep current work on `docs`.** Existing `main` tracks `origin/main`. Remote default verification could not complete because `git ls-remote --symref origin HEAD` failed with Windows HTTPS credential error `SEC_E_NO_CREDENTIALS`. There is no local `origin/HEAD` symbolic reference. The agreement does not claim a verified GitHub default setting. No branch switch, remote change or history rewrite was performed.

At inspection the tree was clean. `docs` and cached `origin/docs` pointed to `55523e2` (PLAN-06); `main` and cached `origin/main` pointed to `964a86a` (PLAN-03). These are observed local references, not a claim that the remote remains unchanged. The history contains planning commits and the original `d935a45` first commit. Existing code is only `check.py`, a print script; no runnable SellerOS frontend/backend, dependency manifests or application configuration exists yet.

## Planning records

- [Scope and requirements](docs/requirements/scope.md) and [traceability register](docs/requirements/traceability.csv).
- [Order, revenue and inventory rules](docs/decisions/order-and-inventory.md).
- [Account and store access](docs/decisions/auth-and-store.md).
- [Analytics, forecast and scenario candidates](docs/decisions/analytics-and-ai.md).
- [Data, provider and evaluation policy](docs/decisions/data-and-provider.md).
- Original proposal and Master Plan are retained under `documents/`.

One store per account with owner/staff roles and synthetic-only demo/evaluation are selected. Financial/lifecycle edge cases, forecast/scenario parameters, authentication details, provider, budget and retention decisions remain open as recorded. SETUP-01 does not resolve them or authorize dependent implementation.

## Approved architecture

React/Vite/TypeScript, Tailwind CSS, shadcn/ui, TanStack Query and Recharts; Python/Django/DRF/Django ORM; PostgreSQL; Pandas/NumPy/Scikit-learn. XGBoost is conditional on later justification. LLM integration is backend-only and remains subject to provider/privacy/budget review. No live social/courier/payment integrations or autonomous actions are included.

## Ignore and review rules

`.gitignore` excludes local environment secrets, Python environments/caches, frontend dependencies/build outputs, local database artifacts/uploads/logs, and generated datasets/model artifacts. Reviewed `.env.example` and `.env.*.example` templates remain eligible for tracking and must contain placeholders only. Ignore rules do not protect already tracked files, forced additions, arbitrary filenames or Git history; review changes before staging. Do not commit provider keys or real customer data. Reviewed source documents, Markdown/CSV planning evidence, package manifests and lockfiles are not blanket-ignored.

No environment or database files are created to test ignore behavior. Validate hypothetical paths with:

```powershell
git check-ignore -v --no-index -- .env backend/.env frontend/.env.local .venv/test node_modules/test data/raw/test.csv
git status --short --branch
git log -6 --oneline
git diff --check
```

Verification outcomes: `git status --short --branch` initially showed a clean `docs` branch; `git branch -avv`, `git log -6 --oneline`, `git ls-files` and `rg --files --hidden -g '!.git'` confirmed the baseline above. `git symbolic-ref refs/remotes/origin/HEAD` failed because no symbolic reference exists; the remote query failed as described. `git check-ignore -v --no-index` matched all six listed hypothetical paths. Quiet ignore assertions also passed for `db.sqlite3` and `model.joblib`; `.env.example`, `backend/.env.development.example`, `README.md`, `package.json`, `package-lock.json` and the traceability CSV remained eligible. Thus 8 excluded and 6 eligible paths passed without creating those files. `git diff --check` returned no tracked whitespace errors; newly untracked files were separately checked using `git diff --no-index --check -- NUL <file>`. No-index comparisons use exit 1 to indicate differences, not an application test failure. Final status contains only the new `.gitignore` and `README.md`; existing tracked files are unchanged.

Application run/build/test commands are unavailable until later setup tasks create their projects. No installation, Django/React initialization, database configuration, application feature, commit or push was part of SETUP-01 verification.

## Root layout — SETUP-02

Recorded 6 October 2026. Current work is on `setup`; the working tree was clean at inspection. The agreed default remains `main`. The earlier branch/status observations above describe SETUP-01, not the current checkout.

```text
SellerOS/
├── backend/README.md       # Future Django/DRF backend; placeholder only
├── frontend/README.md      # Future React/Vite/TypeScript frontend; placeholder only
├── docs/
│   ├── decisions/          # Existing business/access/AI/data decisions
│   └── requirements/       # Existing scope and traceability records
├── data/sample/README.md   # Future reviewed synthetic fixtures; no data yet
├── documents/              # Original proposal and Master Plan, preserved
├── check.py                # Existing print script, preserved
├── .gitignore
└── README.md
```

Minimal README placeholders keep the new locations visible in Git; no modules, manifests, secrets, datasets or framework scaffolds are created. Existing `docs/` and `documents/` remain in place. Runtime pinning and runnable skeletons are later tasks. Next dependency: **SETUP-03 — Pin and document runtime versions**, only when authorized.

## Runtime baseline — SETUP-03

Verified 6 October 2026 on branch `setup`. Preserve the pre-existing SETUP-02 README changes and untracked placeholders. The table records exact local observations and selected project runtime pins; it does not claim a fresh installation or a production security baseline.

| Component | Selected exact version | Verification / status |
| --- | --- | --- |
| Python | 3.12.14 | Bundled executable reports 3.12.14, AMD64; no Python/py command on PATH |
| Python installer tool | pip 26.2.1 | Bundled Python `-m pip --version` reports 26.2.1 |
| Node.js | 22.14.0 | `node --version`: v22.14.0, installed under Program Files |
| Project JS package manager | npm 10.9.2 | `npm --version`: 10.9.2; use npm consistently for the project |
| PostgreSQL server/client binaries | 17.4 | `postgres --version` and `psql --version`: 17.4; no database connection queried |
| Development OS target | Windows 11 25H2, x64 | Python identifies Windows 11 build 26200; registry reports DisplayVersion 25H2, build 26200.9457 |
| Shell | PowerShell 7.6.5 | `$PSVersionTable.PSVersion.ToString()` |

pnpm 11.25.0 is available through the Codex runtime but is not the selected project manager. Use one npm lockfile when dependencies are introduced. Other operating systems are unverified, not declared supported. The exact OS build is observed evidence, not a requirement to downgrade Windows updates. Registry ProductName says Windows 10 Pro despite build/platform identifying Windows 11; `Get-CimInstance Win32_OperatingSystem` was denied. OS edition is not conclusively verified.

`.python-version` and `.node-version` record runtime selections; they do not install runtimes or enforce versions without a compatible version manager. `frontend/package.json` records exact Node/npm engines and `packageManager`; `frontend/.npmrc` enables strict engine checking. No application scripts/dependencies are added in SETUP-03. PostgreSQL and pip pins are documented here because neither belongs in a frontend dependency manifest. Framework/package pins and resolved lockfiles will be established in SETUP-04/05 when required packages are chosen; no empty requirements file or fabricated lockfile is supplied.

Compatibility review: [Django 5.2's official Python matrix](https://docs.djangoproject.com/en/5.2/faq/install/) includes Python 3.12. [Vite's official requirement](https://vite.dev/guide/) accepts Node 22.12+, which this Node satisfies; individual template requirements still need checking. This establishes runtime-family compatibility, not selected Django/Vite package versions or verified dependency resolution. Recheck patch/security releases before deployment rather than treating these observed older Node/PostgreSQL patches as indefinitely safe. Python distribution availability and package wheels must be checked for a fresh machine; the bundled interpreter is not a project-installed Python.

For this machine the verified interpreter is:

```powershell
$sellerosPython = 'C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $sellerosPython --version
& $sellerosPython -m pip --version
node --version
npm --version
postgres --version
psql --version
```

On a fresh machine provision the recorded runtime versions from approved distribution sources, then verify their versions before creating an isolated backend environment in SETUP-04. Do not depend on this user's bundled path on other machines. Once actual backend requirements and frontend lockfile exist, their isolated install commands will be `python -m pip install -r backend/requirements.txt` and `npm ci --prefix frontend`; these are future commands, not runnable dependency installation instructions today. A fresh dependency install has **not** been verified because no application dependencies exist yet. No packages were installed in this task.

Checks performed: runtime commands above; `Get-Command python,python3,py,node,npm,pnpm,psql`; bundled Python `-B -c` for version/platform; registry OS read after denied CIM inspection. Node JSON/version assertions verify manifest pins against the actual Node/npm versions and version files. `git diff --check` and no-index whitespace checks cover new pin files. No application build/database test applies. Next task: **SETUP-04 — Create Django backend skeleton**, only when authorized; runtime pins do not resolve outstanding business/provider decisions.
