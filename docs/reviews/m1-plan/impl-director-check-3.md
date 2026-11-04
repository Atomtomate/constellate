# impl-director plan check — M1, round 3 (the re-cut)

*2026-11-04. The owner has answered every decision the M1 plan put to them, and the record step
(PR #27, merged as `50c96bc`) wrote the answers into the files that own them: `docs/02` §1/§7/§8
(key type, null item, `event.service`, `owner_id`, the import set), ADR-0003's 2026-11-03 revision,
new ADR-0004 (sign-in), ADR-0002's `CatalogueAdapter` note, and `docs/08` Q-E's store half. Two of
the plan's leanings were reversed: sign-in (decision 2) and the owner column (decision 7). This
round re-cuts what those two reverse and only that; every other lane stands as `impl-director.md`
cut it. The amendments are marked `[C3]` there. No reviewer was run (a plan, not code).*

## What each reversed answer changed

- **Decision 2 — sign-in (ADR-0004, stored revocable sessions, over the stateless-cookie leaning).**
  The session is now a row in an `auth_session` table holding a hash of an opaque cookie token, not
  an HMAC-signed stateless cookie. Login creates a row; `require_session` looks it up; logout
  deletes it; revoke-all deletes the rows. The table is a separate `0003_auth_session` migration
  plus repo functions, a small `impl-database` task briefed with Lane 3, gated on Lane 1's 0002 by
  the migration chain - so Lane 3's backend half no longer runs fully parallel to Lane 1. The wire
  contract is unchanged (`/auth/login`, `/auth/logout`, `/me`, a scheme, 401s, no new `ErrorCode`).
- **Decision 7 — the owner column (owner chose "add it now", over the no-column leaning).**
  `owner_id` is on the log tables from the first migration. Lane 1 grows this column and an index;
  the ingestion repos that create an owned row take an `owner_id` argument. No contract change
  (`owner_id` is internal, never on a response).

Decision 8 (null item + `event.service`) and decisions 1, 3, 4-6, 9 landed **as their leanings**,
already in the record; they need no re-cut.

## Issue #28 — settled (director's call)

The owner's "the log tables" and "the one owner" are made; the three sub-points were handed to the
re-cut, and I settle them as #28's leaning has them - none reverses the owner's choice, none is
expensive to reverse before any data, and the issue delegates them:

1. **Which tables.** `owner_id` on the owner's-own cluster - `event`, `observation`, `ingest_run`,
   `source` - and **not** on the world/catalogue tables (`item`, `item_ref`, `creator`,
   `creator_ref`, `item_creator`, `catalogue_cache`), which name shared facts, not the owner's
   activity.
2. **What it holds.** One configured owner UUID, read from config at creation; no users table
   (`docs/00`: "No accounts beyond that").
3. **Uniqueness.** Unchanged - `observation.record_key`, `item_ref (namespace, value)` and
   `source.key` stay global, so a second user's identical-looking record would collide. The owner's
   "buys nothing until a second user exists" accepts this; it is stated, not papered over.

The session writes this into `docs/02` §8 (Open -> Answered), #28's done-when, before Lane 1 codes.

## Issue #20 — the two re-cut questions

1. **Does M1 build list/revoke? Answered: a command, not endpoints or a screen** (the owner's
   leaning). `python -m constellate.sessions` lists and revokes (by id, and all). It keeps the
   contract additive-minimal and Lane 7 as cut; management endpoints and a sessions screen are M2+
   polish. An entry point, so `impl-backend`'s, no contract impact. The listing/revoke repo
   functions therefore belong in the `0003` task.
2. **How a non-browser client presents a credential? Deferred to Q-F / the extension** (the owner's
   leaning). The only M1 client is the same-origin browser, so no token/header path is built. The
   one constraint on Lane 3 so a fail-open is not foreclosed by accident: the session is found by a
   token and the cookie is only the browser's carrier - keep the lookup transport-agnostic, so a
   later header-borne token is additive and needs no migration.

## Lane order and gates, as they now stand

Lane 1's gates all resolve (decision 1 UUIDv7, decision 8 null item + `event.service`, decision 7
`owner_id`/#28), recorded by PR #27 and settled here, so **Lane 1 is unblocked** once the session
writes #28's table list into `docs/02` §8. **Lane 2a** (`domain/`, un-gated) and the
**password-hashing helper** of Lane 3 draft beside Lane 1. **Lane 2b** waits on Lane 1.
**`0003_auth_session`** (small `impl-database` task) stacks on 0002; **Lane 3's** table-backed
backend half waits on `0003` -> `0002`, then its frontend half and the sessions command. Lanes 4,
5, 6, 7, 8, 9 are unchanged: 4 gates on 2b, 6 on 1+3, 5 trails 1+2b and closes when scheduled, 7's
W2 on 3 and W3 on 6+W2, 8 on 4c, 9 on 1.

## The two lane briefs the coordinator can hand now

A new worktree has no `api` venv: the specialist makes one first, from `api/`, with
`py -3.13 -m venv .venv` then `pip install -e ".[dev]"` with that interpreter (per `api/CLAUDE.md`),
before any `pytest`. The two lanes run in parallel, in separate worktrees, on disjoint files.

**Lane 2a (`impl-backend`, pure `domain/`, un-gated).** Build the ingestion seam's pure half with no
I/O, as `impl-director.md` Lane 2 and the backend plan's 2a cut it: `<pkg>/domain/vocab.py` (the
`StrEnum`s for basis, item kind, creator kind and role, with `docs/02` §7's CHECK values, and
`EntityId = uuid.UUID`), `draft.py` (`Ref`, `CreatorHint`, `ItemHint`, `Catalogue`, `DraftEvent`'s
nine `docs/02` §2 fields, `Batch`, with the validating `__post_init__`), `precedence.py` (`resolve`
in ADR-0003's orders, item rank export -> Google history -> extension -> poller -> name-only
Last.fm), `matching.py` (`MatchWindows`, `name_key`, `pair_in_order`, in-order never nearest), and
`<pkg>/services/sources.py`'s `SourceAdapter` protocol (`key`, `service`, `fetch(cursor) ->
Iterator[Batch]`, cursor-optional). The two reversed answers do **not** touch this lane:
`DraftEvent` gains no owner field (the service stamps `owner_id` from config in 2b), and sign-in is
elsewhere - so 2a stands exactly as cut. Tests: `test_domain_*.py` (every arrival order resolves the
same event; back-to-back plays pair k-th with k-th; a relinked URI pairs by name). Commands from
`api/`: `ruff check . && ruff format --check .`, `pytest -q`, `python ../scripts/check_layering.py`.
Waits on nothing; runs beside Lane 1.

**Lane 1 (`impl-database`, the schema).** Write the one core-log migration (`0002_core_log`,
`down_revision = "0001_scaffold"`) and its `models/` and `repos/`, exactly `docs/02` §7's ten tables
with the load-bearing shape `impl-director.md` Lane 1 and the database plan fix (nullable
`event.item_id`; immutable `event.service`; the two duration CHECKs; `observation.record_key` unique;
`item_ref` unique `(namespace, value)`; `creator_ref` PK `(namespace, value)`; `catalogue_cache`
keyed by `item_ref_id`; the timeline indexes; `lazy="raise"`). **New in this re-cut:** `owner_id`
(`uuid.UUID` NOT NULL, indexed) on `event`, `observation`, `ingest_run` and `source` only - not the
world/catalogue tables (#28) - set at creation from a configured owner UUID; `get_or_create_source`,
`start_run`, `create_event` and `add_observation` take an `owner_id` argument. Uniqueness stays
global. Build only the `repos/` Lane 2 steps 1-5 call (later lanes' queries are small tasks); the
name-ref lookup narrows by the resolved creator link, with `name_key(title)` picked in `domain/`,
no casefold `=` in SQL (C2). The `auth_session` table is **not** here (separate `0003`). The session
writes #28's table list into `docs/02` §8 and folds #17 (retire the §7 sketch) in this PR. Tests:
`test_models.py` (every CHECK/unique/FK, and `owner_id` NOT NULL on the four, absent on the rest),
`test_repos_*.py`, `test_migrations.py` (`NO_ROWS["0002_core_log"]`). Commands from `api/`:
`pytest -q`, `ruff check . && ruff format --check .`, `python ../scripts/check_layering.py`; by hand
on the dev Postgres, `alembic upgrade head && alembic downgrade base && alembic upgrade head` and an
empty `--autogenerate`. Gated on nothing now outstanding (decision 1 is recorded UUIDv7); needs the
dev Postgres up for the migration hand-run.
