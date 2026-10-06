# `api/` — the backend

FastAPI, SQLAlchemy 2 and Alembic on Postgres (ADR-0002); the package is `constellate`, under
`src/`. Read the root `CLAUDE.md` first; this covers only what is specific to the Python
codebase. The layering is `src/constellate/CLAUDE.md`'s, the migrations `alembic/CLAUDE.md`'s
and the tests `tests/CLAUDE.md`'s.

## Running it

The venv is `.venv/` here — its interpreter `.venv/Scripts/python.exe` on Windows,
`.venv/bin/python` elsewhere — and a worktree needs its own: from `api/`, `python -m venv .venv`,
then `pip install -e ".[dev]"` with that interpreter, which is also what CI installs. Run
everything from `api/` with the venv's tools; the commands below assume its `Scripts/` (or
`bin/`) is on PATH.

```bash
pytest -q                               # SQLite in memory; no Docker needed
ruff check . && ruff format .           # lint, then format
python scripts/export_openapi.py        # after ANY change to the API surface; --check is CI's
uvicorn constellate.main:app --reload   # then http://127.0.0.1:8000/api/docs
python -m constellate.poll              # the poller: logs that no source is configured, exits 0
alembic upgrade head                    # needs Postgres: docker compose up -d, from the repo root
```

The app is served under `/api` and knows it (`docs/03-architecture.md`, Conventions):
`/api/health`, `/api/health/ready` and FastAPI's own `/api/docs`, the same straight from uvicorn
as through the dev proxy or Caddy. Postgres is the one `compose.yaml` at the repository root
describes; on the dev PC that server is the sibling project's container, and `infra/README.md`
says how the `constellate` database and role get onto it.

Settings are `config.py`'s `Settings`, read from `CONSTELLATE_`-prefixed environment variables
or an `.env` in `api/`: `CONSTELLATE_DATABASE_URL`, defaulting to the development database
`infra/postgres/init-constellate.sql` creates (at `127.0.0.1`, never `localhost`, which on
Windows resolves to `::1` first and waits out libpq's connect timeout), and
`CONSTELLATE_LOG_LEVEL`, default `INFO`, a standard level name — an unknown one stops the
process at startup. A setting belongs to whoever adds it (`.claude/agents.local.md`, file
ownership).

## What CI fails you on

`.github/workflows/api.yml`, on any change under `api/`; the hooks run the same checks first
(`scripts/gates.py`'s `api` area: ruff on commit, pytest and the contract check on push), and
`.github/workflows/record.yml` runs `scripts/check_layering.py` over `src/constellate/`. Beyond
lint and tests, each of these exists because it covers a way the project can rot silently:

- **`ruff check`** carries the `D1` docstring rules, the linter the root `CLAUDE.md`'s Style
  promises, off only where that rule exempts: `tests/**`, and the generated revisions under
  `alembic/versions/**`.
- **`openapi.json` must match the code** — `python scripts/export_openapi.py --check`.
  Regenerate it in the same commit as the change, then `web/`'s client from it
  (`web/CLAUDE.md`).
- **Migrations must match the models and every revision must revert** — the round trip and the
  drift check, CI's alone because both need a live database (`alembic/CLAUDE.md`).
- **The tests pass on Postgres too**, not only on the SQLite the hook runs (`tests/CLAUDE.md`).

## Python conventions

- **Type hints on everything public.** Modern syntax: `str | None`, `list[str]`, no `Optional`
  or `typing.List`.
- **Pydantic v2 for anything crossing a boundary** — requests, responses, settings. SQLAlchemy
  2.0 `Mapped[...]` for tables.
- **Sync, not async.** A blocking call inside an `async def` stalls the event loop, and the
  failure is invisible until it is a slow endpoint. FastAPI runs plain `def` endpoints in a
  threadpool, which is correct at any load this project will see (`db.py` says the same).
- **What crosses the wire is `docs/03-architecture.md`'s Conventions** — the envelope and the
  service errors a router raises in place of an `HTTPException`, times, the request id, the
  `/api` base — and this file does not repeat them. `services/errors.py` is the list of errors a
  router may raise.
- **Logging is `src/constellate/CLAUDE.md`'s**: who configures it, and what a log line may not
  carry.
- **Bound every input that reaches a column.** An unbounded string hitting a `VARCHAR` is a 500
  for a user's mistake.
- Keep modules flat until they hurt; split a file when reading it stops being comfortable, not
  before.

## Adding a dependency

Rare, and worth justifying in the commit message; `pyproject.toml` groups them with a comment
each, and a dependency belongs to whoever is adding it, as a setting does. Anything that
duplicates what Pydantic, SQLAlchemy, FastAPI or the standard library already does is a no.
