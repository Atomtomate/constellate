Plan the scaffold PR for Constellate: the cut across the three specialists, the order, the
hand-offs, the decisions for the owner, and how it is verified. You write no code and no file but
your plan (and a friction note, if you have one).

## Where

- Repository `Atomtomate/constellate` (private). Your worktree is `C:\wt\constellate-scaffold`,
  on branch `claude/scaffold`, created from `origin/main` at `<MAIN_HEAD>`, which holds `ADR-0002`
  (merged as PR #1). Work only there. Do not `cd` to the main checkout
  `C:\Users\Atomt\Documents\favorites_tracker`, which other sessions share.
- Write your plan to `docs/reviews/scaffold/impl-director.md` in that worktree: plain Markdown,
  files named in backticks and never as links, since `scripts/check_docs.py` walks `docs/`.

## Read first

The root `CLAUDE.md`; `.claude/agents.local.md`, whose file-ownership map is the ground you cut
along; `docs/03-architecture.md`, the standard the scaffold must meet; `docs/adr/0002-the-stack.md`,
especially its Consequences and its appendix's gate-area table; `docs/adr/0001-…`;
`docs/07-roadmap.md` (M1) and `docs/08-open-questions.md`; `scripts/README.md`,
`scripts/gates.py`, `scripts/tests/test_gates.py` and `.github/workflows/record.yml`, the gate
machinery the new areas plug into; and `python scripts/open_work.py --fetch` for what is in flight.

**The reference implementation**, read-only: `C:\Users\Atomt\Documents\boardgame-tracker`, the
owner's sibling project, whose stack `ADR-0002` adopts "as is". Other sessions work there. Read it,
never write to it, and run nothing there that writes (no install, no migration, no git command
that changes state). What it has that this scaffold ports: `api/` (`pyproject.toml`, `alembic/`,
the `src/bgtracker/` layout, `scripts/export_openapi.py`, `tests/conftest.py`) and its four
`CLAUDE.md` files (`api/`, `api/src/bgtracker/`, `api/alembic/`, `api/tests/`); `web/` (its
`package.json`, the Vite config, the generated-client script, `src/layering.test.ts`) and
`web/CLAUDE.md`; `scripts/check_layering.py` and its tests; `scripts/gates.py`'s `AREAS`;
`.github/workflows/{api,web,infra}.yml`; `infra/`. That repository is private, so nothing
committed here may link into it: Constellate's docs stand on their own.

## What "done" is

The owner's list, relayed by the coordinating session on 2026-09-23:

1. `api/` laid out per the overlay's map, package `constellate`, with `pyproject.toml`, ruff
   (docstring rules on, per the root `CLAUDE.md`'s style), pytest, Alembic wired to Postgres
   with an empty first migration, and a health endpoint.
2. `api/openapi.json` exported by `api/scripts/export_openapi.py` and checked by its `--check`.
3. `scripts/check_layering.py` ported to package `constellate` **with the `sources/` rule** that
   `docs/03` states — a source imports only `domain/` and the leaves, satisfies the interface
   `services/` declares structurally, and no layer imports it — and **two tests** in
   `scripts/tests/`: an adapter importing `repos/` or `models/`, and a service importing an
   adapter. A port that changes only the constants passes both; `pr-tech-review` verified that on
   2026-09-23 against a fake package, so each test must fail against such a port.
4. The `api`, `web` and `infra` gate areas in `scripts/gates.py`, with their workflows under
   `.github/workflows/`, and `scripts/tests/test_gates.py` green. The `record` area gains the
   layering check (`ADR-0002`'s appendix table).
5. `web/` scaffolded (React + Vite + TypeScript) as a consumer of the client generated from
   `api/openapi.json`, with its layer rule and the test that enforces it.
6. The per-directory `CLAUDE.md` files, with the sibling's set as the model. The "arrives with the
   scaffold PR" markers cleared: the overlay's banner and its contract, layers and toolchain
   sections; `docs/03`'s paragraph under its layers; the root `CLAUDE.md`'s banner.

**Not in scope:** any endpoint but health; any table or column, since the schema is the
migration chain alone; the poller, the sampler, any source adapter or importer; registering a
scheduled task; sign-in; the extension; the domain model (Q-C, on PR #4). Say what the plan
excludes so no specialist builds it helpfully.

## Already decided — do not reopen

- **`ADR-0002`, Accepted 2026-09-23**: the sibling's stack as is (FastAPI, SQLAlchemy 2, Alembic,
  Postgres, `api/openapi.json` committed and generated from, React + Vite + TypeScript); the
  poller a one-shot command fired by the OS scheduler.
- **The poller's shape** (the owner, 2026-09-23): Spotify's playback sampler and the
  export-plus-Last.fm path together. The poller is a bounded sampling run that the OS scheduler
  fires, every five minutes or so, for a run that exits after a few; it is the same entry point
  as the other sources. Nothing writes the sampler before the scaffold has the seam, so not in
  this PR.
- **The scaffold is M1's first bullet** (the owner, 2026-09-23). M0 is done.

## What is known, so you need not establish it

- **GitHub Actions does not run**: the account's billing state stops jobs before they start
  (2026-09-23). The hooks `.githooks/pre-commit` and `.githooks/pre-push`, which call
  `scripts/gates.py`, are the CI that actually runs, so every verification step must run
  locally. `core.hooksPath` is set to `.githooks`.
- On the dev machine: Python 3.13.14, Node 24.9.0 and npm 11.6.0 are on PATH. There is no global
  ruff and no `psql`. **Docker Desktop was not running** when checked, and the sibling's Postgres
  is a container under it. Say what verifies Alembic without a live database, and what needs one.
- **No specialist owns `scripts/`, `.github/`, `infra/` or the `CLAUDE.md` files**: the overlay
  gives them to the session. Items 3, 4 and 6, and the `infra` area, sit there. Say who does
  each, the session or a specialist you propose with the reason, and in what order relative to
  the specialists' steps.
- **In flight**: PRs #2 and #3 (the data sources, Q-D), and #4 (the domain model, and `ADR-0003`
  Proposed, the ingestion seam). A consolidation PR after #1 and #4 merge will add Q-E's
  requirement, fix `review_briefs.py`'s repository name, add `ADR-0003`'s standing constraints and
  answer questions in `docs/08`; none of that is this PR's. Where your plan touches a file those
  touch (`docs/03`, the root `CLAUDE.md`, the overlay, `docs/08`), say so.
- **Concurrency**: at most two opus runs at once, and two specialists writing in one worktree
  collide. Say which steps run in parallel and whether each needs a worktree of its own.

## Decisions I expect you to surface

Recommend an answer for each, and add any others you find:

- **The API's conventions**: the error envelope, pagination and how times travel. `docs/03` says
  the scaffold's plan writes them there before the first endpoint, and the health endpoint is the
  first. The sibling's (one envelope for every error, cursor pagination, ISO-8601 UTC times) are
  where option A starts.
- **Where the development Postgres runs**: its own container and port, or a database on the
  sibling's instance. This is next to Q-E and is the owner's.
- **What the API tests run against**: SQLite in memory, as the sibling's do, or Postgres, which
  `ADR-0002` chose for `timestamptz` and local-time bucketing.
- **Empty modules against "no dead code, no speculative parameters"** (the root `CLAUDE.md`):
  whether `sources/`, `poll.py` and the other layers exist as empty packages now, or arrive with
  their first code.

## Your plan, and the round after it

The plan in execution order, with the open decisions first. The hand-offs are concrete: the
health endpoint's path and response shape, the generated client's command and output path, and
each gate area's paths and checks in `gates.py`'s spelling. Give the contract impact, what is
not in scope, and how each step is verified, by command. Each specialist then drafts its own
plan before any code, and the session brings those plans back to you for a direction check
(the fleet's "Plan before code").

Return at most fifteen lines: the open decisions, the order, the path to the plan. After that,
only those of Follow-ups, Friction and What carried it whose answer is not None.
