# impl-database plan — M1 Lane 1 (the schema) and the repo tasks later lanes will brief

*Authored at the plan-before-code round for M1, against `impl-director.md`. No code. Planned under
the leanings (UUIDv7 keys, the sibling's cookie scheme, `docs/02` §8 as written); "If the owner
decides otherwise" says what each changes. The worktree has no `api/.venv`, so I probed the
mechanisms in a scratch venv (SQLAlchemy 2.1.4, SQLite 3.50): a `TypeDecorator` over
`DateTime(timezone=True)` returns aware UTC on SQLite; a JSON/JSONB variant creates on both;
`FILTER (WHERE)` and row-value comparison run on SQLite; Alembic applies the metadata's
`naming_convention` in `op.create_table` and compares types by compiled DDL. Postgres: not probed.*

**Position.** Cut as the director has it, plus the changes under "Where the cut is wrong".

## Lane 1 — the schema (gate: decision 1)

One PR, two commit groups so `git log -p` reads in order: models + migration + their tests, then
the repos + theirs. `<pkg>` is `api/src/constellate/`.

**Files.** New: `<pkg>/models/types.py`, `ingest.py`, `item.py`, `creator.py`, `event.py`,
`cache.py`; `api/alembic/versions/0002_core_log.py` (`down_revision = "0001_scaffold"`);
`<pkg>/repos/sources.py`, `items.py`, `events.py`, `observations.py`, `catalogue.py`;
`api/tests/factories.py`, `test_models.py`, `test_types.py`, `test_repos_*.py`. Edited:
`models/base.py`; `models/__init__.py` and `repos/__init__.py` ("nothing exists yet" docstrings);
`api/tests/conftest.py` (the model-built half); `api/tests/test_migrations.py`.

**The schema** is `docs/02` §7 as model classes: `Owned` (UUIDv7 `id`, `created_at`) on every
single-key table, `uuid.UUID` for every FK. Changes to §7 are marked (Δ).
- `types.py`: `UtcDateTime` (binds aware values only, returns aware UTC: SQLite drops the offset,
  so an aware-minus-naive `TypeError` would show only under the hook's engine), `Json` (the
  JSON/JSONB variant), `in_list()` for CHECKs. `Owned.created_at` uses it. `Base.metadata` gets a
  `naming_convention` and every CHECK a name, so a later revision can widen one (a new item kind).
- `Source`: `key` unique, `service`, `cursor` Json|None. Rows are created on first use
  (`get_or_create_source`), not seeded, so the migration touches no rows and `NO_ROWS` is honest.
- `IngestRun`: `source_id`, `started_at`, `finished_at`, `outcome` (CHECK ok|failed|null),
  `file_sha256`, `counts` Json|None, `error`. Indexes `(source_id, started_at)` and
  `(source_id, file_sha256)`, the latter not unique: a failed run's hash must not block a retry.
- `Item`: `service`, `kind` (CHECK track|episode|chapter|video), `title`, `detail` Json NOT NULL,
  ORM `default=dict` and no server default (Δ: Postgres reads `'{}'::jsonb` back and
  `compare_server_default=True` would report drift forever). `ItemRef`: `item_id`, `namespace`,
  `value`, unique `(namespace, value)`, index `item_id`.
- `Creator`: `service`, `kind` (artist|channel|show), `name`. `CreatorRef`: PK `(namespace,
  value)`, `creator_id`. `ItemCreator`: PK `(item_id, creator_id, role)`, `position`, index
  `creator_id` (the by-creator filter and total reach the link from that side).
- `Event`: Δ `service`, `item_id` nullable, `started_at`, `duration_ms`, `duration_basis` (CHECK the
  three values; CHECK `(basis = 'measured') = (duration_ms is not null)`). Indexes `(started_at,
  id)` (the timeline's keyset order), `(item_id, started_at)`, `(service, started_at, id)`.
- `Observation`: §7's columns, `record_key` unique, Δ the same two CHECKs (an adapter cannot hand
  the resolver a `measured` play without milliseconds). Indexes `event_id`, `ingest_run_id`,
  `item_ref_id`, `(source_id, started_at)` (coverage range, disconnect, candidate lookup).
- `CatalogueCache`: PK `item_ref_id`, `source_id`, `fetched_at`, `status` (CHECK found|not-found),
  `length_ms`, `payload` Json|None; index `fetched_at`.
- Delete rules: `ItemRef`, `CreatorRef`, `ItemCreator`, `CatalogueCache` CASCADE from their parent;
  every other FK RESTRICT, so an event cannot lose its observations, nor an observation its ref,
  source or run, except through a repo function that orders the deletes.
- Every relationship is `lazy="raise"`: a lazy load in a service is SQL run outside `repos/` that
  `check_layering.py` cannot see, so the repos' `selectinload`s are the only way to a related row.
- Vocabulary strings (bases, kinds, roles, statuses) are literals in `models/`; `domain/` does not
  exist yet. Lane 2 defines `StrEnum`s with the same values and a test pinning the two sets equal.

**Repo signatures** (in Lane 1's PR; each is named by a step of `docs/02` §2). `s` is the session,
first; the rest keyword-only unless an id; ids are `uuid.UUID`. Repos flush and never commit: the
caller commits where it completes (`src/constellate/CLAUDE.md`).

```text
sources.py  get_or_create_source(s, key, service) -> Source
            get_cursor(s, source) -> dict | None;  set_cursor(s, source, cursor)
            start_run(s, source, *, started_at, file_sha256=None) -> IngestRun
            finish_run(s, run, *, finished_at, outcome, counts, error=None)
            find_ok_run_by_hash(s, source_id, file_sha256) -> IngestRun | None   # before parsing
items.py    find_ref(s, namespace, value) -> ItemRef | None;   get_item(s, item_id) -> Item | None
            create_item(s, *, service, kind, title, detail) -> Item
            add_ref(s, item_id, namespace, value) -> ItemRef
            update_item(s, item, *, title, detail)        # the export's title replaces a stand-in's
            find_items_by_name(s, *, service, kind, title, creator_name) -> list[Item]  # casefold =
            find_creator_by_ref(s, namespace, value) -> Creator | None
            create_creator(s, *, service, kind, name, namespace, value) -> Creator
            link_creator(s, *, item_id, creator_id, role, position=0)            # idempotent
            prune_item(s, item_id) -> bool   # iff no event and no observation names its refs;
                                             # then its refs, links, cache, and linkless creators
events.py   lock_service(s, service)             # advisory xact lock per service; no-op on SQLite
            find_candidates_by_item(s, *, service, item_id, within, lacking) -> list[Event]
            find_candidates_by_name(s, *, service, title, creator_name, within, lacking) -> same
            create_event(s, *, service, item_id, started_at, duration_ms, duration_basis) -> Event
            set_event_columns(s, event, *, item_id, started_at, duration_ms, duration_basis)
            get_event(s, event_id) -> Event | None   # observations, their source and ref loaded
            delete_event_if_empty(s, event_id) -> bool
observations.py
            existing_record_keys(s, keys) -> set[str]                     # step 1, as a batch
            add_observation(s, *, event_id, source_id, ingest_run_id, record_key, item_ref_id,
                            started_at, duration_ms, duration_basis, raw) -> Observation
            delete_event_observations(s, event_id, *, source_ids) -> int   # the export re-sources
catalogue.py  CACHE_MAX_AGE = timedelta(days=30)                  # the read rule, in one place
            upsert_cache(s, *, item_ref_id, source_id, fetched_at, status, length_ms, payload)
            get_cache(s, item_ref_id, *, now) -> CatalogueCache | None      # over 30 days: None
```

`within` is `(lo, hi)`, `lacking` the source ids of the draft's own stream. An event is a candidate
when some observation of it starts inside `within` and none comes from a `lacking` source ("never
two observations from one stream on one event"). The per-pair windows stay in `domain/`, which
gets the events back ordered `(started_at, id)` for ADR-0003's in-order pairing and picks.
`find_items_by_name` is the name ref's "exactly one item with this title and album artist" test;
`prune_item` is how a stand-in left with nothing goes, after `delete_event_observations`.

**Small tasks the later lanes will brief** (my sketch; none is coded in Lane 1):
- Lane 2: `observed_range(s, source_id) -> (min, max) | None`, `count_unmatched_live(s, *,
  live_source_ids, export_source_id, within) -> int` (§4's "kept and counted in the ingest run").
- Lanes 4c/4d, disconnect or termination: `delete_source_observations(s, source_id) ->
  list[event_id]`, `delete_cache_of_source(s, source_id) -> int`; the service re-resolves the
  returned events (a domain rule, never SQL), then `prune_item`, in one transaction. Undoing an
  import is the same shape: `delete_run_observations`, then `delete_run`.
- Lane 5: `refs_needing_catalogue(s, *, namespace, now, refresh_after, limit) -> list[ItemRef]`,
  `delete_expired_cache(s, *, now) -> int`, `cache_rows_with_isrc(s, isrc, *, now)`, and for §3's
  merge `repoint_ref(s, ref, item_id)` and `events_of_item(s, item_id) -> list[Event]`.
- Lane 6: `list_timeline(s, *, now, after, limit, since, until, service, item_id, creator_id) ->
  list[TimelineRow]`: `after` is the decoded keyset `(started_at, id)`; a row holds event, item,
  credits, the longest fresh cached `length_ms` and `next_started_at` (next event of the same
  service), so `domain/` computes `min(length, gap)`; the service asks for `limit + 1`.
  `totals_by_period(s, *, now, period, tz, since, until, service)`, `totals_by_creator(...)`,
  `totals_by_item(..., kind, limit)` -> `TotalsRow(key, label, measured_ms, estimated_ms,
  upper_bound_ms, unknown_count, event_count)`; `source_status(s)`. A time counts once per linked
  creator, so rows by creator do not sum to the whole.

**Tests and fixtures.** `factories.py`: `make_source/run/item/event/observation(session, **over)`
with defaults, so a model change breaks one file (the overlay's construction rule); Lanes 2 and 6
import it. `conftest.py`: `PRAGMA foreign_keys=ON` on a SQLite `engine`, so RESTRICT and CASCADE
are tested on both engines, and a `postgres_only` skip. `test_models.py`: every CHECK, unique and
FK rule rejects its bad row. `test_repos_*.py`: each function, the candidates on a track played
twice back to back, `prune_item`'s refusals, `get_cache`'s 30 days. `test_migrations.py`:
`NO_ROWS["0002_core_log"]`, a SQLite `upgrade head` creating exactly `Base.metadata`'s tables, a
`downgrade base` leaving none. From `api/`: `pytest -q`; `ruff check . && ruff format --check .`;
`python ../scripts/check_layering.py`. By hand on Postgres: `pytest -q` with
`CONSTELLATE_TEST_DATABASE_URL`; `alembic upgrade head && alembic downgrade base && alembic upgrade
head`; `alembic revision --autogenerate` empty. **Needs** decision 1 (#10) and the dev Postgres up
for that hand-run, the one step I cannot take alone; nothing from another lane.

## Where the cut is wrong or underspecified

1. **The PR's scope contradicts itself.** Lane 1 lists the timeline, aggregates, disconnect delete
   and cache refresh, then says a later lane's queries are small tasks briefed by its need. I take
   the second: a query drafted now has no caller until its lane, and the gate shrinks to what
   Lane 2's steps 1–5 call.
2. **A null-item event has no service.** The timeline's service filter, per-service totals and the
   gap to "the next watch" (per service, or Spotify plays every few minutes cap a video's
   estimate) read the service through the item. Proposal: `event.service`, set at creation from
   the draft's source and never re-resolved, so ADR-0003's "no source on the event" stands. Without
   it each query joins observation to source. `docs/02` §1's Event table gains a row.
3. **The repo list missed four things:** the per-service lock is SQL (`pg_advisory_xact_lock`), so
   mine; re-sourcing (§4) deletes live observations; candidates must come back with all their
   observations, since a window belongs to a pair of streams, not an event; and the run row must be
   committed before the first batch, or a rolled-back batch takes the `failed` record with it.
4. **SQLite cannot test every total.** `totals_by_period` is `date_trunc(… at time zone :tz)`, so
   its test is Postgres-only (CI, or by hand) and the hook never sees it. Lane 6's "fixture-
   testable" holds for the rest. A SQLite emulation would be a second central query: not worth it.
5. **Sign-in may need a table.** "Lane 3 on decision 2 alone" holds for a stateless signed cookie;
   revocable stored sessions need `auth_session`, and Lane 3 then waits on my revision.
6. **Smaller.** Spotify cache rows must carry the `spotify-poller` source id (Lane 5) or the
   disconnect misses them. `creator.kind` has no audiobook author: 4a maps it to `show` or asks.
   A merged item's cached length is the longest across its refs. Rankings are top-N by `limit`, not
   a cursor (a keyset over a computed sum shifts as events arrive); Lane 6 should say so.
7. **Stale after this PR, the session's:** `alembic/CLAUDE.md` ("one empty revision"),
   `api/tests/CLAUDE.md` ("No Postgres-only migration cases"), `docs/02` §1 and §7 (#17).

## If the owner decides otherwise

- **Key type, bigint.** `Owned` loses `id`; each key is `BigInteger().with_variant(Integer,
  "sqlite")` with `Identity()` (SQLite autoincrements only an `INTEGER PRIMARY KEY`); FKs follow.
  `ids.py`, `test_ids.py` go; repo ids and the `(started_at, id)` cursor become `int`. Settle it
  first: after the migration it rewrites every FK.
- **Sign-in.** Signed cookie or proxy-side auth: nothing. Stored sessions: `0003_auth_session`
  (`token_hash` unique, `expires_at`) and three repo functions, a small task, not in 0002.
- **`docs/02` §8.** Import-everything, `ip_addr` stripped, one zone, a null-item event: no schema
  (`raw` is JSON; the zone is `totals_by_period`'s argument). A placeholder item per unidentifiable
  record makes `event.item_id` NOT NULL and drops `event.service`. Splitting YouTube Music by
  `header` is the one that adds a column totals read: a later revision, backfilled from `raw`, on
  `event` or `item` once 4b's Takeout shows which; `incognito_mode` likewise.

## Not in this plan

Atlas tables, owner column, search indexes, rollups, partitioning; the Spotify sign-in date column
(4d's); seed rows; `updated_at`, soft delete; `auth_session`; the enrichment job; any `domain/`,
`services/`, `api/` file, `config.py`'s zone setting (Lane 6's), `pyproject.toml`; the record edits.
