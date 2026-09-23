# ADR-0002 — The stack: the sibling project's, with the poller as a scheduled command

- **Status:** Proposed
- **Date:** 2026-09-23

## Context

Q-B in [`docs/08-open-questions.md`](../08-open-questions.md) asks which stack, and nothing is
built until it is answered. This ADR argues the options for the owner to decide. It is written
before the two data-source documents (`01-data-sources-spotify.md`, `01-data-sources-youtube.md`)
exist, so it leans on nothing beyond Q-D's stated leanings, and its Consequences name where their
answer could change it.

**What the product needs.** From [`docs/00-vision-and-scope.md`](../00-vision-and-scope.md) and
[`docs/07-roadmap.md`](../07-roadmap.md):

- **A poller that runs all day.** Spotify's recently-played endpoint returns only a short tail
  of plays, so it has to be asked often enough that nothing falls off the end (Q-D). It runs on
  a machine the owner controls (Q-E, open) — today that would be a PC, and a PC sleeps — and it
  has to come back from a sleep without losing what the source still holds.
- **A store that holds years of events**: one per play or watch, with an item, a creator, a
  start and a duration (Q-C, open), exportable whole in a plain format at any time (00's success
  criteria).
- **A private website that reads it back**, phone-friendly: a timeline, and totals by day, week
  and month and by artist, channel, track and video. One user; the owner signs in (M1).
- **Room for what comes after**: the atlas on the same items (M2, M3), and "a system of apps"
  (Q-F). One of those apps may be needed at M1 already: Q-D's leaning is that live capture of how
  long a YouTube video was actually watched needs something running where the watching happens,
  a browser extension or userscript. A browser runs JavaScript, so that extension is TypeScript
  whatever else is chosen.

**The scale is small, and time-series concerns with it.** A heavy day is on the order of a hundred
plays and a few dozen videos; a decade of that is around half a million events, a few hundred
megabytes even with each source's raw record kept beside the parsed one. Every total the site
shows is an indexed scan of that. No partitioning, no time-series database or extension, no
pre-aggregated rollups are needed — named here so that none is added for this reason.

**What the fleet imposes.** ADR-0001 mounted the fleet, whose implementers are split by file
ownership — `impl-database`, `impl-backend`, `impl-frontend` — along a map in
[`.claude/agents.local.md`](../../.claude/agents.local.md) that is empty until this ADR is
accepted. So the stack has to be one that:

- divides into trees two of those agents can change at once without colliding;
- has a contract the clients generate from, so that the fleet's build order — schema, then API
  and contract, then clients — means something (the overlay's "The contract, and the order",
  today *not yet*);
- has a layering the architecture reviewer can check by running something rather than by
  reading every import (the overlay's "Layers, architecture, and the standard", *not yet*).

**What already exists.** The owner's sibling project, the board-game tracker, runs FastAPI,
SQLAlchemy, Alembic and Postgres, with an OpenAPI contract committed as `api/openapi.json` and
checked in CI, a React + Vite + TypeScript client generated from it, all served from the owner's
PC behind Caddy and driven by `infra/stack.py` for `ops`. Its ownership map, its layering
(`api/` → `services/` → `repos/` → `models/`, with `domain/` pure) and the script that enforces
it (`scripts/check_layering.py`) are what the fleet was built against. ADR-0001 copied that
project's record scripts and left its product checks out, to return with a stack. The owner is
fastest in Python.

## Options

Three stacks; then the poller and the store, which are decided largely independently of which
stack carries them.

### A — The sibling's stack, as is

Python 3.13, FastAPI, SQLAlchemy 2 with Alembic, Postgres; `api/openapi.json` committed and
generated from; React + Vite + TypeScript in `web/`, built to static files; Caddy in front.

*For it.* The ownership map is the sibling's with the package renamed, and the layering check
ports with its constants changed, so the fleet runs on ground it already knows. The part that
must work is in the owner's fastest language. An extension, a phone app or whatever Q-F names is
one more client of a contract that already exists, on equal terms with the website — the
sibling's one structural rule. The rig (Caddy, a public name, `stack.py`) is there to reuse if
Q-E says so.

*Against it.* The most machinery of the three: two toolchains from the first milestone, a
code-generation step between them, a single-page app for screens that at M1 only read, and a
database server to keep running. For one user's timeline that is more than day one needs; it is
paid for by what comes after — the extension, the apps — and by the fleet's parallelism.

### B — Python only, lighter

FastAPI or Flask, SQLite, pages rendered on the server with Jinja and made interactive with HTMX.
One toolchain, one process, and a file for the store.

*For it.* The fastest route to a first screen, by some distance: no Node, no code generation, no
client build. The store is a file that is backed up by copying it and needs no server running
when the poller fires. Phone-friendly is CSS either way.

*Against it.* It trades away the contract, and the saving is smaller than it looks. An extension
that posts watch events, or any app Q-F names, needs a JSON API, which B then grows beside its
pages with no contract — the sibling's `docs/03-architecture.md` describes that path ("a hastily
bolted-on `/api` when the phone app arrives") as the one that produces two data models, and its
`ADR-0015` rejected this option for that reason. The fleet's split degenerates: a page is a view
function and a template changed together, so `impl-backend` and `impl-frontend` would each own
half of every screen and could not work on one in parallel; in practice it is two agents,
database and everything else. And there is no line between the pages and the data for the
architecture reviewer to hold, since the templates render in the process that holds the queries.

### C — TypeScript end to end

SvelteKit or Next.js, Postgres through Drizzle or Prisma, the extension in the same language and
the same repository.

*For it.* One language across the server, the website and the extension; types shared by import
rather than by generation; server rendering and API routes in one framework. The owner already
knows TypeScript — the sibling chose React for its web client because it was the one already
known (its `ADR-0015`).

*Against it.* It moves the part that must work — the poller, the parsing of exports, the store —
out of the owner's fastest language. Both frameworks put a page's server loader beside its
component in the same route directory, so the ownership line runs through the files of every
directory rather than between trees: expressible (`*.server.ts` the backend's, the component the
frontend's), but new, and a server component that reads the database directly is a client with
privileged access, which is what a contract exists to prevent. The contract, if there is one, is
TypeScript types (tRPC, or zod schemas) that a non-TypeScript client cannot consume, so a native
app later needs OpenAPI bolted on. None of the sibling's product tooling carries over, and the
fleet would be learning a new shape during the first milestone.

### The poller: what fires it

Three ways to run a job all day on a machine that sleeps. **None of them polls a sleeping
machine.** Each can catch up when it wakes, provided the job asks the source for everything since
a cursor it stored and writes idempotently, so that an overlap is harmless — and the job has to
do both whichever of the three fires it. What separates them is what happens after a reboot, a
crash, or a morning on which nobody started anything.

- **In-process: APScheduler inside the API.** One process to supervise, and the schedule is code
  in the repository; its coalescing and misfire grace time turn the runs missed during a sleep
  into one late run. But it polls only while the web process runs, so a deploy or a crashed API
  stops capture; it runs twice under `--reload` or a second worker; it adds a dependency that a
  loop would replace; and a scheduler thread started from `main.py` is an entry point hidden in
  the wiring, which the layering has no place for.
- **A separate worker process**: a long-running loop, its own process. Decoupled from the web
  process, portable, one log. But it is a fourth process to keep alive, and after a reboot or a
  crash something has to start it again — `stack.py up` if somebody runs it, or an OS task at
  logon, at which point the OS scheduler is doing the work anyway.
- **An OS scheduled task firing a one-shot command** — fetch, ingest, store the cursor, exit:
  Task Scheduler on a Windows rig, a cron line or a systemd timer on a Linux one. It survives a
  reboot and a crash with nothing of ours supervising it; a failed run is retried by the next
  firing; every run starts clean. Task Scheduler has a setting to run a missed start as soon as
  possible (`StartWhenAvailable` in its task XML) and one to wake the machine for a run
  (`WakeToRun`) — the two a sleeping PC wants; named from memory of that schema, to be verified
  when the task is written. The cost: the schedule lives in the OS rather than in the code unless
  the repository commits the task's definition and a script installs it, and that definition is
  platform-specific. The command is the portable part.

### The store: Postgres or SQLite

At this scale both are comfortable for decades; the question is which inconveniences to own.

*Postgres* is the sibling's and the fleet's ground — `impl-database`'s habits, the Alembic rules,
`ops`. `timestamptz`, and `date_trunc` in the owner's time zone, are the tracker's central query —
totals by local day, week and month — done in the database. Full-text and trigram search are
there when the atlas asks "who were those creators again?". Concurrent writers (the poller, an
extension, the website) need no thought. The cost is a server that must be running when the
poller fires. On the sibling's rig that server is a container under Docker Desktop, which that
project's root `CLAUDE.md` records as "not always running"; a poll that meets a stopped database
fails, and waits for the next firing.

*SQLite* is a file: nothing to start, a backup is a copy, the poller writes whether or not
anything else is up, and the tests run on the production engine. Its costs: no `timestamptz`, so
times are stored in UTC and bucketed into local days in Python or through a stored local-date
column; Alembic alters tables in batch mode; one writer at a time, which in WAL mode is no
constraint at this rate; and a later move to a server — if the apps or a second user ask for
one — is a migration of data, not only of code.

## Decision

**Proposed: option A, the sibling's stack as is, with the poller as a one-shot command fired by
the OS scheduler and Postgres as the store.** In full:

- Python 3.13, FastAPI, SQLAlchemy 2, Alembic and Postgres in `api/`, package `constellate`, laid
  out and layered as the sibling's `api/src/bgtracker/` is.
- The contract is `api/openapi.json`: committed, checked in CI, generated from. The build order is
  the fleet's.
- The website is React + Vite + TypeScript in `web/`, a consumer of the generated client with no
  privileged access to anything.
- The browser extension, if Q-D needs one, is a second TypeScript client of the same contract in
  `extension/`, its own deployable, so the sibling's one-language-per-deployable rule (its
  `ADR-0013`) holds.
- The poller is `python -m constellate.poll`, an entry point beside `main.py` that asks each
  pollable source for what is new since its stored cursor, and exits; the OS scheduler fires it.
  It writes through the same service as the importers and the extension's endpoint: **one
  ingestion path**, every source an adapter producing the same draft event (the roadmap's second
  sequencing rule; the draft's shape is Q-C's).

The reasons, strongest first:

1. **It is the only option whose ownership map is already proven.** M0 is done when an
   implementation agent can be briefed against a map (the roadmap), and A's is the sibling's
   renamed, with the check that holds it. B collapses the three-way split to two; C makes it an
   experiment run during the first milestone.
2. **A contract is needed early whatever is chosen.** If Q-D confirms the extension, the website
   is not M1's only client; if it does not, Q-F's apps are the next. B's saving is repaid at the
   first of them.
3. **Python is where the owner is fastest**, and the part that must work — polling, parsing
   exports, date arithmetic over years of events — is Python-shaped work.
4. **The OS scheduler is the one trigger that survives a sleep, a reboot and a crash with nothing
   of ours supervising it**, and a one-shot command is the same code whether the OS, the stack
   script, a test or the owner runs it.
5. **Postgres keeps the fleet's ground and does the central query natively.** Its one real cost,
   a server that must be up, is a requirement on Q-E's answer rather than a reason to leave it
   (Consequences).

## Consequences

- **What leaves the source's tail while the machine sleeps is not polled.** No trigger changes
  that. The design makes it a gap the export closes rather than a loss: a poll takes everything
  since its cursor, ingestion is idempotent, and the backfill importer reconciles against what
  polling already stored. The worst-case delay for a play made during a long sleep is then the
  export's turnaround, days to weeks by Q-D's leaning. A host that does not sleep (Q-E) removes
  the gap; `WakeToRun` narrows it at the price of waking the PC.
- **Postgres has to be a service that starts with the machine**, wherever Q-E puts it, not a
  container someone starts by hand, because the poller fires unattended. If Q-E settles on a host
  where that cannot be promised, SQLite is the better store and the switch costs nothing before
  the first migration: this ADR is then revised, not worked around.
- **Capture has to be observable.** A poller failing silently looks exactly like a quiet day. The
  last successful poll per source is stored, shown on the site, and reported by the stack
  script's `status`.
- **The scheduled task's definition belongs in the repository**, committed under `infra/` with
  the script that installs it, so the schedule is reviewed like code. `infra/` stays edited from
  the session with no specialist, as in the sibling.
- **Two toolchains from M1**, Python and Node, and a generated client to keep in step. Accepted
  for the reasons above.
- **Accepting this ADR is a PR of its own.** It moves the appendix's map into
  `.claude/agents.local.md` and fills the overlay's contract and layering sections; ports
  `check_layering.py`, and adds the appendix's areas to `scripts/gates.py` and the CI workflows;
  writes `docs/03-architecture.md`; adds the committed contract and the one ingestion path to the
  root `CLAUDE.md`'s standing constraints; and records Q-B as answered. The standard review pass
  runs on that PR.
- **Not decided here**: the domain model (Q-C); where it runs (Q-E); what the apps are (Q-F); how
  the owner signs in, which M1 needs (the sibling's `ADR-0014` is a starting point, not a
  precedent); the poll interval, which is the Spotify document's to set.
- **Where the data-source research could change this.**
  - *Whether YouTube needs an extension* (`01-data-sources-youtube.md`). If it does, M1 has a
    second client: reason 2 is confirmed, `extension/` and its gate area exist from the start, and
    TypeScript is on M1's critical path, which narrows C's gap without closing it, since the
    generated client gives the extension typed calls. If Takeout and the Data API suffice, the
    website is M1's only client, reason 2 rests on Q-F alone and B becomes more defensible; A
    still holds on reason 1.
  - *Whether Spotify can be polled at all, and how often* (`01-data-sources-spotify.md`). The
    tail's length sets the interval, not the trigger. If the recently-played endpoint turns out
    unusable, nothing polls — YouTube cannot be polled, per Q-D — and the requirement to run all
    day disappears, with the scheduler question.
  - *How a polled play and an exported play are recognised as the same play.* That shapes the
    ingestion service's idempotency key, not the stack.

## Alternatives considered

- **B, Python only, pages rendered on the server, SQLite.** Fastest to the first screen. Lost on
  the contract and on the split: the first client that is not the website needs a JSON API that B
  grows without one, and its screens cannot be divided between two agents. The sibling rejected
  the same option for the same reason (its `ADR-0015`).
- **C, TypeScript end to end.** Coherent, and the natural choice for someone faster in
  TypeScript. Lost because it moves the part that must work out of the owner's fastest language,
  runs the ownership line through every route directory, and ties the contract to TypeScript
  clients.
- **APScheduler inside the API.** Lost because capture would stop whenever the web process does,
  and would run twice under reload.
- **A long-running worker.** Lost because something has to restart it after a reboot or a crash,
  and that something is the OS scheduler.
- **SQLite as the store.** Close, and the right answer if Q-E cannot keep a database server
  running. Lost on the fleet's ground and on local-time bucketing in the database — not on scale.
- **A hosted database or platform** (managed Postgres, a serverless host). Excluded by the vision,
  which keeps the log "on infrastructure the owner controls".
- **A time-series database or extension.** Named only to be excluded: half a million rows over a
  decade is not a time-series problem.

## Appendix: File-ownership map (draft)

The table the overlay's "File ownership" section takes when this ADR is accepted, for option A.
`<pkg>` is `api/src/constellate/`. The line between database and backend is SQL: `repos/` is the
only module that knows it.

| Agent | Owns | Never touches |
|-------|------|---------------|
| `impl-database` | `<pkg>/models/`, `<pkg>/repos/`, `<pkg>/db.py`, `api/alembic/`, and their tests under `api/tests/` | routers, services, sources, the contract |
| `impl-backend` | `<pkg>/api/`, `<pkg>/services/`, `<pkg>/domain/`, `<pkg>/sources/`, `<pkg>/main.py`, `<pkg>/poll.py`, `api/openapi.json`, and their tests under `api/tests/` | migrations, SQL |
| `impl-frontend` | `web/`, and `extension/` if Q-D calls for one | anything under `api/` |

No specialist owns `infra/` — the stack script, the Caddyfile, the scheduled task's definition and
its installer — which is edited from the session as in the sibling; nor the record (`docs/`,
`scripts/`, the `CLAUDE.md` files, the overlay).

`sources/` is new against the sibling: one adapter per source — the Spotify Web API client, the
Spotify export parser, the Takeout parser — each producing draft events and knowing HTTP or a file
format, never SQL. It is reached only through an interface `services/` declares, so one source's
outage degrades that source and nothing else (the sibling's rule for integrations, in its
`docs/03-architecture.md`). `poll.py` is an entry point above `api/`, like the sibling's
`seed.py`: it may reach `services/`, and nothing reaches it.

The sibling's two rules that make its map a partition come with it, and the accepting PR copies
them rather than deriving them again: a module the rows do not name belongs to the agent whose
layer imports it, the lower where both do, with `config.py` belonging to whoever adds the
setting; and a break in constructing a `models/` object in a test belongs to whoever changed the
model.

**The CI areas `scripts/gates.py` would gain**, each with its workflow, in the sibling's shape:

| Area | Workflow | Paths | Checks |
|------|----------|-------|--------|
| `record` (exists) | `record.yml` | `**` | gains the layering check, `scripts/check_layering.py`: quick, narrowed to `api/**` and the script |
| `api` | `api.yml` | `api/**` | `ruff check` and `ruff format --check` (quick); `pytest`; `export_openapi.py --check`; and, CI's alone since they need a live database, migrations that upgrade cleanly and autogenerate an empty diff |
| `web` | `web.yml` | `web/**`, `api/openapi.json` | the generated client matches the contract; the web tests; the build |
| `extension` | `extension.yml` | `extension/**`, `api/openapi.json` | the same three as `web`, if Q-D calls for an extension |
| `infra` | `infra.yml` | `infra/**`, `.github/workflows/**` | the stack script's tests (quick); the Caddyfile validates |

`compose.yaml` joins `infra`'s paths if Q-E runs Postgres from one.
