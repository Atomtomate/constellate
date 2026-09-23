# 03 — Architecture

> **The standard a change is held to.** What this page states was decided by
> [ADR-0002](adr/0002-the-stack.md); where a detail waits on another question it names that
> question rather than guessing. None of it exists as code yet: the scaffold PR lays it out.

*Last updated: 2026-09-23*

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

`scripts/check_layering.py` enforces this and arrives with the scaffold PR, ported to package
`constellate` and given a rule for `sources/`, which the sibling's check has no place for: a port
that changes only its constants passes both an adapter importing `repos/` and a service
importing an adapter, so the port carries a test for each. Until it exists a reviewer reads the
imports. The per-layer rules in detail go
in `api/src/constellate/CLAUDE.md`, which arrives with the same PR, and this page stays the
summary it expands. The website's own layer rule arrives with `web/`.

## Not decided here

Named so nobody fills the gap by typing:

- The domain model — what an event, an item and a creator are, and how an item on two sources
  is one item: Q-C, in `docs/02-domain-model.md` once written.
- What each source gives, how often the poller runs, and whether an extension exists: Q-D, in
  the two data-source documents.
- The host, and what keeps Postgres and the scheduled task running there: Q-E.
- How the owner signs in, which M1 needs.
- The API's conventions — the error envelope's codes, pagination, how times travel. The
  scaffold PR's plan writes them into this page before its first endpoint, where the plan's
  review sees them; the sibling project's (one error envelope for every error, cursor
  pagination, ISO-8601 UTC times) are where option A starts.
