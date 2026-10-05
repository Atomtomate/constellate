# impl-director direction check — scaffold PR, round 1

*2026-10-05. Direction and broader-context check of the three specialist plans against
`docs/03-architecture.md`, `ADR-0002`, the overlay's ownership map, the fleet build order and
the brief's scope. Implementation detail inside a layer is the specialist's; it is not judged
here.*

Plans read: `impl-database-plan.md`, `impl-backend-plan.md`, `impl-frontend-plan.md`. None
missing. Note: `impl-director.md` did not exist when they planned — all three cut against the
brief directly and said so. I have authored `impl-director.md` as the plan of record this round;
see "Changes to my own plan" below.

## Per lane

### impl-database — settled (with the shared decision 4 to reconcile)

- Ownership correct: `models/`, `repos/`, `db.py`, `alembic/`, tests under `api/tests/` are all
  this lane's. `config.py` (`database_url`), `pyproject.toml` and `ids.py` are handled per the
  map's shared-exception rules; `ids.py` is reasoned to the importing lower layer (database),
  which is where the map lands it. No ownership break.
- Empty first migration (`0001_scaffold`) and the chain starting there is exactly brief item 1.
  `test_migrations.py` with the revision in `NO_ROWS` is within-lane and reasonable; not a
  direction matter.
- Build order respected: this lane is the foundation the other two build on.
- Reconcile: the lane creates `repos/__init__.py` (and the `Owned` mixin plus `ids.py`) calling
  them structural, not dead code — the backend lane reaches the opposite conclusion on the same
  question. That is the owner's decision 4, not a per-lane call; both lanes must match whatever
  is decided. Also: the lane lists a `client` fixture in the shared `conftest.py`, but `client`
  wraps the app (backend's) — see the cross-cutting conftest note.

### impl-backend — settled (one wording fix; the shared decision 4; one hand-off to pin)

- Ownership correct: `api/`, `services/`, `main.py`, `api/scripts/`, `openapi.json` and its
  tests are this lane's. The API conventions, `docs/03` Conventions section and the gate/layering
  work are correctly attributed to the session, not claimed. The item 3/4/6 specs it carries are
  framed as "what the session needs," which is appropriate — and they belong in the director plan
  (now authored).
- API conventions are the sibling's (one envelope, cursor pagination pattern, ISO-8601 UTC,
  `X-Request-ID`) — this is where `docs/03` says option A starts. Serves direction.
- `api/deps.py` importing `db.get_session` is a correct, hard schema-to-API ordering constraint.
- Two health endpoints (`/health` and `/health/ready`) rather than the brief's singular "a
  health endpoint": accepted. `/health/ready` exercising `select 1` through `SessionDep` proves
  the db wiring in a PR with no tables; the `select 1` is the sanctioned exception the layering
  check already carries. Noted, not a revise.
- Fix: the plan's "Contract impact" says `web/` "is a later PR." It is not — brief item 5 puts
  `web/` in this scaffold PR, and `impl-frontend` builds it here consuming `api/openapi.json`
  generated in the same PR. Correct the sentence so the lane does not treat web consumption as
  deferred.
- Reconcile: the lane decides not to stub `domain/`, `repos/`, `sources/` — the opposite of the
  database lane on `repos/`. Owner's decision 4; align the two.
- Pin: `api/openapi.json` must expose `ErrorBody` and `FieldError` as named `components.schemas`
  (FastAPI does this for Pydantic models by default), which `impl-frontend`'s `errors.ts`
  depends on. The plan defines both as Pydantic models, so this holds; stating it as a hand-off
  keeps it from slipping.

### impl-frontend — settled

- Ownership correct: `web/` only, no `api/`, no `extension/` (Q-D unconfirmed; brief excludes).
- Build order respected: everything but `web/src/api/schema.d.ts` and `check:api-types` runs in
  parallel in its own worktree; those two wait on `api/openapi.json`. This is the
  schema-to-contract-to-clients order honoured.
- The `layering.test.ts` threshold (10 to 5), the trimmed `MAY_NOT_IMPORT` table and the omitted
  `web/scripts/` section are within-layer design calls, correctly flagged as such; not judged.
- Strong hand-off catch: `errors.ts` needs `ErrorBody`/`FieldError` as contract components —
  pinned above against the backend lane.
- `queryKeys.ts` created empty-with-docstring is the same empty-module question as decision 4,
  on the client side; folded into that one decision so the answer is consistent across `api/`
  and `web/`.
- Contract impact: none beyond consuming the contract. No direction concern.

## Cross-cutting

- **Build order and parallelism hold.** schema (database) to API+contract (backend) to clients
  (frontend). `impl-frontend` runs in its own worktree from the start; `impl-database` then
  `impl-backend` sequence in the shared `api/` worktree; at most two opus runs at once — all
  three plans agree and respect the concurrency constraint.
- **Shared `conftest.py` collision.** Both the database and backend plans describe authoring the
  ported `conftest.py`, and both list a `client` fixture. `client` wraps the app, which is
  backend's. Resolution (now in the director plan): database lays the engine / session /
  per-run-provisioning fixtures built from `models/`; backend adds the app-dependent `client`
  and `anon_client`. This matches the overlay's shared-fixture rule and the layering direction.
- **Decision 4 is one owner decision, not three lane calls.** The database and backend lanes
  decided the empty-module question oppositely for `repos/`, and the frontend lane made its own
  call for `queryKeys.ts`. Surfaced once below; the lanes conform to the answer.

## Changes to my own plan

`impl-director.md` did not exist (a gap from the prior director run; the brief stood in for it
and carried the specialists). I authored it this round as the plan of record, folding in what
the plans surfaced: (1) decision 4 stated as one owner decision applied to all three lanes,
including `web`'s `queryKeys.ts`; (2) the `conftest.py` split pinned (database the model-built
fixtures, backend the app-dependent `client`/`anon_client`); (3) the `ErrorBody`/`FieldError`
as-components hand-off pinned between backend and frontend; (4) `web/` affirmed as in this PR,
not deferred; (5) the session-owned items 3/4/6, `docs/03` Conventions and marker-clearing
assigned and ordered. The four open owner decisions and the build order are unchanged from the
brief; nothing in the plans forced a re-cut.

## Open owner decisions as they now stand

1. **API conventions** — recommend the sibling's as-is (one error envelope with a closed
   `ErrorCode`, cursor pagination pattern only, ISO-8601 UTC, `X-Request-ID`); the session
   writes them into a new `docs/03` Conventions section before the health endpoint.
2. **Dev Postgres** — recommend a new `constellate` database/role on the sibling's Docker
   Postgres (port 5432) via a repo-root `compose.yaml`; default URL in `config.py`.
3. **API test backend** — recommend dual: SQLite in-memory default, Postgres via
   `CONSTELLATE_TEST_DATABASE_URL`; the round-trip and autogenerate checks CI-only.
4. **Empty modules vs "no dead code"** — the one the lanes diverge on. Recommend scaffolding
   only what carries content now (`models/` Base, `services/`, `api/`+`routers/`), deferring
   `domain/`, `sources/`, `poll.py`; keep `repos/__init__.py` as the one enforced seam and port
   the `Owned` mixin + `ids.py` as the ORM foundation; apply the same answer to `web`'s
   `queryKeys.ts`. Both `api` lanes conform once settled.
