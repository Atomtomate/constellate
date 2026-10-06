Reviewed at dd6ae24e3f66

**Verdict:** Needs fixes before merge, none of them a blocker. Two folds stop short of the
first-wave findings they answer: the log wiring and rule 1. Two fold changes each bring a new
defect: a layering false positive, and a hook type the alembic pin does not cover.

### 1. The request-id test builds its own handler, so the production wiring stays untested
- **`api/tests/test_logging.py:98`**: the test attaches a handler it builds itself, with
  `ConstellateFormatter` and `RequestIdFilter`. It never reads the handler `configure_logging()`
  installs (`api/src/constellate/logging_config.py:186-187`).
- **Failure:** delete `handler.addFilter(RequestIdFilter())` at `logging_config.py:187`, which is
  the regression the first wave named, and all 29 api tests pass while every production line
  carries `"request_id": null`. Delete `handler.setFormatter(formatter)` at `:186` instead and
  29 still pass, while the app writes plain-text lines with the stdlib traceback, a `DETAIL`
  value and a rejected input included. Both were probed in a copy of the branch.
- **Confidence:** certain.
- **Fix:** take the `constellate` logger's handler whose formatter is a `ConstellateFormatter`,
  `setStream(buf)` it and restore it in `finally`, and drop the hand-built one. Probed: green on
  the branch, red under each deletion.

### 2. Layer rule 1 still misses the `.js` spelling of `api/client`
- **`web/src/layering.test.ts:68`**: `api\/client(\.tsx?)?['"]` catches `.ts` and `.tsx`, but
  under `moduleResolution: "bundler"` TypeScript and Vite also resolve `../api/client.js` to
  `client.ts`.
- **Failure:** add a `src/routes/Probe.tsx` with `import { api } from "../api/client.js";` and
  route it from `App.tsx`. `tsc -p tsconfig.app.json` passes, `vitest run` passes (24 tests), and
  `vite build` bundles it against the same client. That is the first wave's finding 4 breach,
  with the test still green. Probed in a copy of the branch.
- **Confidence:** certain.
- **Fix:** strip any extension from the specifier and test what is left against
  `/\/api\/client$/`. Then add a `.js` probe case beside the `.ts` one.

### 3. The one-pass `leaf_importers` makes an entry point a leaf when its sibling is imported
- **`scripts/check_layering.py:272`**: the fold counts every import from every module, but
  places by top-level unit. An import between two files of one non-placed package therefore
  makes the whole package a leaf, the importing file included.
- **Failure:** take `importers/spotify.py`, which imports `constellate.importers.common` and
  `constellate.services.ingest`, plus `importers/common.py`, with nothing importing
  either. By `docs/03`, `spotify.py` is an entry point ("any importer run as a command may
  reach `services/`"). The check passes this at `d1f7201` and fails it at `dd6ae24` with
  `importers/spotify.py:2: imports services/, but importers/spotify.py imports it`, citing the
  module as its own reacher. `from .common import parse` fails the same way. Probed on a fixture.
- **Confidence:** certain.
- **Fix:** place non-placed modules per file, not per top-level directory, so `common.py` is
  the leaf and `spotify.py` stays an entry point. Add this fixture as a case in
  `scripts/tests/test_check_layering.py`.

### 4. The post-write hooks need Alembic 1.16.3, but the package admits 1.14
- **`api/alembic.ini:17`** and `:21`: Alembic first ships the `type = module` hook runner in
  1.16.3, and `api/pyproject.toml:10` requires only `alembic>=1.14`.
- **Failure:** under alembic 1.16.2, which the pin allows, `alembic revision -m x` writes the
  file and then stops with `FAILED: No formatter with name 'module' registered`, exiting
  non-zero. CI's drift step, run under `bash -e`, would then fail with no drift at all. pip
  resolves 1.20.0 today, so only an older environment hits it. Checked against the 1.14.1,
  1.15.x and 1.16.0–1.16.5 wheels, and reproduced with 1.16.2.
- **Confidence:** certain about the gap; the impact today is low.
- **Fix:** `"alembic>=1.16.3"` in `api/pyproject.toml`.

**Follow-ups**
- `scripts/review_briefs.py:45` tells every reviewer it is reviewing "the board-game-tracker
  repository". The template was ported from the sibling unchanged.

**What carried it**
- The definition's "where you can cheaply check by running … do", at the fold's own request-id
  test. Deleting the production filter in a copy of the branch and still seeing 29 tests green
  turned a test that only looked indirect into finding 1.
