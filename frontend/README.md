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

`npm run dev` from frontend started the loopback server. Bundled Playwright's downloadable Chromium was absent, so browser verification uses installed Edge without adding project test dependencies. The first browser run exposed a missing favicon 404; an empty data favicon removes that request. Browser assertions check the shell heading and collect console/page errors. Final outcomes are reported in chat. No dependency or application tests for feature behavior are claimed. No backend/decision files changed, and no commit made. Next task: SETUP-06 — safe environment configuration templates.
