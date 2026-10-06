# `web/` — the web client

React + Vite + TypeScript (ADR-0002), scaffolded here and built out screen by screen from
here on. Everything in this directory is the web client's; it never touches `api/`
directly -- see the root `CLAUDE.md`'s standing constraints.

At scaffold time there are no product screens. The shell shows the API health status at
`/` and a not-found fallback at every other path. M1 brings the timeline, totals and
sign-in screens.

## Running it

Node ^22.18 or >=24.2 is required.

```bash
npm install
npm run dev          # http://localhost:5173, proxying /api to the API
```

The API must be running separately on `127.0.0.1:8000` -- `cd api && uvicorn
constellate.main:app --reload`, per `api/README.md`. `vite.config.ts` proxies `/api` to it,
matching what Caddy does in every other environment -- which matters because the session
cookie is sent with `credentials: "include"` and a same-origin request is what makes the
browser send it.

**Set `API_PROXY_TARGET`** to point the dev proxy at an API on another port instead of
`127.0.0.1:8000` -- a branch's own uvicorn running beside the rig's, say. `vite.config.ts`
reads it; left unset, it keeps that default.

```bash
npm run build         # tsc -b && vite build; static output in dist/, what Caddy serves
npm run preview       # serve that build locally
npm test              # vitest run; test files live beside their modules as *.test.ts(x)
```

`build` stamps `dist/.built` via `postbuild`. `build-inputs.json` beside this file
declares what the build reads; `stack.py status` uses both to detect a stale build
without touching git.

## The generated API client

`src/api/schema.d.ts` is generated from `api/openapi.json` by `openapi-typescript` and
**committed**, the same rule `openapi.json` itself follows and for the same reason --
without a committed, checked copy the type the client compiles against can drift from
the server it talks to.

```bash
npm run generate:api-types   # regenerate after api/openapi.json changes
npm run check:api-types      # what CI runs: regenerate, then fail if that changed the committed file
```

`src/api/client.ts` wraps `openapi-fetch` into the one client every screen calls through
-- typed against that schema, `credentials: "include"` for the session cookie, base URL
`/api` since the API lives there and `openapi-fetch` does not read the spec's `servers`
entry.

## Layer rules

The rules enforced by `src/layering.test.ts` (which reads `src/` off the filesystem so a
file added later is covered without being listed):

1. `api/client` is only imported by `hooks/` and `api/`. A route that imports it directly
   names its own cache keys and bypasses every hook that would invalidate them.
2. `queryFn` is only declared inside `hooks/` and `api/`. Same principle: a cache entry
   that a hook does not own is a cache entry nothing can invalidate correctly.
3. A section may only import from the sections its row in `MAY_NOT_IMPORT` does not
   forbid. Pure sections (`lib`, `domain`, `theme`, `test`) may `import type` from
   `hooks/` or `routes/` for their type-checking value without creating a runtime
   dependency.
4. A route module has at most one export. Routes are entry points; exporting helpers from
   them makes the layer boundary invisible.

When a new top-level directory is added under `src/`, add a row to `MAY_NOT_IMPORT` in
`layering.test.ts` on the same commit. An empty row (`[]`) is still a row -- it records
that the new section has no forbidden imports on purpose.

## Routing

The API answers only under `/api` (ADR-0002): the client owns every other path. That is
one proxy rule in dev (`vite.config.ts`) and one `handle` in Caddy -- no list of either
side's routes to keep in step by hand. At scaffold time: `/` (health status), `*`
(NotFound).

**A constraint the next screen must respect:** any screen that displays per-item `detail`
must be complete without it and must use a per-item renderer rather than a generic one
(`docs/03-architecture.md`'s "Nothing generic renders per-game detail" translated to the
client side).
