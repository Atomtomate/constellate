# impl-database plan — scaffold PR

*Plan-before-code round, revised 2026-10-05 per director check-1.*
*Branch: `claude/scaffold`, stacked on PR #1.*

---

## What my lane builds

The database layer's deliverables for the scaffold PR are structural: the ORM base, the
session factory, the Alembic wiring, and an empty first migration. No tables and no
queries yet — the domain model (Q-C) has not been written, and the brief explicitly
excludes any schema content. The pieces that arrive now are what every later migration and
repo depends on.

---

## Files, exact paths

`<pkg>` is `api/src/constellate/`.

### Created by this lane

**`api/src/constellate/models/__init__.py`**
Exports `Base`; once decision 4 is settled and the `Owned` mixin is included, exports
`Owned` as well. Re-exports table classes as they are added in later PRs. In the scaffold
there are no table classes. This is the module `api/alembic/env.py` imports to register
`Base.metadata`.

**`api/src/constellate/models/base.py`**
`DeclarativeBase` subclass and the `Owned` mixin (UUIDv7 primary key, `created_at`
timestamp with time zone), ported from `bgtracker/models/base.py` with `bgtracker`
replaced by `constellate` and `uuid7` imported from `constellate.ids`. The `Owned` mixin
is included here if decision 4 keeps it (director recommendation: yes); it is deferred if
the owner rules against it. `id` defaults to a callable generating UUID v7 at insert time;
`created_at` uses `server_default=func.now()` so the database clock owns the timestamp.

**`api/src/constellate/db.py`**
Sync SQLAlchemy engine and `get_session` dependency, ported from `bgtracker/db.py`:
`create_engine` with `pool_pre_ping=True`, `future=True`, `hide_parameters=True`;
`SessionLocal` with `autoflush=False`, `expire_on_commit=False`; `get_session` as a
generator that rolls back on exception and closes in `finally`, and deliberately does
not commit. The URL comes from `config.settings.database_url`.

**`api/alembic/env.py`**
Alembic environment, ported from the reference. Reads the URL from
`constellate.config.settings` (one source of truth). Imports `constellate.models.Base`
with `# noqa: F401` to register all tables on `Base.metadata`. Supports the
`config.attributes["connection"]` path for the migration test harness (caller-supplied
connection, so the test's per-run database is migrated rather than what `database_url`
resolves to). Sets `compare_type=True` and `compare_server_default=True` on Postgres so
autogenerate catches column type and default drift.

**`api/alembic/script.py.mako`**
Template for generated revisions, ported verbatim from the reference.

**`api/alembic/versions/0001_scaffold.py`**
The empty first migration. `upgrade()` and `downgrade()` contain only `pass`. Its purpose
is to start the revision chain at a known id before any table definition exists, so the
first real table migration has a `down_revision` to point at. Revision id: `0001_scaffold`.

**`api/alembic.ini`**
Standard Alembic configuration at `api/alembic.ini` (beside `pyproject.toml`). Ported
from the reference with `script_location` set to `%(here)s/alembic` and `sqlalchemy.url`
left empty (overridden at runtime by `env.py`). Commands run from `api/`.

**`api/tests/conftest.py`**
Shared test fixtures, ported from `bgtracker/tests/conftest.py`. This lane lays the
model-built fixtures only; `impl-backend` adds the app-dependent fixtures (`client`,
`anon_client`) on top:

- `TEST_DATABASE_URL` from `CNL_TEST_DATABASE_URL` env var, defaulting to `sqlite://`.
- `_RUN_DATABASE_URL`: for Postgres, a unique `constellate_<8hex>_test` name chosen
  before `constellate.main` is imported (so the module-scope engine in `db.py` points at
  the per-run database, not the configured one — same trick and same reason as the
  sibling, reference comment `#292`).
- `is_disposable`: the allow-list guard — only in-memory SQLite and `*_test`-suffixed
  databases may be acted on.
- `_pg_database` (autouse, session-scope): creates the per-run Postgres database, yields
  it, drops it in `finally`. SQLite passes through unchanged.
- `engine` (function-scope): drops and recreates `Base.metadata` tables in the per-run
  database. In the scaffold this creates nothing (no tables yet); the fixture is present
  because later migrations populate `Base.metadata` and expect it.
- `session_factory` (function-scope): `sessionmaker` bound to the test engine.
- `session_override` (function-scope): wires the app's `get_session` dependency to the
  test database for the duration of one test.

`client` and `anon_client` are not in this lane's section of the conftest: both wrap the
FastAPI app, which is backend's. The overlay rule applies — the construction of `models/`
objects in a test body belongs to whoever changed the model, not to the file's owner.

**`api/tests/test_db_engine.py`**
One smoke test: `engine.connect()` succeeds on SQLite by default. Verifies that `db.py`,
`config.py` and the sessionmaker wire together without a live Postgres.

**`api/tests/test_migrations.py`**
Minimal coverage registry for the empty first migration. `NO_ROWS` contains
`"0001_scaffold"`. The `test_all_revisions_are_covered_or_no_rows` assertion walks the
`ScriptDirectory` and passes — the empty migration touches no rows. Runs on SQLite; no
live database needed for the `ScriptDirectory` walk.

---

### Files shared with impl-backend (created by this lane, amended by that one)

**`api/pyproject.toml`**
This lane creates the file with the full project structure (metadata, build system, ruff
and pytest config) and only the database dependencies: `sqlalchemy>=2.0`,
`psycopg[binary]>=3.2`, `alembic>=1.14`. `impl-backend` amends it with its own
dependencies (FastAPI, uvicorn, pydantic, pydantic-settings). The shared ruff and pytest
config is in this file; neither lane changes it unilaterally.

**`api/src/constellate/config.py`**
This lane creates a minimal `Settings` class with `database_url` only.
`impl-backend` adds its settings (session secret, cookie settings, etc.) in a later
commit without touching `database_url`.

---

### Files contingent on owner decision 4

The following are included if decision 4 (empty modules vs "no dead code") resolves in
their favour. The director's recommendation is to keep both; the owner's call stands.

**`api/src/constellate/repos/__init__.py`** (per decision 4)
Module declaration and docstring only: "Queries. The only part of the project that knows
SQL." No functions until the first table exists. If decision 4 keeps it, it is the
documented seam the layering check enforces — a service that imports `models/` directly
has skipped this module. If decision 4 defers it, this file does not arrive until the
first query.

**`api/src/constellate/ids.py`** (per decision 4)
`uuid7` generator, ported from `bgtracker/ids.py`. Imported by `models/base.py` for the
`Owned` mixin's default. If decision 4 keeps the mixin, `ids.py` must exist when
`models/base.py` is written and is this lane's to create (it is a leaf imported by the
lowest layer; the ownership map rule "to the lower one where both import it" lands it
here). If decision 4 defers the mixin, `ids.py` can wait; `models/base.py` still exists
with only `Base`, and `Owned` is added alongside `ids.py` in the first migration PR.

---

## What I will not do

- No table definitions. Q-C is not answered.
- No repository functions. No tables means no queries to write.
- No migration beyond the empty first one.
- No health endpoint (`api/routers/health.py` is `impl-backend`'s).
- No `main.py`, `poll.py`, `sources/`, `domain/`, `services/` (all `impl-backend`'s,
  or deferred per decision 4 for those not yet decided).
- No `client` or `anon_client` fixtures — those wrap the app and are `impl-backend`'s.
- No data-migration test case for `0001_scaffold`: the empty migration touches no rows and
  goes in `NO_ROWS`.

---

## Verification (by command)

**Without a live Postgres (dev machine, no Docker needed):**
```
cd api && .venv/Scripts/python.exe -m pytest tests/test_db_engine.py tests/test_migrations.py -q
cd api && .venv/Scripts/python.exe -m ruff check . &&
    .venv/Scripts/python.exe -m ruff format --check .
```
The venv is created by `impl-backend` as part of the pyproject.toml step; my files pass
lint and the smoke tests without a database.

**With a live Postgres (CI or once Docker Desktop is running):**
```
cd api && alembic upgrade head
cd api && alembic downgrade base
cd api && alembic upgrade head
cd api && alembic revision --autogenerate -m "check" --head-only
```
The last command must produce an empty diff. The round-trip verifies that the empty
migration's `downgrade()` is a no-op and re-applies cleanly. Both are in the `api`
workflow gate (ADR-0002 appendix) and run in CI, not in the pre-commit hook.

---

## Build order and parallel execution

My files have no dependency on `impl-backend`'s work beyond the shared `config.py` and
`pyproject.toml`. The coordination points are:

| What | Who creates | Who amends |
|------|-------------|------------|
| `api/pyproject.toml` | `impl-database` (structure + db deps) | `impl-backend` (fastapi, uvicorn, pydantic) |
| `api/src/constellate/config.py` | `impl-database` (`database_url` only) | `impl-backend` (remaining settings) |
| `api/src/constellate/ids.py` | `impl-database` (if decision 4 keeps it) | neither (complete as written) |
| `api/tests/conftest.py` | `impl-database` (engine, session, provisioning) | `impl-backend` (app, `client`, `anon_client`) |

`impl-frontend` has no dependency on any of my files. My work and `impl-frontend`'s
scaffold run fully in parallel in separate worktrees.

`impl-backend` can start once I have committed `db.py` and `models/__init__.py`. Sequence
in the shared `api/` worktree: my commits first, `impl-backend`'s on top.

---

## Where the brief's premises did not survive

**The domain model is absent.** `docs/03-architecture.md`'s `models/` layer implies
tables; the brief says none yet. The empty migration resolves this: the chain starts, the
models module has only the base, and table definitions arrive with PR #4. No design call
needed — the brief is explicit.

**`alembic.ini` placement.** The reference places it at `api/alembic.ini` beside
`pyproject.toml`. This is standard and the commands in the sibling's `CLAUDE.md` run from
`api/`. The scaffold follows this layout; naming it here to prevent a
"why is it not inside `alembic/`?" question.
