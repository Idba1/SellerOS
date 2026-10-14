# Frontend

React/TypeScript SellerOS shell, styled with Tailwind's Vite plugin. FRONTEND-01 adds accessible navigation and route placeholders only; no API requests, authentication, business actions or generated demo data. Node 22.14.0 and npm 10.9.2 pins are retained. Exact dependency versions and transitive resolution are recorded in package.json/package-lock.json.

## Application shell — FRONTEND-01

`src/app/routes.ts` is the shared UI route register: `/` (dashboard), `/products`, `/inventory`, `/customers`, `/orders`, `/expenses`, `/profit`, `/assistant`, `/advisor`, `/segments`, `/forecast`, `/simulator`, and `/settings`. These placeholders map to the approved scope and do not claim implemented features. They are UI paths, separate from `/api/v1/`. Unknown paths show a not-found state and dashboard recovery link. Trailing slashes are accepted; query strings do not affect route selection.

Navigation uses native links and full document navigation, including normal browser back/forward behavior, without another routing dependency. Vite serves direct application URLs locally; future deployment must serve index.html for UI paths while keeping API/static handling separate. The shell includes a keyboard skip link, semantic landmarks, visible focus, current-page indication, and mobile navigation. No permissions are implemented here: all links are visible placeholders; server authorization and later authenticated route handling remain separate tasks. Store settings/user-management access must follow the approved owner/staff policy when implemented.

### Verification — 13 October 2026

- `npm run build --prefix frontend`: TypeScript and Vite passed (30 modules). Initial sandbox attempt failed with filesystem EPERM; elevated retry passed.
- Browser smoke command from repository root, using the pre-existing bundled Playwright and installed Edge:

```powershell
$env:NODE_PATH = 'C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
node frontend/tests/shell-smoke.cjs
```

Passed all 13 direct route headings/current-page/title checks, trailing slash/query handling, not-found recovery, keyboard skip-link and navigation activation, 375px/1280px overflow checks, and no console/page errors. The script starts/stops its own loopback Vite server on port 18767 and closes its browser; no project dependency was added. The sandbox attempt could not reach the test server; elevated retry passed. These checks are not a complete accessibility certification or authentication test. Other machines need an existing Playwright installation and Edge to run this optional browser script; typecheck/build use project tooling only.

No business-rule decision was made. Next task: FRONTEND-02 shared API client/error handling; no API client added here.

From `frontend/`:

```powershell
npm ci
npm run typecheck
npm run build
npm run dev
```

Open the printed loopback URL (normally http://127.0.0.1:5173/). `npm run preview` serves the built output for local inspection. Development servers are not production deployment. If the default npm cache is inaccessible, set `$env:npm_config_cache = Join-Path $env:TEMP 'selleros-npm-cache'` for the current shell; no global npm configuration is changed.

Source locations: `src/app/App.tsx` for the shell, `src/main.tsx` for mounting, `src/styles/index.css` for Tailwind, and `vite.config.ts` for React/Tailwind plugins. shadcn/ui components will be introduced when an actual component is needed; no CLI or unused component packages are installed. TanStack Query/Recharts likewise belong to later API/data feature tasks.

## Verification — 6 October 2026

Initial Git status was clean on setup. npm registry engine/peer metadata verified compatibility with the runtime pins. The first default-cache query failed with EPERM; the temporary cache fixed it. Initial Vite 7.3.1 build passed but audit reported advisories; updated to 7.3.6 and applied a compatible transitive audit fix. `npm ci --prefix frontend` passed with zero audit vulnerabilities. `npm run build --prefix frontend` passed TypeScript and Vite production build. Build output and node_modules are ignored.

`npm run dev` from frontend started the loopback server. Bundled Playwright's downloadable Chromium was absent, so browser verification uses installed Edge without adding project test dependencies. The first browser run exposed a missing favicon 404; an empty data favicon removes that request. Browser assertions checked the shell heading and collected console/page errors; passed. No feature behavior tests are claimed. No backend/decision files changed during SETUP-05.

## Repeatable run and shutdown — SETUP-07

See the [root guide](../README.md#local-setup-and-run--setup-07). From frontend use `npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`; stop with Ctrl+C. For production-output inspection use `npm run preview -- --host 127.0.0.1 --port 4173 --strictPort` after build, then Ctrl+C. These are local servers, not deployments. No frontend test/lint command exists; use typecheck/build plus browser checks.

Clean dependency rehearsal, 6 October 2026: initial `npm ci --prefix frontend` failed with EPERM on a locked lightningcss native file. Subsequent checks failed because that interrupted install had removed tools. Port/process inspection located the earlier SellerOS Vite server on 5173; stopping that specific process required elevated execution after access denied. Once stopped, `npm ci --prefix frontend` succeeded (84 packages, zero audit vulnerabilities), `npm run typecheck --prefix frontend` passed and `npm run build --prefix frontend` passed. Do not reinstall while a server holds native modules open; do not stop unrelated processes.

The live rehearsal launched Vite's CLI (the same entry point as npm's dev script) with the documented host/port/strictPort arguments, verified HTTP 200, and used bundled Playwright with installed Edge to assert the shell heading and no console/page errors. The supervisor terminated/waited for its server process in `finally`. No new browser/test package was added. Both live rehearsal servers stopped; no claim of a clean-OS or independent student test is made. Next task: BACKEND-01, only when authorized.

## Shared API transport — FRONTEND-02 (14 October 2026)

`src/api/client.ts` implements the BACKEND-05 direct-success/error contract without registering or calling business endpoints. `createApiClient` requires an explicit HTTP(S) base ending in `/api/v1/`. Relative resource paths and absolute pagination links must stay inside that origin/prefix and end in a slash; redirects are rejected. Query values are URL-encoded. JSON requests send Accept/Content-Type headers as appropriate. No automatic retries, login redirects, token storage, provider keys, or background requests are added.

`src/api/config.ts` lazily reads public `VITE_API_BASE_URL`; missing/invalid configuration fails before a request. Example: `http://127.0.0.1:8000/api/v1/`. The placeholder shell does not import this client or require API configuration. Endpoint callers supply a `decode(unknown)` function that validates their approved response schema; TypeScript generics alone do not validate network data. A successful 204 returns undefined. Non-JSON, malformed envelopes and rejected success schemas become safe protocol errors without retaining raw bodies. DRF nested details and status/code remain available for field errors. Network/cancellation failures use safe messages; future UI must render details as text, never HTML.

Authentication transport remains [DECISION REQUIRED] until AUTH tasks: default credentials are omitted. `credentials` and a per-request `authHeaders` callback are explicit extension points, not an approved token/session implementation. 401 or 403 authentication codes are distinguished from 403 permission_denied. Cross-origin cookies/CSRF/CORS must be configured under the chosen authentication policy before enabling credentials; the client does not bypass backend authorization.

`createRequestState` exposes idle/loading/success/error snapshots, subscription and an async run method for screen operations (compatible with a future useSyncExternalStore consumer). Latest-started requests own state, so stale completions cannot overwrite newer results. Consumers handle the returned promise, provide AbortSignal when needed, and own lifecycle cancellation. No UI status components or feature fetching are introduced here.

Verification from repository root:

```powershell
node frontend/tests/run-api-tests.cjs
npm run typecheck --prefix frontend
npm run build --prefix frontend
git diff --check
```

Unit runner uses existing TypeScript and Node test tooling, compiles into a disposable OS temporary directory and removes it in finally. Seven tests passed: success/query/JSON, nested validation/auth/permission, explicit auth adapter, network/cancellation, unsafe URL blocking, 204/protocol/schema failures, and loading/error/stale request state. Typecheck and production build passed; build used elevated execution for known sandbox filesystem restrictions. No live business API integration, authentication flow, database change or dependency installation is claimed. Next: FRONTEND-03 reusable form/status primitives.

## Shared visual system — FRONTEND-UI-01 (14 October 2026)

`src/app/AppLayout.tsx` owns the grouped sidebar, SellerOS wordmark, contextual topbar, non-interactive demo profile, skip link and footer. Existing paths/native link behavior stay intact. `src/ui/primitives.tsx` provides genuinely reused Card and Badge components; semantic props are forwarded by Card. There are no fake account controls or business metrics.

`src/styles/index.css` defines shared neutral surfaces, restrained blue accent, spacing tokens, typography, border/radius/shadow treatments and reusable button/input classes. Future inputs still require explicit labels and validation; no sample form is added. Responsive navigation remains visible and keyboard accessible, with single-column content on smaller screens. No fonts or icons are fetched externally; marks use inline SVG and system font fallbacks.

Verification: `npm run typecheck --prefix frontend` passed; `npm run build --prefix frontend` passed (32 modules); bundled-Playwright `node frontend/tests/shell-smoke.cjs` passed all 13 routes, title/current-page, topbar/profile/cards, keyboard skip/navigation, 404 recovery, 375px/1280px overflow and console checks. Screenshot visual review confirmed desktop alignment and restrained styling. Build/browser used elevated execution for known sandbox restrictions. `git diff --check` passed. No lint script exists. Backend, API client, dependencies and route register unchanged. Pages remain explicitly marked placeholders; authentication and business screens remain later work.

## Dashboard overview — FRONTEND-UI-02 (14 October 2026)

Inspected clean frontend branch at ecbfff4, shared shell/design components, manifests/API types, BACKEND-05 contract and backend URLs. Only health/readiness endpoints exist; there is no approved live dashboard/resource response schema. Dashboard therefore performs no API calls and imports no API client. Every section is explicitly synthetic/demo-only.

Sources: `src/dashboard/demo.ts` holds four fictional orders, three fictional inventory products and a fixed 8–14 October 2026 date range. Revenue/chart sum only delivered fixture amounts; average divides by delivered fixture count; order count includes every selected fixture status. Inventory attention uses stock <= each fictional threshold. These are presentation arithmetic, not production financial rules; amounts use fictional units, without choosing currency. No customer data, returns/cost/profit modeling or AI predictions appear. The 3/7-day selector really filters these records and updates KPIs, chart and orders; inventory remains a current fictional snapshot.

`Dashboard.tsx` renders matching KPI cards, an inline SVG daily chart with descriptive accessible text and a table alternative, demo orders and inventory attention. Preview-state selector explicitly demonstrates loading/empty/error states and live-unavailable messaging; it does not simulate actual network requests or confuse absent data with zero. Other routes retain their placeholders.

Verification: `npm run typecheck --prefix frontend` passed; `node frontend/tests/run-api-tests.cjs` passed all 7 existing API tests; `npm run build --prefix frontend` passed (34 modules); bundled-Playwright `node frontend/tests/shell-smoke.cjs` passed dashboard totals (720 for 7 days, 240 for 3 days), period order counts, four preview states/recovery, existing 13 routes, keyboard, 404, 375px/1280px overflow and console checks. Desktop screenshot visually reviewed. `git diff --check` passed; no lint script exists. No dependency/backend/authentication change. Live integration remains blocked until metric definitions, authorized endpoints and resource schemas are approved.

## Products and inventory preview — FRONTEND-UI-03 (14 October 2026)

Inspected clean frontend at 7c8b9c2, routes/dashboard/shared components, API types/client and backend URLs. There are no business models, serializers or registered product/inventory endpoints. Generic BACKEND-05 transport conventions are not a product field schema. No backend or API transport changes are made.

`src/products/demo.ts` isolates four synthetic catalogue records (demo reference, name, category, fictional-unit price, stock). This is a presentation fixture, not a proposed production serializer. No SKU, variant, availability or low-stock threshold policy is selected. Dashboard and catalogue fixtures are independent visual examples, not synchronized store records. `Products.tsx` is reused by the existing /products and /inventory routes. Both are clearly marked read-only synthetic previews.

Functional local controls: case-insensitive trimmed name/category search; exact category filter; zero/positive recorded-quantity filters; clear filters; native keyboard-accessible read-only details; cross-links between the existing workspaces. Count is derived from filtered fixture records. Stock badges show exact units, not low-stock/availability classifications. Preview-state control demonstrates static loading, empty, error and live-unavailable states without making requests. No create/edit/delete/deactivate/stock-adjust buttons or persistence claims exist.

[DECISION REQUIRED] Live field schema, SKU uniqueness, variants, currency/rounding and stock/availability policy remain pending the previously recorded decisions and DB/API tasks. Seller-configured low-stock thresholds are not invented here. Authorized store-scoped read/write endpoints are prerequisites to actual management.

Verification: `npm run typecheck --prefix frontend` passed; `node frontend/tests/run-api-tests.cjs` passed all 7 existing tests; `npm run build --prefix frontend` passed (36 modules); bundled-Playwright `node frontend/tests/shell-smoke.cjs` passed search/category/stock combinations, zero matches/clear, keyboard details, all preview states/recovery, both product/inventory routes, existing dashboard/13 routes, keyboard/404/console and 375px/1280px overflow checks. Initial browser test used an exact label selector that timed out; corrected to the accessible combobox selector and rerun passed. Desktop screenshot visually reviewed. `git diff --check` passed. No lint script, added dependencies, API requests, backend changes or real-data test claimed.
