Reviewed at 8c7f64153fa7

**Verdict:** Mostly yes. The scaffold lays out ADR-0002's stack as planned and writes its
conventions down before the first endpoint. But it brings in two sibling decisions this project
leaves open: how the owner signs in, and every table's key type. And some of its new lines go
untrue once the consolidation PR, which merges first, lands.

### 1. The sign-in scheme is settled, twice, and differently
- **What** — Every 401 carries a `Bearer` challenge and the test docs give `client` "a bearer
  token", while the web client sends "the session cookie" and names the sibling's
  `RequireSession`/`['me']` wiring. Sign-in is undecided.
- **Where** — `api/src/constellate/api/errors.py:108`, `docs/03-architecture.md:158`,
  `api/tests/CLAUDE.md:45`, `api/tests/conftest.py:162`, `web/src/api/client.ts:7-9`,
  `web/README.md:49`, `web/src/main.tsx:10-12`; against `docs/03-architecture.md:222` and
  `docs/adr/0002-the-stack.md:234-235` (the sibling's `ADR-0014` "not a precedent").
- **Why it matters** — This is `ADR-0014`'s cookie-plus-bearer arrangement arriving piecemeal and
  unasked. M1's sign-in decision would start from a convention row that already answers it.
- **Suggested resolution** — Code: drop `_CHALLENGE`, since no endpoint can return a 401 yet.
  Remove the scheme from the `docs/03` row and make the comments say "the credential M1 decides".
  Adopting `ADR-0014` is a decision for the record, not a port.

### 2. UUIDv7 keys for every future table, chosen silently
- **What** — `Owned` ("every table with a single-column key") fixes every key as an app-made
  UUIDv7 plus `created_at`. `ids.py` cites `docs/02` for an identity guarantee that is the
  sibling's invariant 5; Constellate's §7 sketch keys tables `bigint ... identity`, with types
  marked as placeholders.
- **Where** — `api/src/constellate/models/base.py:16-28`, `api/src/constellate/ids.py:7-8`;
  `docs/02-domain-model.md:515-590`; `docs/reviews/scaffold/impl-director.md:28-31`.
- **Why it matters** — Decision 4 asked the owner "port it now or later?", never "UUIDv7 or
  bigint". The key type is the hardest thing to change after the first migration, and that
  migration inherits whatever the base offers. `Owned` also reads as the open owner column.
- **Suggested resolution** — Ask the owner now. Record the answer in `docs/02` §7–§8 and fix
  `ids.py`'s citation. If the answer waits for the first table, `Owned` and `ids.py` wait too.

### 3. Lines that become untrue when the consolidation PR merges first
- **What** — New text says Q-C is "still open", tables come "once docs/02 is accepted", and
  adapters "once that question is settled". `claude/consolidate-m0` answers both Q-C and Q-D, and
  no rebase conflict will flag new files. Also, `CLAUDE.md:52-53` ("the first work it cuts") goes
  stale at this merge, and it is not the banner the PR body leaves for the consolidation PR.
- **Where** — `api/alembic/CLAUDE.md:15-17`, `api/src/constellate/models/__init__.py:3-4`,
  `repos/__init__.py:4-6`, `sources/__init__.py:8-9`, `services/sources.py:29-31`,
  `poll.py:8-10`, `api/src/constellate/CLAUDE.md:27-29,33`, `CLAUDE.md:52-53`.
- **Why it matters** — An agent starting cold reads that the model is unaccepted when `docs/08`
  says it is answered, and waits on a gate that is already open.
- **Suggested resolution** — Prose; no check can read a claim about a question's status. Name
  what each module waits on (the first migration, the first adapter) without any Q-C/Q-D status.
  Fix `CLAUDE.md:53` in whichever PR merges second.

### 4. The plan of record says the opposite of the owner's decision 4
- **What** — Code cites "decision N (impl-director.md)", but that file holds only the director's
  recommendations. It says to defer `domain/`, `sources/` and `poll.py` and lists them as Not in
  scope. The branch ships them on the owner's contrary answer.
- **Where** — `docs/reviews/scaffold/impl-director.md:22-32,117-124`, cited by
  `web/src/api/queryKeys.ts:6`, `web/CLAUDE.md:46`, `compose.yaml:8` and `docs/03:114-115`. The
  answer is only in main's `docs/handoffs/2026-10-06-coordinator-handoff.md`, with no sub-calls.
- **Why it matters** — Following the pointer leads to "defer". A reviewer holding "No dead code"
  (`CLAUDE.md:152`) sees unsanctioned empty packages, and the sanction sits in a handoff due to be
  folded.
- **Suggested resolution** — Prose, since the plan is the record: add "Owner's answers,
  2026-10-05" to `impl-director.md`, with decision 4's sub-calls (`Owned`, `ids.py`, `repos/`,
  `queryKeys.ts`), and strike the Not-in-scope line it reverses.

### 5. `docs/03`'s "leaf or entry point" no longer classifies every module
- **What** — `logging_config.py` is imported by the entry points and imports `api/request_id.py`,
  so it is neither of `docs/03`'s two kinds. The package `CLAUDE.md` and `check_layering.py` give
  it a third standing, "stands with them above `api/`", that `docs/03` never states; `docs/03`
  also says "Nothing imports an entry point".
- **Where** — `api/src/constellate/CLAUDE.md:17-19` and `scripts/check_layering.py`
  (`leaf_importers`), against `docs/03-architecture.md:98-102`.
- **Why it matters** — `docs/03` is "the standard a change is held to". Held to it alone, a module
  outside the layers imports `api/` with no rule that allows it.
- **Suggested resolution** — Prose: one clause in `docs/03-architecture.md:98-102` saying a
  module only entry points reach stands with them. The check already derives this.

### 6. Sentences that state the sibling's facts, or claim more than holds
- **What** — `db.py` argues for sync from "a few plays a week". `web/README.md` and
  `vite.config.ts` speak of Caddy "in every other environment" and "the rig's" uvicorn, and cite
  the root `CLAUDE.md` for a localhost note it lacks. The root Style says ruff enforces a
  docstring rule that "applies everywhere", but `web/` has no linter.
- **Where** — `api/src/constellate/db.py:3-4`, `web/README.md:22,27`, `web/vite.config.ts:11,13`
  and `CLAUDE.md:144-145`, against `docs/adr/0002-the-stack.md:33,159` and Q-E (no rig yet).
- **Why it matters** — `db.py`'s docstring records the reason for a design choice, and its premise
  is two orders of magnitude off. The Style line makes TypeScript docstrings look enforced.
- **Suggested resolution** — Reword each line to this project's facts. Either limit "enforced" to
  `api/` or file a TypeScript docstring lint and keep the claim only once it exists.

**Decisions**
- Envelope, closed `ErrorCode`, keyset cursors, UTC `Z`, `X-Request-ID`: recorded (`docs/03`).
- `/api` on one origin with `servers` declared: recorded (`docs/03`; the PR body flags it).
- Six generic codes before sign-in; 405 as `invalid_request`: recorded (`docs/03` table).
- `Bearer` challenge, web session cookie, bearer test client: silent (finding 1).
- UUIDv7 key and `created_at` on every single-key table: silent (finding 2).
- Every layer present now, including empty ones: recorded only in main's handoff (finding 4).
- Two health endpoints; `select 1` the one SQL outside `repos/`: recorded (`docs/03` Health).
- Dev Postgres shared with the sibling's server: recorded (decision 2, `infra/README.md`).
- Tests on SQLite by default, Postgres by env var, CI on both: recorded (`api/tests/CLAUDE.md`).
- `infra` area checks only `compose.yaml`: recorded (decision 5, `infra.yml`).
- Sync SQLAlchemy; commit where the write completes: recorded (`db.py`), with a wrong reason
  (finding 6).
- `SourceAdapter` as a member-less structural `Protocol`: recorded (`docs/03`, package
  `CLAUDE.md`).
- `logging_config.py`'s standing: recorded in the package `CLAUDE.md`, not `docs/03` (finding 5).
- Web libraries (openapi-fetch, TanStack Query, react-router, vitest): recorded (ADR-0002 "as is").
- Docstring rule exempts tests and generated revisions: recorded (root Style).

**Follow-ups**
- `docs/reviews/scaffold/impl-director.md:14` and its "GitHub Actions does not run" are stale now
  that the repository is public.
- PR #9 has no M1 milestone or project 7 item, though `claude/consolidate-m0` makes the scaffold
  M1's first bullet.

**What carried it**
- Reading the sibling's own `docs/02` (invariant 5) and its `docs/03` 401 row beside the ported
  files, when `ids.py` cited a guarantee Constellate's `docs/02` does not make.
