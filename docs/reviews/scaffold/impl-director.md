# impl-director plan — scaffold PR (plan of record)

*Authored 2026-10-05 at the plan-before-code round. This file did not exist when the three
specialists planned; they cut against `impl-director-brief.md` directly, which was thorough
enough to carry them. This is the director's cut of record, folding the reconciliations the
`impl-director-check-1.md` round produced, and updated after `impl-director-check-2.md`
(2026-10-05): the conftest env-var name pinned to `CONSTELLATE_TEST_DATABASE_URL`, venv
sync ownership named, sign-in plumbing added to Not-in-scope, and decision 5 (the `infra`
area while Q-E is open) added. Updated once more at the review fold (2026-10-06): the owner's
answers recorded under "Owner's answers", the Not-in-scope clause they reverse struck, and the
two lines overtaken by PR #1's merge and the public repository corrected. It writes no code
(fleet "Plan before code").*

Branch `claude/scaffold`, planned stacked on PR #1 (`ADR-0002`). PR #1 merged on 2026-10-05
before the code was written, so the branch is on `main` and the PR says "merge after" nothing.

## Open decisions for the owner (settle before code starts)

1. **API conventions** (`docs/03` requires them written before the first endpoint; health is
   the first). Recommend the sibling's as-is: one error envelope
   `{"error": {"code", "message", "fields"}}` with a closed `ErrorCode` literal; cursor
   pagination (pattern only — no list endpoint ships here); ISO-8601 UTC times; `X-Request-ID`
   on every response. The session writes these into a new `docs/03` "Conventions" section.
2. **Where the development Postgres runs.** Recommend a new `constellate` database and role on
   the sibling's existing Docker Postgres (port 5432), created by a repo-root `compose.yaml`;
   the default URL lives in `config.py`. Owner's call, next to Q-E.
3. **What the API tests run against.** Recommend the sibling's dual setup: SQLite in-memory by
   default, Postgres via `CONSTELLATE_TEST_DATABASE_URL`; the round-trip and autogenerate
   checks are CI-only (need a live database; Docker was down when checked).
4. **Empty modules vs "no dead code"** (root `CLAUDE.md` style constraint). The lanes diverge
   here, so it must be settled once and applied to all three. Recommend: scaffold the package
   skeleton only where it carries real content now — `models/` (Base), `services/`
   (`services.errors`), `api/` + `routers/` (health); defer `domain/`, `sources/` and
   `poll.py` to their first code (Q-C/Q-D). Two sub-calls inside this one decision: whether
   `repos/__init__.py` exists now as the enforced service-to-repo boundary (database wants it;
   backend calls it premature — leaning: keep it, it documents the one seam a service must
   route through), and whether the ORM `Owned` mixin and `ids.py` are ported now though no
   table uses them yet (leaning: yes, they are the foundation the first migration needs and are
   cheap). `web`'s empty `queryKeys.ts` is the same question on the client side; apply the
   same answer.

5. **The `infra` gate area's checks, with Q-E still open.** `ADR-0002`'s appendix defines the
   `infra` area as checking the stack script's tests and that the Caddyfile validates — files
   (`infra/stack.py`, the Caddyfile) whose content is Q-E's (the host, the public name). The
   scaffold must have the `infra` area and `infra.yml` (brief item 4), but building those two
   files now is building into Q-E. Recommend: the scaffold's `infra` area carries only
   `compose.yaml` (decision 2) and the `docker` probe; the Caddyfile-validate and
   stack-script-test checks arrive with Q-E's PR, which the overlay's gate-area table already
   frames as conditional. Surfaced by the backend plan's infra-area spec; the owner's call
   next to Q-E.

## Owner's answers, 2026-10-05

As the coordinator handoff of 2026-10-06 records them ("Decisions the owner took"), and what
the code cites as "decision N":

1. **API conventions**: the sibling's, as is. Written into `docs/03`'s Conventions section.
2. **Development Postgres**: shared with the sibling's Docker instance, through a repo-root
   `compose.yaml`.
3. **Tests**: dual — SQLite by default, `CONSTELLATE_TEST_DATABASE_URL` for Postgres.
4. **Empty modules**: **every layer scaffolded now**, against the director's leaning. So
   `domain/`, `sources/` and `poll.py` ship with the scaffold — `poll.py` as the entry point
   that logs no source is configured and exits 0; what the poller does against a source stays
   out of scope with the adapters. The sub-calls go the same way: `Owned` and `ids.py` ported
   now, `repos/__init__.py` now, `web`'s `queryKeys.ts` now.
5. **The `infra` gate area**: checks only `compose.yaml` and the `docker` probe; the
   Caddyfile and stack-script checks arrive with Q-E's PR.

## The cut (who owns what) and the order

Ownership follows `.claude/agents.local.md`'s map. Three lanes, two worktrees.

- **`impl-database`** (`api/` worktree, goes first): `pyproject.toml` (structure and its deps),
  `config.py` (`database_url` only), `ids.py`, `models/base.py` and `models/__init__.py` (Base,
  and the `Owned` mixin per decision 4), `repos/__init__.py` (per decision 4), `db.py`,
  `alembic/` (`env.py`, `script.py.mako`, `alembic.ini`, empty first migration
  `0001_scaffold`), and its tests (`conftest.py` engine/session/provisioning fixtures,
  `test_db_engine.py`, `test_migrations.py` with `0001_scaffold` in `NO_ROWS`).
- **`impl-backend`** (`api/` worktree, after database): `__init__.py`, `main.py`,
  `config.py` (its settings, amending database's), `logging_config.py`, `services/errors.py`,
  `api/errors.py`, `api/request_id.py`, `api/deps.py` (imports `db.get_session` — hard
  dependency on database's `db.py`), `routers/health.py`, `api/scripts/export_openapi.py`,
  its test fixtures and `test_health.py`, and `api/openapi.json` (generated last).
- **`impl-frontend`** (its own `web/` worktree, fully parallel): the `web/` toolchain and
  source per its plan; only `web/src/api/schema.d.ts` and `check:api-types` wait on
  `api/openapi.json`.
- **Session (no specialist owns these)**: the `docs/03` Conventions section (decision 1) and
  the cleared "arrives with scaffold PR" markers (overlay banner and its
  contract/layers/toolchain sections, `docs/03`, root `CLAUDE.md` banner); the per-directory
  `CLAUDE.md` files (`api/`, `api/src/constellate/`, `api/alembic/`, `api/tests/`, `web/`);
  `scripts/check_layering.py` ported to `constellate` with the `sources/` rule and its two
  `scripts/tests/` cases; the `api`/`web`/`infra` gate areas in `scripts/gates.py` (adding
  `VENV`, `PROBES`, the `ci_only` field) with their workflows, and the layering check added to
  `record`; `compose.yaml` and `infra/` per decision 2. The `infra` gate area and `infra.yml`
  exist here (brief item 4), but `ADR-0002`'s appendix checks for it — stack-script tests,
  Caddyfile validate — presume `infra/stack.py` and a Caddyfile whose content Q-E governs;
  the scaffold's `infra` area checks only what exists now (`compose.yaml` / the `docker`
  probe), and those two checks arrive with Q-E's PR (decision 5).

**Order.** Settle the four decisions. Then: the session writes the `docs/03` Conventions
section (decision 1); `impl-database` lays the `api/` foundation; `impl-backend` builds the API
and exports `api/openapi.json`; `impl-frontend` generates `schema.d.ts`. The session's
`check_layering.py` port, `gates.py` areas and `CLAUDE.md` files can proceed alongside once the
layer layout is fixed; the marker-clearing is last. `impl-frontend`'s non-schema work runs from
the start in its own worktree. At most two opus runs at once: frontend plus one `api`-lane run. The
`api/.venv` is created by `impl-database` with the db deps (enough for its smoke tests) and
re-synced by `impl-backend` after it amends `pyproject.toml`, so both lanes' deps are present
before `pytest` runs.

## Hand-offs, concretely

- **Health**: `GET /health` returns `200 {"status": "ok"}` (no DB); `GET /health/ready`
  returns `200 {"status": "ready"}` (runs `select 1` through `SessionDep`, the one sanctioned
  SQL outside `repos/`). Two endpoints, not one — accepted, because `/health/ready` proves the
  db wiring end to end in a PR that has no tables.
- **Contract to client**: `impl-backend` runs `python scripts/export_openapi.py` from `api/`,
  committing `api/openapi.json`; `impl-frontend` runs `npm run generate:api-types` to produce
  `web/src/api/schema.d.ts`, and `check:api-types` diffs it against the committed contract.
- **Error schemas as components**: `api/openapi.json` must expose `ErrorBody` and `FieldError`
  as named `components.schemas` (FastAPI emits Pydantic models so by default), because
  `web/src/api/errors.ts` imports `components["schemas"]["ErrorBody"]` and `["FieldError"]`.
- **Shared `api/tests/conftest.py`**: `impl-database` lays the engine / session_factory /
  session_override / per-run provisioning fixtures (built from `models/`); `impl-backend` adds
  the fixtures that need the app — `client` and `anon_client`. The app-dependent fixtures are
  backend's; database does not own `client`. The per-run Postgres URL override is read from
  `CONSTELLATE_TEST_DATABASE_URL` (decision 3's name — not `CNL_*`, which the database plan
  drifted to), and the scaffold `conftest.py` sets no sign-in or session env, that plumbing
  being out of scope (see Not in scope).
- **Shared `config.py` and `pyproject.toml`**: database creates each with its own field/deps;
  backend amends with its settings/deps (overlay's shared-exception rule).

## Contract impact

`api/openapi.json` is created for the first time — entirely additive, no prior contract, so
nothing breaking for a generated client. It carries only the two health paths, the error
envelope components and the `X-Request-ID` header.

## Not in scope (so no lane builds it helpfully)

Any endpoint but health; any table or column (the schema is the migration chain alone until
Q-C); the poller, the sampler, any source adapter or importer; the scheduled task; sign-in and its
plumbing — the session-cookie test env, the 401->reset-`['me']` QueryClient wiring,
`RequireSession`, session hooks, ported only with sign-in (M1); the extension (`extension/`, Q-D);
the domain model (Q-C, PR #4). The in-flight PRs #2/#3/#4 and the post-merge consolidation
PR also touch `docs/03`, the overlay, root `CLAUDE.md` and `docs/08`; this PR edits only the
`docs/03` Conventions section and the "arrives with scaffold PR" markers, and keeps clear of
the questions those PRs answer.

## Verification (by command)

- Local (no Postgres): from `api/` — `ruff check .`, `ruff format --check .`,
  `python -m pytest -q` (SQLite in-memory; health and db-engine smoke), and
  `python scripts/export_openapi.py --check`. From root —
  `python scripts/check_layering.py` (no violations) and
  `python -m unittest discover scripts/tests` (the two `sources/` cases and `test_gates.py`).
- From `web/`: `npm ci`, `npm run generate:api-types`, `npm test` (layering and error tests),
  `npm run build`, `npm run check:api-types`.
- CI-only (live Postgres): `alembic upgrade head`, then `downgrade base`, then `upgrade head`,
  and `alembic revision --autogenerate` producing an empty diff. GitHub Actions runs on this
  repository since 2026-10-05, when it went public, so `api.yml` runs these against its Postgres
  service; the `.githooks` pre-commit/pre-push run the rest, and name these as CI's alone on
  their result line.
