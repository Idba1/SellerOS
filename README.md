# SellerOS

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

Application run/build/test commands are unavailable until later setup tasks create their projects. No installation, Django/React initialization, database configuration, application feature, commit or push is part of this verification. Next task: SETUP-02, only when explicitly authorized.
