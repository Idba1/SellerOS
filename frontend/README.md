# Frontend

SETUP-05 minimal React/TypeScript SellerOS shell, styled with Tailwind's Vite plugin. No business screens, routes, API requests, authentication or generated demo data. Node 22.14.0 and npm 10.9.2 pins are retained. Exact dependency versions and transitive resolution are recorded in package.json/package-lock.json.

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
