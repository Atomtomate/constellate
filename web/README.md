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

The API must be running separately on `127.0.0.1:8000` -- from `api/`, activate its venv
and run `uvicorn constellate.main:app --reload`. `vite.config.ts` proxies `/api` to it,
matching what Caddy does in every other environment: the proxy decides which side answers
`/api` requests and the website owns every other path, so neither side keeps a list of
the other's routes (docs/03-architecture.md Conventions, "One origin").

**Set `API_PROXY_TARGET`** to point the dev proxy at an API on another port instead of
`127.0.0.1:8000` -- a branch's own uvicorn running beside the rig's, say. `vite.config.ts`
reads it; left unset, it keeps that default.

```bash
npm run build         # tsc -b && vite build; static output in dist/, what Caddy serves
npm run preview       # serve that build locally
npm test              # vitest run; test files live beside their modules as *.test.ts(x)
```

## The generated API client

`src/api/schema.d.ts` is generated from `api/openapi.json` by `openapi-typescript` and
**committed**, the same rule `openapi.json` itself follows and for the same reason --
without a committed, checked copy the type the client compiles against can drift from
the server it talks to.

```bash
npm run generate:api-types   # regenerate after api/openapi.json changes
npm run check:api-types   # CI: regenerate, then fail if that changed the committed file
```

`src/api/client.ts` wraps `openapi-fetch` into the one client every screen calls through
-- typed against that schema, `credentials: "include"` for the session cookie, base URL
`/api` since the API lives there and `openapi-fetch` does not read the spec's `servers`
entry.

## Layer rules

`web/CLAUDE.md`'s "Layer rule" section is the single statement of the rules that
`src/layering.test.ts` enforces. The test reads `src/` off the filesystem so a file added
later is covered without being listed.

## Routing

The API answers only under `/api`: the client owns every other path. That is
one proxy rule in dev (`vite.config.ts`) and one `handle` in Caddy -- no list of either
side's routes to keep in step by hand. At scaffold time: `/` (health status), `*`
(NotFound).

