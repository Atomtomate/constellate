Reviewed at 8c7f64153fa7

**Verdict:** Needs fixes before merge, none of them a blocker. One crash on a realistic database
URL (`api/alembic/env.py`). Two guards have holes: the 405 handler and the web layer test. The
revision template fails its own gates. The two invented rules with the most riding on them, log
redaction and UUIDv7 order, have no test.

### 1. `env.py` passes the database URL through ConfigParser unescaped
- **`api/alembic/env.py:16`**: `config.set_main_option("sqlalchemy.url", settings.database_url)`
  sends the URL through ConfigParser's `%` interpolation, so a URL with a percent-encoded
  character is rejected.
- **Failure:** a rig password with `@`, `/` or `#` has to be percent-encoded in the URL. With
  `CONSTELLATE_DATABASE_URL=sqlite:///C:/wt/p%40x.db`, `alembic upgrade head` dies before
  connecting: `ValueError: invalid interpolation syntax in '<the whole URL>'`. No migration can
  run, and the message prints the URL, password included, to the terminal or the CI log.
  Reproduced in the worktree's venv.
- **Confidence:** certain.
- **Fix:** take the URL out of the ini path entirely. In `run_migrations_online`, build the
  engine with `create_engine(settings.database_url, poolclass=pool.NullPool)` and drop the
  `set_main_option` line; offline mode already reads `settings` directly. Then add a test that
  runs `alembic.command.upgrade` against a SQLite file URL containing `%40`.

### 2. No test covers the log redaction or the request id on log lines
- **`api/src/constellate/logging_config.py:41`**: `_exc_only_lines`, `ConstellateFormatter` and
  `RequestIdFilter` hold the project's rules on what a log line may carry. No test under
  `api/tests/` reads a log line.
- **Failure:** replace `_exc_only_lines`'s body with `traceback.format_exception_only(...)`, or
  take the filter off the handler, and all 21 api tests still pass. Meanwhile a
  `UniqueViolation`'s `DETAIL: Key (...)=(<value>)` and a `ValidationError`'s rejected input
  reach the log, and `docs/03`'s "the same id on every log line the request writes" stops being
  true.
- **Confidence:** certain about the gap; probed, the code is right (id present, input absent).
- **Fix:** three cases that format records with `ConstellateFormatter` itself, not caplog's
  formatter. An exception whose `.orig` has `sqlstate` renders `SQLSTATE`, not its message; a
  pydantic error's input string is absent; a line logged during a request that 500s carries the
  response's `X-Request-ID`.

### 3. The HTTPException handler drops the exception's own headers
- **`api/src/constellate/api/errors.py:167`**: `_http_error` sends only
  `_CHALLENGE.get(status)` as headers and throws away `exc.headers`.
- **Failure:** `POST /api/health` answers 405 with no `Allow` header, which RFC 9110 §15.5.6
  requires on a 405. Starlette raises it with `Allow: GET`, and a default FastAPI app sends that
  header; both were probed. A dependency that raises with `Retry-After` or a specific
  `WWW-Authenticate` loses that header the same way.
- **Confidence:** certain.
- **Fix:** `headers={**_CHALLENGE.get(exc.status_code, {}), **(exc.headers or {})}`, plus a
  case in `test_health.py` asserting that `POST /health` answers 405 with `allow: GET`.

### 4. The web layer test's rule 1 misses an import written with its extension
- **`web/src/layering.test.ts:77`**: the pattern `/from\s+['"][^'"]*api\/client['"]/` expects
  the quote right after `client`. Rule 1 is the only guard on `api/client`, because rule 3's
  table leaves it out on purpose.
- **Failure:** a `src/routes/Timeline.tsx` with `import { api } from "../api/client.ts";` passes
  `npm test`, typechecks (`allowImportingTsExtensions` is on) and builds. That breaches
  `web/CLAUDE.md`'s layer rule with the test green. The spelling is already in use:
  `src/api/errors.test.ts:2` imports `"./errors.ts"`. Probed with the regex copied verbatim.
- **Confidence:** certain.
- **Fix:** `api\/client(\.tsx?)?['"]`, plus a probe case for the `.ts` spelling beside rule 3's
  exemption cases.

### 5. The revision template produces files that fail the api gates
- **`api/alembic/script.py.mako:9`**: the template puts `from alembic import op` before
  `import sqlalchemy as sa`, writes ids with `repr()` (single quotes) and always imports both.
  Nothing formats the output, and `pyproject.toml` exempts `alembic/versions/**` from `D1` only.
- **Failure:** render the template and run ruff with `api/pyproject.toml`. A `create_table`
  revision gets `I001`, and `ruff format --check` wants to rewrite it. An empty data-migration
  revision gets `I001` plus two `F401`. So the first revision made the way
  `api/alembic/CLAUDE.md` describes fails the pre-commit hook and `api.yml`'s Lint step until
  it is fixed by hand. `0001_scaffold.py` already had its imports trimmed by hand.
- **Confidence:** certain. Rendered into the scratchpad and checked there.
- **Fix:** add a `[post_write_hooks]` entry to `alembic.ini` that runs `ruff check --fix` and
  `ruff format` on the new file, so a generated revision lands clean.

### 6. No test covers `uuid7`'s ordering guarantee
- **`api/src/constellate/ids.py:35`**: the module promises ids that sort in mint order within a
  millisecond, across a counter overflow and across a backwards clock step. Nothing under
  `api/tests/` imports it.
- **Failure:** a regression such as `if now_ms >= _last_ms:` reseeds the counter inside the
  same millisecond. Two ids minted in that millisecond then sort at random, which is the "newest
  first is wrong" case its docstring names, and every test stays green. The current code is
  right: 200,000 ids minted in a tight loop sorted strictly, and with the clock 5 s behind the
  ids still ascended.
- **Confidence:** certain about the gap.
- **Fix:** patch `time.time_ns` to a constant and assert that 5,000 ids ascend strictly, which
  crosses the 4,096 overflow. Then step the clock backwards and assert the next id is greater.

**What carried it:** the definition's "where you can cheaply check by running … do". Running
`alembic upgrade head` with a `%40` URL in the worktree's venv turned a suspected interpolation
problem into a reproduced crash that prints the password.
