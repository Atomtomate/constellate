Reviewed at d1f7201cd1eb

**Verdict:** The package's imports point the way `docs/03-architecture.md` draws them, and
`python scripts/check_layering.py` runs clean (21 modules; the two sanctioned `select 1` lines).
Two placements are unsettled: a module that only the entry points import, where the check and
`docs/03` disagree, and the contract's `/api` base, which the exporter writes instead of the app.

### 1. The layering check and `docs/03` disagree about a module only the entry points import

- **file:line** — `api/src/constellate/logging_config.py:14`, imported by `main.py:13` and
  `poll.py:16`: one of the two rules that place it is wrong, and the check reports it clean.
- **The crossing** — `from constellate.api.request_id import get_request_id`: the log filter
  gets the request id from the HTTP middleware's module. So `python -m constellate.poll` loads
  `constellate.api.request_id`, and FastAPI and Starlette with it, to write one log line (its
  `sys.modules` after import, in this worktree's venv).
- **The rule** — `docs/03-architecture.md:98`: "Outside the layers, a module is a leaf or an
  entry point … A module nothing reaches is an entry point … Nothing imports an entry point."
  By that rule, `logging_config.py` is either a leaf that imports `api/` or an entry point that
  something imports. `scripts/check_layering.py:253` ("a module only `poll.py` imports … stands
  with the entry points"), its case at `scripts/tests/test_check_layering.py:491` and the new
  `api/src/constellate/CLAUDE.md:18` add a third kind that may import anything and is checked
  for nothing. The owner decides which is wrong; `docs/03` is the page ADR-0002 decided.
- **The fix** — if `docs/03` holds: `leaf_importers` also seeds from the entry points, the case
  at `:491` flips, and the request id's contextvar and getter move to a new leaf module (e.g.
  `request_context.py`) that the middleware sets and the filter reads, which adds one module.
  If the check holds: `docs/03:98` names the third kind and its rule, and `:491` pins it.

### 2. The contract's base path is written by the exporter, not by the app that owns it

- **file:line** — `api/scripts/export_openapi.py:49` writes the committed contract's `servers`
  from a literal `"/api"`, although the prefix belongs to `main.py:24`'s `root_path`.
- **The crossing** — `spec.setdefault("servers", [{"url": "/api"}])`: `app.openapi()` carries
  no `servers`. The served `/api/openapi.json` takes its entry from the request scope's
  `root_path`; the committed file takes it from this copy. One contract entry has two producers.
- **The rule** — no document states it. On its own terms: every other convention writes its
  contract entry from inside the app (`api/request_id.py:7`, "the same way `errors.py` owns its
  own contract entries"). This one is written from a copy, by a tool outside the package. If
  `root_path` and its test (`api/tests/test_app_config.py:22`) change, the committed contract
  still says `/api`, and both `--check` and `test_app_config.py:30` stay green: the
  served/committed split that `docs/03`'s "One origin" exists to close.
- **The fix** — pass `servers=[{"url": ...}]` to `FastAPI(...)` in `main.py` from the constant
  `root_path` uses, and drop the exporter's line; on FastAPI 0.142.2 `app.openapi()` then carries
  it and the served spec does not duplicate it. A test asserts
  `app.openapi()["servers"] == [{"url": app.root_path}]`. No code is added.

**Follow-ups**

- `web/CLAUDE.md`'s layer rule does not place the top-level files of `web/src/`: `App.tsx:26`
  defines the index route's screen and calls `hooks/` (`App.tsx:3`) where `layering.test.ts:92`'s
  per-section rules do not reach. A row for the shell would settle whether M1's screens go there.

**What carried it**

The definition's escalation rule for the check disagreeing with the written standard, applied
when the check's clean pass over `logging_config.py:14` was read against `docs/03:98`.
