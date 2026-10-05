# impl-frontend — scaffold plan

**Branch:** `claude/scaffold` (stacked on PR #1)
**Written at:** 2026-10-05, against the director's brief and the architecture documents directly.

> Note: `docs/reviews/scaffold/impl-director.md` was not present in the worktree at planning
> time. This plan is written against `docs/reviews/scaffold/impl-director-brief.md` and the
> architecture documents directly. If the director's plan later narrows or reorders the
> frontend lane, this plan should be revisited.

---

## What I build

All files are under `web/`, which is the frontend specialist's layer.

### Toolchain and configuration

These have no dependency on the API and can be written as soon as this plan is approved.

- `web/package.json` — ported from the sibling, name `constellate-web`, same dependency
  versions (React 19, Vite 8, TypeScript 5, `openapi-fetch`, `@tanstack/react-query`,
  `react-router-dom`, `openapi-typescript`). `puppeteer-core` is not included: it drives
  the sibling's screenshot scripts, which do not exist at scaffold time, and nothing else
  needs it. The `generate:api-types` and `check:api-types` scripts are ported verbatim.
- `web/index.html` — the Vite entry HTML, `<div id="root">`, loads `src/main.tsx`.
- `web/vite.config.ts` — API proxy at `/api` → `http://127.0.0.1:8000`; the
  `API_PROXY_TARGET` env override from the sibling is kept (it lets a branch test against a
  different port without editing the file). No other plugins needed at scaffold time.
- `web/tsconfig.json` — two-project references: `tsconfig.app.json` and `tsconfig.node.json`.
- `web/tsconfig.app.json` — bundler mode, `target: "es2023"`, `jsx: "react-jsx"`, strict.
  Includes `src/`. `types: ["vite/client", "node"]` so tests that read the filesystem
  typecheck without a separate test tsconfig project.
- `web/tsconfig.node.json` — Node module mode for `vite.config.ts` only.
- `web/build-inputs.json` — declares what `npm run build` reads, for the ops build-staleness
  check. Includes `src`, `public`, `index.html`, `package.json`, `package-lock.json`,
  `vite.config.ts`, `tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`. Excludes
  `*.md`, `*.test.ts`, `*.test.tsx`, `src/test`.
- `web/.gitignore` — adds `dist/` (the Vite build output). The root `.gitignore` already
  covers `node_modules/`.

### Source files — no API contract dependency

All can proceed in parallel with `impl-backend`.

- `web/src/index.css` — minimal stylesheet, reset only. Product styles arrive with the first
  screen.
- `web/src/main.tsx` — `QueryClient` with the `ApiError` session-reset logic from the
  sibling (a 401 on any query resets `["me"]`), `QueryClientProvider`, `BrowserRouter`, and
  `App`. The session cookie name will be updated from the sibling's `bgt_session` to
  whatever the backend names it; the name in the docstring is the only place it lives on the
  web side, so this is a single-line edit when the backend spec says.
- `web/src/App.tsx` — minimal routing shell. At scaffold time there are no product routes:
  the only routes are a `NotFound` fallback. Product routes (timeline, totals) arrive with
  M1 screens. A comment names where the first protected routes will go.
- `web/src/api/client.ts` — `openapi-fetch` typed against `paths` from `schema.d.ts`,
  `baseUrl: "/api"`, `credentials: "include"`. Docstring notes the one origin / one base URL
  invariant from the sibling's `ADR-0016` equivalent.
- `web/src/api/errors.ts` — ported verbatim from the sibling: `ApiError`, `unwrap`,
  `unwrapOrNull`, `unwrapNoContent`, `describeError`, `describeFormError`,
  `describeFieldErrors`. Uses `components["schemas"]["ErrorBody"]` and
  `components["schemas"]["FieldError"]` from `schema.d.ts`. **Dependency on the backend:**
  see the sequencing note below.
- `web/src/api/errors.test.ts` — ported verbatim from the sibling: unit tests for
  `ApiError`, `unwrap`, `unwrapOrNull`, `describeFormError`. Run in Node, no DOM.
- `web/src/api/queryKeys.ts` — no keys at scaffold time (no product queries yet), but the
  module is created with its docstring so the file exists for `layering.test.ts` to walk.
  The `ME_QUERY_KEY` and session-reset wiring in `main.tsx` arrive with the sign-in screen
  (M1).
- `web/src/routes/NotFound.tsx` — single component, single export, renders a "Not found"
  message.
- `web/src/test/walkFiles.ts` — ported verbatim from the sibling: recursive file-system walk
  used by `layering.test.ts`.
- `web/src/layering.test.ts` — ported from the sibling with three adaptations:

  1. **Threshold**: the sibling asserts "at least ten non-test source files". At scaffold time
     there are eight (`main.tsx`, `App.tsx`, `api/client.ts`, `api/errors.ts`,
     `api/queryKeys.ts`, `api/schema.d.ts`, `routes/NotFound.tsx`, `test/walkFiles.ts`).
     The scaffold sets the threshold to **5**, which is still large enough to catch a broken
     walk, and is raised each time a route is added until the test is no longer the binding
     constraint.

  2. **`MAY_NOT_IMPORT` table**: the sibling lists nine top-level directories. The scaffold
     starts with three (`api`, `routes`, `test`). Only those three have rows initially; the
     test still enforces "every directory has a row" so a new directory added without a rule
     is a test failure rather than an unruled gap.

  3. **`web/scripts/` rules**: the sibling's test includes a describe block that checks every
     `.mjs` script under `web/scripts/`. There are no web scripts at scaffold time, so those
     three describe blocks (`web/scripts/ → web/src/ import rule`, `web/scripts/ Node
     loadability`, and the `shoot.mjs` direct-run test) are omitted. They are added alongside
     the first web script.

  The four per-file rules (layer rule 1–4) and the `import-type exemption` cases are ported
  verbatim.

### Schema-dependent source file

This step cannot start until `impl-backend` delivers `api/openapi.json` with the health
endpoint.

- `web/src/api/schema.d.ts` — generated by `npm run generate:api-types` from
  `api/openapi.json`. Committed at the state the health endpoint's contract produces.

---

## What I do not build

- **Any product screen.** No timeline, no totals, no login, no account page. Those arrive
  with M1 screens, one at a time.
- **`RequireSession` or session hooks.** Sign-in is not in scope for the scaffold.
- **The browser extension** (`extension/`). Q-D has not confirmed it is needed; the brief
  says the scaffold excludes it.
- **The `web` gate area** in `scripts/gates.py` or `.github/workflows/web.yml`. Those are
  session-owned files. What the `web` area's checks should be, so the session can write them:
  - paths: `["web/**", "api/openapi.json"]`
  - checks (in `web/` cwd, in order):
    - `npm run check:api-types` (quick: false — it runs a generate step)
    - `npm test` (quick: false)
    - `npm run build` (quick: false)
  - `npm` needs a `PROBES["npm"]` entry in `gates.py`; Node 24.9.0 is on PATH.
- **`web/CLAUDE.md`** — the layer conventions document. Session-owned. The layer rules the
  test enforces are the content; the sibling's `web/CLAUDE.md` is the model.
- **`web/README.md`** — session-owned.
- The poller, any data source adapter, any API layer file.

---

## Where the brief's premises did not survive my reading

### Layering test threshold

The sibling's "at least ten" is calibrated for a mature product. A scaffold that sets that
threshold and provides fewer files fails on its first `npm test`. I am adjusting to 5, which
still catches a broken walk (5 files, all in different modules, is already a meaningful
signal). This is a design decision within my layer, not a direction change.

### `errors.ts` depends on the error schemas being in the backend contract

`errors.ts` uses `components["schemas"]["ErrorBody"]` and `components["schemas"]["FieldError"]`
from the generated `schema.d.ts`. If the backend's initial `api/openapi.json` does not define
these schemas (as reusable components), `tsc` will report a type error when I generate the
schema. The backend's conventions section (the scaffold plan's "API conventions" decision)
should confirm that `ErrorBody` and `FieldError` are defined as schema components, not only
as inline response schemas. This is a flag for the director and `impl-backend`, not something
I work around: patching `errors.ts` to avoid the type would be hand-writing what the contract
should guarantee.

### No `web/scripts/` at scaffold time

The sibling's `layering.test.ts` has a hard "has at least one .mjs file" assertion that fails
if `web/scripts/` is empty. Since the scaffold has no web scripts, I omit the scripts section
of the test rather than create a placeholder `.mjs` file. A placeholder would be dead code,
which the style forbids; the sections are added alongside the first real script.

---

## Parallel and sequential steps

### Fully parallel with other lanes

Everything except `web/src/api/schema.d.ts`:
- All config and toolchain files
- `web/src/api/client.ts`, `errors.ts`, `errors.test.ts`, `queryKeys.ts`
- `web/src/layering.test.ts`, `web/src/test/walkFiles.ts`
- `web/src/main.tsx`, `web/src/App.tsx`, `web/src/routes/NotFound.tsx`
- `web/src/index.css`

These can start as soon as this plan is approved and do not require a separate worktree (the
frontend specialist owns `web/` alone; no other specialist writes there).

### Blocked on `impl-backend`

`web/src/api/schema.d.ts` — needs `api/openapi.json` to exist with the health endpoint
defined, including the `ErrorBody` and `FieldError` component schemas.

`npm run check:api-types` — needs the above, so cannot be verified until after the backend
delivers `api/openapi.json`.

---

## Files another lane also needs or produces

| File | Producer | Consumer |
|------|----------|----------|
| `api/openapi.json` | `impl-backend` | `impl-frontend` (schema generation) |
| `web/src/api/schema.d.ts` | `impl-frontend` (generated) | nothing imports it at scaffold time, but `web.yml` gate checks it matches `api/openapi.json` |
| `web/CLAUDE.md` | session | informs `layering.test.ts` rule table |
| `scripts/gates.py` `web` area | session | triggers `npm test` / build on pushes |
| `.github/workflows/web.yml` | session | workflow that mirrors the gate area |

---

## Verification

Run from `C:\wt\constellate-scaffold\web` after `impl-backend` delivers `api/openapi.json`:

```
npm ci
npm run generate:api-types
npm test
npm run build
npm run check:api-types
```

`npm test` passes without `api/openapi.json` if `schema.d.ts` is committed (layering test
and error tests have no network dependency). The `check:api-types` step regenerates from
`api/openapi.json` and diffs the result against the committed file — this is the drift check
that the `web.yml` gate mirrors.

`npm run build` runs `tsc -b && vite build`. The TypeScript project references mean the
build fails on any type error in `src/` or `vite.config.ts`.

---

## What I do not reopen

- The stack choice (ADR-0002, Accepted 2026-09-23). React + Vite + TypeScript it is.
- The extension's scope. Not in Q-D's answer yet; `extension/` does not exist in this PR.
- The API conventions (error envelope, pagination, time format). Those are the director's
  decision surfaces, named in the brief; I consume whatever `api/openapi.json` defines.
