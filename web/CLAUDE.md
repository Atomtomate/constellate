# `web/` — the web client

React + Vite + TypeScript (ADR-0002). How to run it, and what is in it, is `web/README.md`;
this file is the conventions a change here has to follow. Read the root `CLAUDE.md` first.

## The generated client

`src/api/schema.d.ts` is generated from `api/openapi.json` by `openapi-typescript` and
committed — never edited by hand. `npm run generate:api-types` regenerates it after the
contract changes; `npm run check:api-types` regenerates and fails on a diff, which is what CI
runs (`.github/workflows/web.yml`, triggered by `web/**` and by `api/openapi.json` itself, and
the `web` gate area in `scripts/gates.py` on push). The build order is schema, then contract,
then this client, so a change to the API surface is regenerated here in the same PR, or the
`web` build goes red without a file under `web/` having changed.

Everything typed against the contract goes through `src/api/`: `client.ts` is the one
`openapi-fetch` client every screen calls through, and `errors.ts` owns the envelope —
`ErrorBody` and `FieldError` imported *by name* from `components["schemas"]`, the request-id
header from `components["headers"]`, which is why the API keeps those as named Pydantic models
and declares the header once — and `ApiError`, which every query function throws through
`unwrap` so a screen's error state has the envelope's `code` to switch on.

## Layer rule

`routes/` calls `hooks/`; `hooks/` calls `api/`; the pure sections — `test/` now, `lib/`,
`domain/` and `theme/` when they arrive — import no runtime value from `hooks/`, `routes/` or
`api/client`, though they may `import type` from `hooks/` and `routes/`. Nothing imports
upward: `api/` does not reach into `hooks/`, `routes/` or `components/`. `api/client` is
imported only by `hooks/` and `api/`, and a `queryFn` is declared only there: a route that
calls the client directly names a cache key no hook can invalidate — which is why the
scaffold's health status reaches `GET /health` through `hooks/useHealth.ts`. A route module
exports only its entry component.

`src/layering.test.ts` enforces all of that at `npm test`, reading `src/` off the filesystem so
a file added later is covered without being listed, and fails on any top-level directory under
`src/` without a row in its `MAY_NOT_IMPORT` table — an empty row is still a row, recording
that the section has nothing to forbid on purpose. A new section brings its row in the same
commit, and a pure one joins `PURE_SECTIONS` too. Test files are excluded from every per-file
check: a test legitimately mocks the client, and the test file says why. The file-count
threshold guards against the loops passing vacuously if the walk ever breaks; raise it as
routes are added.

A query key lives in `src/api/queryKeys.ts` as soon as a second module needs it; a key one
module both reads and invalidates stays with that module. The `health` key is there from the
start although one hook reads it: the file exists from the scaffold for the layer test to walk
(the plan's decision 4), and one real key is a better row than an empty module.

## Testing

vitest, in Node by default: `vite.config.ts` carries no `test.environment`, and there should
be no global `jsdom` — it would put every pure test (`api/`, `test/`, the layering test) in a
DOM it does not use, a slower run and a second way for a case to pass. A component test opts
into a DOM per file, with `// @vitest-environment jsdom` as its first line, and the first one
brings `jsdom` in as a devDependency in the same commit — nothing needs a DOM yet, so none is
installed. Globals are off — every suite imports `describe`, `it` and `expect` — so a
component test also cleans up its own renders between cases.

What is worth a test: a branch no type catches, and a rule this client invented — the error
helpers' fall-through, the layer table. What is not: that a component renders, or that a prop
reaches an attribute the type already guarantees. Assert the count, not just the shape: a loop
over the elements a case found proves nothing about how many there were.

Tests are type-checked by the app project — `tsconfig.app.json` includes `src`, where they
live, with `node` types so a test that reads the filesystem compiles — so `tsc -b` and CI's
build step both see them; there is deliberately no test-only project.

CI (`web.yml`) runs `npm ci`, `npm run check:api-types`, `npm test` and `npm run build`; the
`web` gate area runs the last three from the pre-push hook when `node_modules` is present.
