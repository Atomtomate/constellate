Reviewed at 98442d769fff

**Verdict:** No findings. The fold fixed both first-wave findings in the code, not just the
prose. `logging_config.py:15` now gets the request id from the new leaf `request_context.py`,
which imports nothing from the package, and `import constellate.poll` no longer loads FastAPI
or anything under `api/` (checked in `sys.modules`). `leaf_importers` now counts what the entry
points import as reached, as `docs/03:98` says, and its test at
`scripts/tests/test_check_layering.py:491` was flipped to match. `python scripts/check_layering.py`
is clean on 22 modules, and the check and the standard agree. `main.py:28` passes `servers` from
the constant `root_path` uses. `app.openapi()` and the served `/api/openapi.json` both carry
`[{"url": "/api"}]` once, and the exporter no longer writes it. The first wave's web follow-up
is settled: the screen is `routes/Health.tsx`, and `App.tsx` imports only `routes/`.

**Follow-ups**

- `web/src/layering.test.ts`: `web/CLAUDE.md`'s new shell rule (`main.tsx` and `App.tsx`
  import only `routes/`) is enforced only by review. Section is read as `rel(fp).split("/")[0]`,
  so a top-level file gets `MAY_NOT_IMPORT["App.tsx"]`, which is undefined, and is checked for
  nothing. A `MAY_NOT_IMPORT` row keyed on top-level files and forbidding `hooks/`, `api/` and
  `components/` would make this a test.

**What carried it**

Importing `constellate.poll` in `api/.venv` and listing `sys.modules`. This re-measured the
evidence the first wave's finding 1 rested on, instead of taking the commit message's word for it.
