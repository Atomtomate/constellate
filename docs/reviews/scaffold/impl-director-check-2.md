# impl-director direction check — scaffold PR, round 2

*2026-10-05. Direction and broader-context check of the three specialist plans as they now
stand against `docs/03-architecture.md`, `ADR-0002`, the overlay's ownership map, the fleet
build order (schema -> API+contract -> clients) and the brief's scope. Implementation detail
inside a layer is the specialist's and is not judged here.*

Plans read: `impl-database-plan.md` (revised after check-1), `impl-backend-plan.md` (revised
after check-1), `impl-frontend-plan.md` (unchanged since check-1 — it was settled then, and an
unrevised settled plan is fine). None missing. The three round-1 reconciliations all landed:
the `conftest.py` split (database the model-built fixtures, backend the app-dependent `client`
/`anon_client`), the `ErrorBody`/`FieldError` as-named-components hand-off, and backend's
"`web/` is in this PR, not later" correction. What follows is the small set that surfaced this
round. All three lanes are directionally sound — correct ownership, correct build order,
correct scope, no ADR contradiction, decisions properly surfaced rather than taken by accident.
The verdicts are `revise` only for narrow folds before code, not re-cuts.

## Per lane

### impl-database — revise (two narrow folds)

- **Env-var name drift.** The plan reads the per-run test database URL from `CNL_TEST_DATABASE_URL`
  (its line 72). The plan of record's decision 3 and the backend plan both name it
  `CONSTELLATE_TEST_DATABASE_URL`, and `config.py`'s prefix is `CONSTELLATE_` (backend sets
  `CONSTELLATE_DATABASE_URL` in `export_openapi.py`). `conftest.py` is a file both lanes write,
  so the two cannot disagree on the name of the override they share. Align to
  `CONSTELLATE_TEST_DATABASE_URL`. This is a cross-lane hand-off mismatch, not a within-layer
  call — hence the flag.
- **Venv ownership contradiction.** This plan says "the venv is created by `impl-backend`" (line
  163); the backend plan lists `venv` under `impl-database`'s step (its line 261). Neither is
  quite right: `impl-database` needs the venv with the db deps to run its own smoke tests before
  backend exists, and the venv needs backend's deps too before `pytest` on the health test runs.
  Resolution pinned in the plan of record: `impl-database` creates `api/.venv` with the db deps
  (enough for its smoke tests); `impl-backend` re-syncs it after amending `pyproject.toml`.
- Everything else is settled: ownership correct (`models/`, `repos/`, `db.py`, `alembic/`,
  `ids.py` as the leaf the lower layer imports, tests under `api/tests/`); the empty
  `0001_scaffold` and `NO_ROWS` are brief item 1; `repos/__init__.py`, `ids.py` and the `Owned`
  mixin are correctly held as contingent on owner decision 4 rather than decided in-lane; the
  `conftest.py` split matches backend. No schema content, respecting Q-C.

### impl-backend — revise (one scope fold; one note to the session)

- **Sign-in plumbing leftover from the port.** The `conftest.py` row (line 120) says "No auth
  fixtures (sign-in out of scope)" and, in the same breath, "Sets
  `CONSTELLATE_SESSION_COOKIE_SECURE=false` for the test client." There is no session cookie and
  no auth config in this scaffold — the lane's own `config.py` row excludes it — so that env set
  references a setting that does not exist and crosses the brief's "sign-in out of scope" line.
  Drop it from the scaffold `conftest.py`; it returns with sign-in (M1). Scope is a direction
  matter, so this is flagged; how the fixture is otherwise shaped is the lane's.
- **Infra-area advice over-reaches Q-E (a note, not a lane fix).** The "what the session owns"
  section specifies the `infra` area as checking the stack script's tests and that the Caddyfile
  validates. Those files (`infra/stack.py`, the Caddyfile) carry Q-E's content — the host and the
  public name — which is not decided. This is session work, not this lane's, so it is not a
  revise of the lane; it is surfaced as open decision 5 and recorded in the plan of record.
- Settled otherwise: ownership correct (`api/`, `services/`, `main.py`, `api/scripts/`,
  `openapi.json`, app-dependent fixtures, `test_health`), and `infra/`, `compose.yaml`, `web/`,
  `scripts/`, the `CLAUDE.md` files all correctly disclaimed to the session. The API conventions
  are the sibling's, where `docs/03` says option A starts (decision 1). `api/deps.py` importing
  `db.get_session` is the correct hard schema->API ordering constraint. The `ErrorBody`
  /`FieldError` as-named-components hand-off is pinned and honoured (both are `BaseModel`
  subclasses). The full closed `ErrorCode` set including `unauthenticated`/`forbidden` is the
  envelope convention (decision 1), not sign-in implementation — it stands; the owner settles
  decision 1 whole.

### impl-frontend — revise (one scope reconciliation; decision-4 conformance)

- **main.tsx carries sign-in wiring the plan elsewhere defers.** `main.tsx` is described with
  "the `ApiError` session-reset logic from the sibling (a 401 on any query resets `['me']`)"
  (lines 48-49), while the `queryKeys.ts` entry says "the `ME_QUERY_KEY` and session-reset wiring
  in `main.tsx` arrive with the sign-in screen (M1)" (lines 66-68), and "what I do not build"
  lists session hooks as out of scope. The plan contradicts itself, and the 401->reset-`['me']`
  wiring is sign-in plumbing the brief puts out of scope. Carry a plain `QueryClient` in the
  scaffold; the session-reset default arrives with sign-in. (Same leftover as backend's
  `conftest.py`, from the same sibling port.)
- **queryKeys.ts is decision 4 on the client side.** The plan creates it empty-with-docstring so
  `layering.test.ts` can walk it. That is the empty-module question; conform to decision 4's
  answer. The walk threshold (5) holds either way — seven non-test files remain if `queryKeys.ts`
  is deferred.
- Settled otherwise: `web/` only, no `api/`, no `extension/` (Q-D unconfirmed). Build order
  honoured — everything but `schema.d.ts` and `check:api-types` runs parallel in its own
  worktree; those wait on `api/openapi.json`. The threshold, trimmed `MAY_NOT_IMPORT` and omitted
  `web/scripts/` block are within-layer calls, correctly flagged as such. The `ErrorBody`
  /`FieldError` dependency is clearly stated and is now met by backend.

## Cross-cutting

- **Build order and parallelism hold.** schema (`impl-database`) -> API+contract
  (`impl-backend`) -> clients (`impl-frontend`'s `schema.d.ts`). Frontend parallel in its own
  worktree; the two `api` lanes sequence in the shared `api/` worktree; at most two opus runs at
  once. All three plans agree.
- **The shared sign-in leftover.** Backend's `conftest.py` and frontend's `main.tsx` both port a
  sign-in artefact from the sibling into a PR that excludes sign-in. Folded once into the plan of
  record's "Not in scope" so neither lane re-introduces it.
- **The `conftest.py` contract.** The env-var name and the model-vs-app fixture split are the two
  cross-lane facts in that shared file; both are now pinned in the plan of record's hand-offs.

## Changes to my own plan (`impl-director.md`, edited in place)

1. Conftest hand-off: pinned the override env-var name to `CONSTELLATE_TEST_DATABASE_URL`
   (decision 3's name, not `CNL_*`), and stated the scaffold `conftest.py` sets no sign-in/session
   env.
2. Order/hand-off: named venv ownership — `impl-database` creates it with db deps, `impl-backend`
   re-syncs after amending `pyproject.toml`.
3. Not in scope: added sign-in plumbing explicitly (the session-cookie test env, the
   401->reset-`['me']` QueryClient wiring, `RequireSession`, session hooks) as ported only with
   sign-in (M1).
4. Added open decision 5 (the `infra` gate area's checks while Q-E is open) and a matching note
   in the session-owned work.
5. The opening note records the check-2 update.

The cut, the ownership, the four prior decisions and the build order are unchanged — nothing in
the plans forced a re-cut.

## Open owner decisions as they now stand

1. **API conventions** — recommend the sibling's as-is (one error envelope with a closed
   `ErrorCode`, cursor pagination pattern only, ISO-8601 UTC, `X-Request-ID`); the session writes
   them into a new `docs/03` Conventions section before the health endpoint.
2. **Dev Postgres** — recommend a new `constellate` database/role on the sibling's Docker Postgres
   (port 5432) via a repo-root `compose.yaml`; default URL in `config.py`.
3. **API test backend** — recommend dual: SQLite in-memory default, Postgres via
   `CONSTELLATE_TEST_DATABASE_URL` (this exact name — the database lane must drop `CNL_*`); the
   round-trip and autogenerate checks CI-only.
4. **Empty modules vs "no dead code"** — recommend scaffolding only what carries content now
   (`models/` Base, `services/errors`, `api/`+`routers/`), deferring `domain/`, `sources/`,
   `poll.py`; keep `repos/__init__.py` as the one enforced seam and port the `Owned` mixin +
   `ids.py`; apply the same answer to `web`'s `queryKeys.ts`. All three lanes conform once settled.
5. **The `infra` gate area's checks, Q-E still open (new this round)** — `ADR-0002`'s appendix
   defines the area as checking the stack script's tests and the Caddyfile; both files carry
   Q-E's content. Recommend the scaffold's `infra` area + `infra.yml` exist (brief item 4) but
   check only `compose.yaml` / the `docker` probe now, with the Caddyfile-validate and
   stack-script checks arriving with Q-E's PR. The owner's call next to Q-E.
