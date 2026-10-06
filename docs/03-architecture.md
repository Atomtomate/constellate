# 03 — Architecture

> **The standard a change is held to.** What this page states was decided by
> [ADR-0002](adr/0002-the-stack.md); where a detail waits on another question it names that
> question rather than guessing.

*Last updated: 2026-10-06*

## Shape

```
  website    --.
               +--HTTPS--> Caddy --> API process ----------.
  extension  --'           (the contract)                  |
  (if Q-D needs one)                                       |  each through
                                                           |  services/ and
  Spotify Web API <--asks-- poller ----------------------->+  repos/, in its
                            (one-shot, OS scheduler)       |  own process
                                                           |
  export files --read by--> importers -------------------->+
                                                           v
                                                       Postgres
```

Four moving parts, on a machine the owner controls (where, and what keeps them running, is
Q-E's):

- **The API process**: FastAPI, Python, package `constellate` in `api/`. It serves the contract
  and is the only way a client reaches the data.
- **The poller**: `python -m constellate.poll`, a one-shot command that asks each pollable source
  for what is new since the cursor it stored, ingests it, stores the new cursor and exits. The OS
  scheduler fires it; it is the same code when the stack script, a test or the owner runs it. It
  stores its last successful run per source, so a poller failing silently cannot pass for a
  quiet day. Which sources are pollable, and how often, is the data-source documents' to say;
  whether Spotify's listened time needs a playback sampler, and with it a bounded sampling run
  rather than a single fetch, is the owner's to confirm with the Spotify document (ADR-0002's
  Consequences).
- **The store**: Postgres. At this scale, around half a million events over a decade, it needs
  indexes and nothing more: no partitioning, no time-series extension, no rollups. It has to be a
  service that starts with its machine, because the poller fires unattended.
- **The clients**: the website (React + Vite + TypeScript in `web/`, built to static files that
  Caddy serves), and a browser extension in `extension/` if Q-D finds YouTube needs one. Any app
  Q-F later names joins them on the same terms.

**Nothing polls a sleeping machine.** What leaves a source's short tail while the host sleeps is
recovered from that source's export, not from the poll; the one ingestion path below is what
makes that recovery add nothing twice.

## The seams

Three rules the whole design rests on. The root [`CLAUDE.md`](../CLAUDE.md) holds them as
standing constraints — the first as two, access and the committed file — and changing one needs
an ADR. This section says what each means for the design.

**The contract is the only path to data.** `api/openapi.json` is committed, checked in CI, and
generated from; every client is a consumer of the client generated from it, on equal terms. No
page is rendered with the database one import away, and no client gets an endpoint another
could not use. The poller, and an importer run as a command, are not clients: they are entry
points inside the API's own package, and they reach the data through `services/` as a router
does.

**One ingestion path.** Every source — the Spotify poll, the Spotify export, the Takeout file,
the extension's request — is an adapter producing the same draft event, and exactly one service
persists it. Adding a source is one new adapter, never a second write path. Ingestion is
idempotent: a poll that overlaps the last one, or an export that repeats what polling already
stored, adds nothing twice. The draft event's fields are the domain model's (Q-C); the key that
recognises a polled play and an exported play as the same play is each data-source document's;
whether an import is a command or an upload through the website is Q-D's detail. Whichever, it
enters through that one service.

**One language per deployable.** Python for the API package — the API process, the poller, the
importers. TypeScript for the website, and for the extension as a deployable of its own. Nothing
crosses a language boundary but the contract.

## Layers inside the API package

Thin layers, one direction. The value is that the middle ones know nothing about HTTP or SQL.

```
api/        routers, request and response schemas, the error envelope
services/   use cases; orchestrates repos, domain, and the interfaces sources implement
repos/      queries: the only module that knows SQL
models/     SQLAlchemy tables: the database's shape
domain/     types and rules, the draft event among them; no I/O of any kind
sources/    one adapter per source: HTTP or a file format in, draft events out; never SQL
```

- **Dependencies point one way**: `api/` → `services/` → `repos/` → `models/`. A router that
  imports from `repos/` has skipped a layer.
- **`domain/` is usable by anything and imports none of the four** — not `models/`, not
  `repos/` — because the ORM is the database's shape and the rules are not.
- **`sources/` is reached only through an interface `services/` declares.** Nothing in the four
  layers imports a module of `sources/`: a service calls the interface, and an entry point hands
  it the concrete adapter. One source's outage then degrades that source and nothing else. A
  source knows an external API or a file format, and imports only `domain/` and the leaves: it
  satisfies the interface structurally rather than by subclassing it, so neither `services/` nor
  `sources/` imports the other.
- **Outside the layers, a module is a leaf or an entry point.** A module a layer reaches
  (`config.py`, `db.py`) is a leaf, usable by anything and importing none of the four. A module
  nothing reaches is an entry point, above `api/`: `main.py` wires `api/` together, and
  `poll.py`, the poller, and any importer run as a command may reach `services/`. Nothing imports
  an entry point.

`scripts/check_layering.py` enforces this, ported to package `constellate` and given a rule for
`sources/`, which the sibling's check had no place for: a port that changed only its constants
would pass both an adapter importing `repos/` and a service importing an adapter, so the port
carries a test for each under `scripts/tests/`. It runs in CI (`record.yml`) and from the
pre-commit hook on any change under `api/`. The per-layer rules in detail are
`api/src/constellate/CLAUDE.md`'s, and this page stays the summary it expands; the website's
own layer rule is `web/CLAUDE.md`'s, enforced by `web/src/layering.test.ts`.

## Conventions

The API's conventions, settled 2026-10-05 by the owner with the scaffold PR's plan
(`docs/reviews/scaffold/impl-director.md`, decision 1): the sibling project's, as they are. They
are settled before the first endpoint because every client generates from the contract, so a
convention changed later is a change to every client. What holds them is `api/openapi.json`; this
section is where their meaning is written. Paths in it are inside the API package,
`api/src/constellate/`.

**One origin, the API under `/api`.** The website and the API share one origin, and a reverse
proxy in front of both — `web/vite.config.ts`'s in development, Caddy on the rig once Q-E names
it — decides per request which answers: everything under `/api` is the API's, and the website
owns every other path, so neither side keeps a list of the other's routes. Every path in the
contract is relative to that base — `GET /health` is `GET /api/health` from a browser — and
everything the API serves moves with it, FastAPI's `/docs` included, since one route left at the
root is a one-entry path list. Three parts carry it, and a test under `api/tests/` holds each:
`main.py` passes `root_path="/api"` to the `FastAPI(...)` constructor, not a `--root-path` flag a
launch path can forget, so routing, redirects and the docs page all know the prefix; the proxy
passes the prefix through unstripped — Caddy `handle`, never `handle_path`; no `rewrite` in the
Vite proxy — because Starlette builds a trailing-slash redirect's `Location` from the request
path without re-adding `root_path`, and behind a stripping proxy `/api/health/` would redirect to
a bare `/health`, into the website's half of the origin; and the contract declares
`servers: [{"url": "/api"}]` explicitly, because FastAPI derives that entry from `root_path`
only inside the `/openapi.json` route at request time, so `app.openapi()` — which
`export_openapi.py` calls — never sees it, and the committed spec would differ from the served
one through the one door the contract check cannot see. `openapi-fetch` does not read
`servers`, so on the web side the prefix exists in one place, `web/src/api/client.ts`'s
`baseUrl`.

**One error envelope.** Every error, whatever raised it, leaves in one shape:

```json
{"error": {"code": "not_found", "message": "...", "fields": [...]}}
```

`fields` is present only on a malformed request, as a list of `{"location": [...], "message"}`
naming each offending part; otherwise the key is omitted. `code` is a closed set, a `Literal` in
`api/errors.py`, so that it reaches the contract as an enum and a generated client can switch on
it exhaustively; stated as prose, each client would hand-copy the strings and drift alone. The
scaffold ships the generic codes:

| `code` | Status | Means |
|--------|--------|-------|
| `invalid_request` | 422 | Unreadable: a malformed body, a bad parameter. Carries `fields`. |
| `not_found` | 404 | The thing referenced does not exist. |
| `conflict` | 409 | Collides with something that already exists. |
| `unauthenticated` | 401 | The caller is not signed in. Carries `WWW-Authenticate: Bearer`. How the owner signs in is M1's; the code exists now so the contract does not change when it arrives. |
| `forbidden` | 403 | Signed in, but not allowed. |
| `internal_error` | 500 | Nothing more specific caught it. A fixed message, never the exception's text, so no stack detail reaches a client. |

A product code is added by the endpoint that needs it, in the same `Literal` and in this table.
The sibling's `rule_violated` — 422, well-formed but breaking a rule — is the shape of the first
one, which arrives with the first rule a request can break (`docs/02-domain-model.md`); two 422s
sharing a status is deliberate, since 422 *is* "well-formed but semantically wrong", and the
`code` separates them. Where the codes come from: `services/errors.py` holds one exception class
per code except `internal_error`, each carrying no status of its own; `api/errors.py` maps class
to status and code in one place, registers the handlers, and maps the few `HTTPException`s
Starlette raises itself (an unroutable path, a rejected dependency) back to the same codes by
status. A router raises a service error and never an `HTTPException`, and attaches `RESPONSES`
so the contract advertises the error statuses it can return — without that the spec claims 200
and 422, and every 404 is invisible to codegen.

**Cursor pagination.** The pattern, since no list endpoint ships with the scaffold. A list
endpoint takes `cursor`, an opaque string absent on the first page, and `limit`, bounded, with a
default the endpoint states (the sibling's: 50, at most 200), and returns
`{"items": [...], "next_cursor": ...}` — `next_cursor` is the string to pass back as `cursor`
for the next page, and `null` on the last. Keyset, never offset: the cursor encodes the sort key
of the last item returned (base64 of it, in a module beside the router, as the sibling's
`api/cursor.py`), so a page costs the same at the end of a decade of events as at the start, and
a row that arrives between two fetches — a poll landing mid-scroll — does not shift the pages
behind it. A client never reads inside a cursor, and a malformed one is `invalid_request`. A
keyset cursor only works over an order the endpoint fixes, so the order of a returned list is
the endpoint's, published in its description, and no client re-sorts it. This cursor is a page's
position in a response and nothing else; the *source cursor* of `docs/02-domain-model.md` is a
different thing with a shared word.

**Times.** Every instant on the wire is ISO-8601 in UTC with a trailing `Z` —
`2026-10-05T14:00:00Z` — in a response and in a request alike. In the package an instant is an
aware `datetime` in UTC and Pydantic writes the `Z`; a naive one is a bug. Which zone buckets an
instant into a local day is `docs/02-domain-model.md`'s open point, and nothing here pre-empts
it: a local day, where an endpoint returns one, is a date, and the instants it was built from
travel as above.

**`X-Request-ID`.** Every response carries an `X-Request-ID` header: an opaque id minted per
request by an ASGI middleware in `api/request_id.py`, never read from the request, and the same
id on every log line the request writes, so a client's report of a failure matches one line of
the server's log. It is declared once in the contract, under `components.headers`, and
referenced from every operation's responses, so a generated client sees it. The 500 path sets
the header itself, because Starlette sends an unhandled error's response outside the
middleware's wrapped `send`; the module says so where it does it.

**Health.** The scaffold's two endpoints, and the first the conventions apply to. `GET /health`
answers `200 {"status": "ok"}` and touches no database: the process is up. `GET /health/ready`
answers `200 {"status": "ready"}` after one `select 1` through the session dependency: the
process is up and can reach its database — and that `select 1` is the one sanctioned SQL outside
`repos/`, named as such in `scripts/check_layering.py`. A database that does not answer is a 500
in the envelope, `internal_error`, which is what a probe for whatever keeps the process running
wants to see. Both carry the request id; neither is paginated or carries a time.

## Not decided here

Named so nobody fills the gap by typing:

- The domain model — what an event, an item and a creator are, and how an item on two sources
  is one item: Q-C, in `docs/02-domain-model.md` once written.
- What each source gives, how often the poller runs, and whether an extension exists: Q-D, in
  the two data-source documents.
- The host, and what keeps Postgres and the scheduled task running there: Q-E.
- How the owner signs in, which M1 needs.
