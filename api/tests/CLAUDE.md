# `tests/`

Read the root `CLAUDE.md` and `api/CLAUDE.md` first.

## How they run

SQLite in memory by default, so `pytest -q` from `api/` needs no Docker. **CI also runs the
whole suite against Postgres** (`.github/workflows/api.yml`), because ADR-0002 chose Postgres
for what SQLite does not have — `timestamptz`, local-day bucketing in the database — and the
two disagree about types often enough to matter, so the SQLite pass alone cannot answer for the
backend production uses. The hooks run the SQLite pass only; `scripts/gates.py` names the gap
on its result line.

Set `CONSTELLATE_TEST_DATABASE_URL` to run locally against Postgres:
`postgresql+psycopg://constellate:constellate@127.0.0.1:5432/constellate_test`. It must name a
database whose name ends in `_test` — `conftest.py`'s `is_disposable` refuses anything else,
an allow-list because the danger is a database someone else owns — and the role must be able
to `CREATE DATABASE`, which `infra/postgres/init-constellate.sql` grants `constellate`. The
named database's own tables are never touched: that connection only creates the run's own
`constellate_<8hex>_test` database and drops it afterwards, so concurrent runs do not collide.
Once, on the development server: `docker compose exec db createdb -U constellate
constellate_test` — or `docker exec boardgame-tracker-db-1 createdb -U constellate
constellate_test` on the dev PC, where the sibling's container is the server
(`infra/README.md`).

`conftest.py` chooses the run's database and sets `CONSTELLATE_DATABASE_URL` to it *before*
importing `constellate.db`, because `db.py` builds its engine at module scope from the settings
as they stand at import; the late import there is load-bearing, and so is the autouse
`_pg_database` fixture, since `test_db_engine.py` reaches that engine directly and requests no
fixture of its own.

**What is CI's alone**: the Postgres pass, and the Alembic round trip and drift check
(`alembic/CLAUDE.md`). No Postgres-only migration cases exist yet — the first real table
migration brings the first — and the coverage registry test there runs everywhere.

## Fixtures

Two halves, two owners (`.claude/agents.local.md`, file ownership): the ones built from
`models/` — `_pg_database`, `engine`, `session_factory`, `session_override` — are
`impl-database`'s; the ones that need the app — `client`, `anon_client` — are `impl-backend`'s.
`session_override` points the app's `get_session` at the test engine and, like production, does
**not** commit, so a write path that forgets to commit fails a test instead of passing on the
fixture's goodwill. `client` goes through the whole app — middleware, error handlers — even for
`/health`, so a test sees what a client would. `anon_client` is the same object as `client`
until sign-in (M1), when `client` gains a bearer token and `anon_client` does not; write a test
against the one it means now, so nothing changes when they diverge.

## Conventions

- **A test name is its documentation.** `test_unknown_path_is_not_found_in_envelope` beats
  `test_404` and a docstring. The `D1` docstring rules are off here under the root
  `CLAUDE.md`'s Style, which exempts tests; add a docstring only where the *why* is not
  obvious from the name — usually to record the bug the test exists to prevent.
- **One reason to fail.** Shared setup helpers are encouraged; parametrisation that obscures
  which case broke is not.
- **Duplication in tests is fine.** A test should be readable without scrolling to understand a
  fixture. Do not DRY these the way you would production code.
- **Test through the API where the behaviour is reachable through it.** `test_health.py` is the
  pattern: what the contract promises — the envelope on an unroutable path, the `X-Request-ID`
  header on every response — is asserted on the wire, because that is what the clients see.
- **Fixtures must not paper over the code.** See the session fixture above.

## What a bug fix owes

Every fixed defect gets a test that **fails before the fix**. Write it first and watch it fail;
a regression test that never failed is proof of nothing. Name it for the behaviour, and record
the original symptom in a docstring where it is surprising.

## What not to test

Framework behaviour, SQLAlchemy itself, or that Pydantic validates. Test the rules this project
invented.
