# impl-backend plan — scaffold PR (revised after director check-1)

Plan for `impl-backend`'s lane of the scaffold PR. No code is written here; this is the
plan-before-code round. Files are named in backticks; none are links.

*Revision notes (2026-10-05, after `impl-director-check-1.md`): three changes from the first
draft — (1) "Contract impact" corrected: `web/` is in this PR, not a later one; (2) the
empty-stub question removed from this lane's recommendations and delegated to owner decision 4;
(3) the `ErrorBody`/`FieldError` as-components hand-off pinned as an explicit constraint.*

## Open decisions surfaced to the owner

These must be answered before code starts in my lane. My recommendation follows each.

### 1. API conventions

`docs/03-architecture.md` says the scaffold's plan writes these there before the first
endpoint. The health endpoint is the first. Recommendation: adopt the sibling's conventions
as-is; they are already proven and the generated client expects them.

- **Error envelope**: `{"error": {"code": ErrorCode, "message": str, "fields": [...] | null}}`.
  One shape for every error. `ErrorCode` is a closed `Literal` — the full set is `not_found`,
  `conflict`, `invalid_request`, `rule_violated`, `unauthenticated`, `forbidden`,
  `internal_error` — so the generated client can exhaustively switch on it. Every response
  schema advertises what status codes it returns via `RESPONSES` on the router. `ServiceError`
  subclasses are mapped to status codes and codes in `api/errors.py`; routers raise service
  errors and never `HTTPException`.
- **Cursor pagination**: `{"items": [...], "next_cursor": str | null}`. Cursor is opaque
  base64, no shape committed to the spec. Arrives with the first list endpoint, not with this
  PR; only the pattern is stated here.
- **Times**: ISO-8601 UTC throughout. Python `datetime` with `timezone.utc`; Pydantic
  serialises them to `2026-10-05T14:00:00Z`.
- **Request ID**: `X-Request-ID` on every response as an opaque string, minted per request by
  `RequestIdMiddleware`. Correlates client reports with log lines. The 500 path handles it
  separately from the middleware (the reference says why).

These four go into `docs/03-architecture.md` under a new "Conventions" section, written by
the session before code starts.

### 2. Development Postgres

The sibling's Postgres is a container under Docker Desktop on port 5432, database
`bgtracker`. Recommendation: use the same Docker instance, a new database `constellate`
with its own role (`constellate:constellate`), also port 5432. Avoids standing up a second
container or a second Docker Compose stack. `compose.yaml` at the repo root creates it; the
default settings URL is
`postgresql+psycopg://constellate:constellate@127.0.0.1:5432/constellate`. If the sibling's
container is already running, `docker exec` creates the role and database; if not, a
`compose.yaml` brings it up. The owner decides; the default URL in `config.py` reflects the
answer.

### 3. API tests: SQLite or Postgres

Recommendation: port the reference's dual-backend setup (SQLite in memory by default,
Postgres optionally with `CONSTELLATE_TEST_DATABASE_URL`). The scaffold's only test is the
health endpoint, so Postgres is academic for this PR. But establishing the pattern now costs
nothing, and M1's date-arithmetic queries will fail silently on SQLite if the setup is not
in place before they arrive.

### 4. Empty package stubs vs. "no dead code" — owner's decision, not this lane's

The database and backend lanes arrived at opposite conclusions on this: `impl-database` kept
`repos/__init__.py` as a structural seam; `impl-backend`'s first draft called it dead code.
The director has settled this as one owner decision (decision 4 in `impl-director.md`) applied
to all three lanes, not a per-lane call. The director's recommendation is: scaffold only where
there is real content (`models/` Base, `services/errors`, `api/` + `routers/`), defer
`domain/`, `sources/` and `poll.py`, keep `repos/__init__.py` as the one enforced seam,
and port `ids.py` and the `Owned` mixin as the ORM foundation.

My lane will follow whatever the owner decides. If `repos/__init__.py` is included, it
belongs to `impl-database`. If `domain/`, `sources/` and `poll.py` are excluded (director's
recommendation), my lane builds nothing for them. The "What I will not do" section below
reflects the director's recommendation; if the owner decides otherwise, that section is
adjusted before code starts.

---

## Files I will build, with exact paths

`<pkg>` is `api/src/constellate`.

### Package root

| File | What it does |
|------|-------------|
| `<pkg>/__init__.py` | Package declaration. |
| `<pkg>/main.py` | FastAPI app. Calls `errors.install(app)` and `request_id.install(app)`. Includes `health.router`. Documents the equal-terms rule in its description string. |
| `<pkg>/config.py` | `pydantic-settings` `Settings` class. `CONSTELLATE_` prefix; env file `.env`. Carries `database_url` (default points at the dev Postgres agreed above) and `log_level`. Does **not** carry auth settings (sign-in is out of scope). Shared with `impl-database`; whoever writes it first, the other reviews it for their own settings. |
| `<pkg>/logging_config.py` | `configure_logging()`. Called only from `main.py`. Leaf; installs no handler from outside `main.py`. |

### `services/`

| File | What it does |
|------|-------------|
| `<pkg>/services/__init__.py` | Package declaration. |
| `<pkg>/services/errors.py` | `ServiceError` hierarchy: `NotFound`, `Invalid`, `Conflict`, `Malformed`, `Unauthenticated`, `Forbidden`. No I/O, no imports from other layers. |

### `api/` layer

| File | What it does |
|------|-------------|
| `<pkg>/api/__init__.py` | Package declaration. |
| `<pkg>/api/errors.py` | One error envelope. Defines `ErrorCode` (closed `Literal`), `ErrorBody`, `ErrorResponse`, `FieldError`, `RESPONSES`. `install(app)` registers handlers for `ServiceError`, `RequestValidationError`, `StarletteHTTPException`, and bare `Exception`. Maps service errors to status codes and codes; never re-raises after logging the 500 (matches reference reasoning). Both `ErrorBody` and `FieldError` are Pydantic `BaseModel` subclasses — **this is load-bearing**: FastAPI emits `BaseModel` subclasses as named `components.schemas` entries, and `impl-frontend`'s `web/src/api/errors.ts` imports `components["schemas"]["ErrorBody"]` and `components["schemas"]["FieldError"]` by name. Replacing either with a `TypedDict` or `dict` silently breaks the frontend client. |
| `<pkg>/api/request_id.py` | `RequestIdMiddleware` (pure ASGI). `install(app)` wraps `app.openapi()` to inject `X-Request-ID` into `components.headers` and reference it from every response. `get_request_id()` for the 500 handler. |
| `<pkg>/api/deps.py` | `SessionDep = Annotated[Session, Depends(get_session)]`. Imports `get_session` from `constellate.db` — impl-database's file. **Cannot be finalised until impl-database ships `db.py`.** |
| `<pkg>/api/routers/__init__.py` | Package declaration. |
| `<pkg>/api/routers/health.py` | `GET /health` (no DB, returns `{"status": "ok"}`). `GET /health/ready` (runs `select 1` through `SessionDep`, returns `{"status": "ready"}`). The `select 1` is the one place outside `repos/` that runs SQL, sanctioned explicitly in `check_layering.py`'s constant (ported from the sibling). |

### Scripts

| File | What it does |
|------|-------------|
| `api/scripts/export_openapi.py` | Port of the reference. Sets `CONSTELLATE_DATABASE_URL=sqlite://` before importing the app. Checks the import against the expected package path so a wrong `PYTHONPATH` is caught rather than silently exporting the wrong tree. `--check` mode for CI. |

### Tests

| File | What it does |
|------|-------------|
| `api/tests/__init__.py` | Empty, makes `tests/` a package for pytest discovery. |
| `api/tests/conftest.py` | Partial port of the reference. Dual-backend: `TEST_DATABASE_URL` env var (`CONSTELLATE_TEST_DATABASE_URL`), SQLite in-memory default. Per-session Postgres provisioning with a `_test`-suffixed name, dropped in teardown. **Split with impl-database**: database lays the engine / session_factory / session_override / per-run-provisioning fixtures (built from `models/`); backend adds the app-dependent `client` and `anon_client` fixtures. No auth fixtures (sign-in out of scope). Sets `CONSTELLATE_SESSION_COOKIE_SECURE=false` for the test client. |
| `api/tests/test_health.py` | `test_health_returns_ok` — `GET /health` → 200, `{"status": "ok"}`. `test_ready_returns_ready` — `GET /health/ready` → 200, `{"status": "ready"}`. Uses `client` fixture (no auth on health). |

### Contract

| File | What it does |
|------|-------------|
| `api/openapi.json` | Generated by `python scripts/export_openapi.py` after the venv exists. Contains only the health endpoints and the error envelope schemas. `ErrorBody` and `FieldError` appear as named `components.schemas` entries (FastAPI's default for Pydantic `BaseModel` subclasses). Committed in the same step as the code. Not breaking (no prior contract). |

---

## Hand-off: `ErrorBody` and `FieldError` as named contract components

`impl-frontend`'s `web/src/api/errors.ts` imports these two schemas by name from the
contract:

```ts
components["schemas"]["ErrorBody"]
components["schemas"]["FieldError"]
```

FastAPI emits a Pydantic `BaseModel` subclass as a named entry in `components.schemas` by
default. Both `ErrorBody` and `FieldError` in `api/errors.py` are defined as `BaseModel`
subclasses; this is what causes FastAPI to name them in the contract. The constraint this
imposes on my lane: do not replace either with a `TypedDict`, a plain `dict`, or an inline
schema annotation. If either type changes to something that FastAPI inlines rather than
names, the generated contract silently omits the component and the frontend client breaks
at generation time. Verify after generating `api/openapi.json`:

```sh
python -c "
import json, pathlib
spec = json.loads(pathlib.Path('openapi.json').read_text())
schemas = spec.get('components', {}).get('schemas', {})
assert 'ErrorBody' in schemas, 'ErrorBody missing from components.schemas'
assert 'FieldError' in schemas, 'FieldError missing from components.schemas'
print('ErrorBody and FieldError present in components.schemas')
"
```

---

## What I will not do

- Any endpoint beyond `/health` and `/health/ready`.
- Any table, column, or migration — `impl-database` owns `models/`, `repos/`, `db.py`,
  `alembic/`.
- Sign-in, session cookies, auth dependencies — out of scope for this PR.
- `poll.py` — arrives with the poller (per decision 4; director's recommendation is to defer).
- `domain/` and `sources/` stub packages — director's recommendation is to defer; follows
  decision 4 outcome.
- `repos/__init__.py` — impl-database's, not mine; follows decision 4 outcome.
- `api/src/constellate/api/cursor.py` or pagination schemas — no list endpoints yet.
- `infra/`, `compose.yaml` — out of scope for my lane.
- `web/` — owned by `impl-frontend`; runs in its own worktree and consumes `api/openapi.json`
  generated in this same PR.
- `pyproject.toml` — impl-database writes it; I list my dependencies below.

**Dependencies I need in `pyproject.toml`** (impl-database creates the file, adds these):

```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.10",
    "pydantic-settings>=2.6",
]
[project.optional-dependencies]
dev = ["pytest>=8.3", "httpx>=0.28", "ruff>=0.8"]
```

---

## What the session owns (not my files, but I specify what they need)

The brief lists items 3, 4, and 6 as "no specialist owns" work; this is my read of what each
needs from my lane.

**Item 3 — `scripts/check_layering.py` port.** Rename `PACKAGE` from `bgtracker` to
`constellate`, update `DEFAULT_ROOT` to point at `api/src/constellate`, update
`SANCTIONED_SKIPS` to match Constellate's sanctioned router skips (none at scaffold, so an
empty dict). Add the `sources/` rule: a module whose key starts with `sources/` must import
only `domain/`, leaves, and nothing else; and no module outside `sources/` may import a
`sources/` module. Write two tests in `scripts/tests/` that fail against a port that only
changes the constants: one with a fake adapter that imports `repos/`, one with a fake service
that imports an adapter (the brief's requirement, confirmed by `pr-tech-review` 2026-09-23).
The `select 1` sanction entry must be updated to reference
`api/src/constellate/CLAUDE.md` (not the sibling's path).

**Item 4 — `scripts/gates.py` additions.** The scaffold's `gates.py` has no `VENV`, no
`_venv_tool`, and an empty `PROBES`. The session needs to add:

- `import os` (for `os.name == "nt"` in the venv path)
- `VENV = ROOT / "api" / ".venv" / ("Scripts" if os.name == "nt" else "bin")`
- `_venv_tool(name)` helper
- `_venv(*args)` helper that uses `_venv_tool("python")`
- `PROBES = {"ruff": ..., "the api venv": ..., "web/node_modules": ..., "docker": ...}`
  (reference spellings; `docker` probe can be deferred until `infra` area is added)
- `Area.ci_only: str = ""` field (the `Area` dataclass lacks it; needed for the Alembic note)
- `api` area with paths `["api/**"]`, checks: lint (`ruff check .`, quick, needs ruff),
  formatting (`ruff format --check .`, quick, needs ruff), tests (`pytest -q`, needs api
  venv), OpenAPI contract (`python scripts/export_openapi.py --check`, needs api venv).
  `ci_only = "the two Alembic checks (CI-only — need a live database)"`.
- `web` area with paths `["web/**", "api/openapi.json"]`; and a stub workflow so the
  `test_every_workflow_is_claimed_by_an_area` test passes. `impl-frontend` provides the
  real web checks; the area and stub workflow arrive together.
- `infra` area with paths `["infra/**", "compose.yaml", ".github/workflows/**"]`, checks:
  stack script tests (quick), Caddyfile validate (needs docker, not quick).
- Add layering check to the `record` area: `Check("the layering",
  _py("scripts/check_layering.py"), quick=True, paths=["api/**",
  "scripts/check_layering.py"])`.
- Corresponding workflow files: `api.yml`, `web.yml` (stub), `infra.yml`.
  `record.yml` gains the layering check step.

**Item 6 — `CLAUDE.md` files.** My lane's per-directory files are:

- `api/CLAUDE.md`: commands (`pytest -q`, `ruff check .`, `ruff format .`,
  `python scripts/export_openapi.py`, `alembic upgrade head`); conventions (type hints
  everywhere, Pydantic v2 at boundaries, sync not async, raise service errors never
  HTTPException, bound every input); adding a dependency rule.
- `api/src/constellate/CLAUDE.md`: the layer diagram; the one-direction rule; the
  `sources/` rule (reached only through an interface `services/` declares; satisfies it
  structurally; imports only `domain/` and leaves; nothing imports it); leaf/entry-point
  rules; `select 1` sanction for `health/ready`; loggers convention; non-negotiables
  (these are minimal at scaffold; they grow when the domain model arrives).
- `api/tests/CLAUDE.md`: dual-backend setup; no-commit fixture convention; test naming
  rules.

The `api/alembic/CLAUDE.md` is impl-database's to write.

---

## Sequencing and parallelism

Two specialist runs cannot share one worktree simultaneously. The natural order:

```
Session:       docs/03 conventions section; CLAUDE.md files; check_layering.py port;
               gates.py + workflows.   (can overlap with impl-frontend for different files,
               but the api/ worktree is shared — sequence strictly with database/backend)

impl-database: pyproject.toml (all deps); venv; db.py; models/base.py + __init__.py;
               alembic/ setup; empty first migration.

impl-backend:  <pkg>/__init__.py, main.py, config.py, logging_config.py
               <pkg>/services/__init__.py, services/errors.py
               <pkg>/api/__init__.py, api/errors.py, api/request_id.py
               api/deps.py  <- needs db.py from impl-database
               api/routers/__init__.py, api/routers/health.py
               api/scripts/export_openapi.py
               api/tests/__init__.py, api/tests/conftest.py (app fixtures)  <- needs models.Base
               api/tests/test_health.py
               api/openapi.json  <- generated last

impl-frontend: web/ in its own worktree, fully parallel; web/src/api/schema.d.ts and
               check:api-types wait on api/openapi.json being committed.

Session:       clear "arrives with scaffold PR" markers in overlay, docs/03, root CLAUDE.md.
```

Files that do not depend on `db.py` or `models.Base` — `services/errors.py`, `api/errors.py`,
`api/request_id.py`, `config.py`, `logging_config.py` — can be written before impl-database
finishes, but since both use one worktree they are sequenced anyway. The hard constraint:
`api/deps.py`, the `client`/`anon_client` fixtures in `conftest.py`, and `test_health.py`
cannot be finalised until impl-database's files are present.

`api/openapi.json` is the last file I write: it requires a working venv with the whole
package importable (no missing imports from the database layer).

---

## Premises that did not survive reading the code

1. **`domain/__init__.py` as a stub is dead code.** `check_layering.py` works by scanning
   what is in the package; an absent `domain/` simply produces no violations to report. The
   two sources/ tests use synthetic packages, not the real tree. No domain module is needed
   at scaffold time — it arrives with Q-C's answer.

2. **`api/deps.py` has a hard import from `db.py` (impl-database's).** The reference's
   `deps.py` imports `get_session` from `db.py` at the top level. This is not optional or
   lazy: Python fails at import if `db.py` does not exist. My `deps.py` cannot be written
   until impl-database's `db.py` is in the worktree. The sequencing above is a hard
   constraint, not a recommendation.

3. **`config.py` is needed by both layers.** The reference's `db.py` imports `settings`
   from `config.py` for the database URL. My `main.py` will need it for `log_level` and
   potentially `debug`. Whoever writes `config.py` first owns it; the other layer adds its
   settings in the same commit or a subsequent one before tests run.

4. **The `Area` dataclass in `scripts/gates.py` lacks `ci_only`**, which the `api` area
   needs to document the Alembic checks. The session must add the field before adding the
   area, or `test_gates.py` will reject an area with an unknown keyword argument.

5. **`pyproject.toml` does not yet exist in the scaffold worktree.** It must be the first
   file created (by impl-database) before either layer can install its packages or run any
   check.

---

## Verification

Run from `api/` with the venv (`api/.venv`) active; all checks must pass before the
contract is generated.

```sh
# Lint and format (quick; same as pre-commit hook)
ruff check . && ruff format --check .

# Tests (SQLite in memory; no Docker needed)
python -m pytest -q

# Contract (must match what is committed)
python scripts/export_openapi.py --check

# Verify ErrorBody and FieldError are named in components.schemas
python -c "
import json, pathlib
spec = json.loads(pathlib.Path('openapi.json').read_text())
schemas = spec.get('components', {}).get('schemas', {})
assert 'ErrorBody' in schemas
assert 'FieldError' in schemas
print('components.schemas check passed')
"

# From the repo root:
python scripts/check_layering.py          # no violations
python -m unittest discover scripts/tests # test_gates.py and layering tests green
```

The two Alembic checks — `alembic revision --autogenerate` producing an empty diff, and
`upgrade head; downgrade base; upgrade head` — are CI-only; they need a live Postgres
database. The scaffold PR has no tables, so the empty-diff check is trivially satisfied, but
it still needs the `api` area's `ci_only` note to explain why it does not run locally.

---

## Contract impact

`api/openapi.json` is created for the first time. The health endpoints add two paths
(`/health`, `/health/ready`), the error schemas add two named `components.schemas` entries
(`ErrorBody` and `FieldError`), and `X-Request-ID` appears on every response. Entirely
additive: there was no prior contract.

`impl-frontend` consumes `api/openapi.json` in this same PR: `npm run generate:api-types`
produces `web/src/api/schema.d.ts`, and `check:api-types` diffs it against the committed
contract. The frontend's `web/src/api/errors.ts` imports `ErrorBody` and `FieldError` by
name from `components.schemas`; the hand-off pinned above is what ensures this works.
