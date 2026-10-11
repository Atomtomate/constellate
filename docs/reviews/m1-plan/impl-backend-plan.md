# impl-backend plan — M1 lanes 2, 3, 4a, 6 and 5 (the tracker's API half)

*Plan-before-code round for M1, against `impl-director.md` and the scaffold at `a7cfbe4`. No code.
Decisions 1-3 are planned under the director's leanings; each lane says what moves if the owner
decides otherwise. `<pkg>` is `api/src/constellate/`. I did not read the sibling project (outside
this worktree): sign-in is built from the leaning's sentence, not ported from code I have seen.*

## Order, and where the cut does not survive my layer's detail
Build order inside `impl-backend`: **Lane 3, 2a, 2b, 6, 4a**, then 5. Lane 3 needs decision 2 only
and gives Lane 7 its sign-in contract early; 2a (`domain/`) needs nothing and runs beside Lane 1;
2b waits for Lane 1's repos. One branch and PR per lane.
1. **Lane 2 splits** (2a pure and un-gated, 2b the orchestration) **and gains re-sourcing**
   (`docs/02` §4): the cut names it only under 4c, but it is the one service's rule.
2. **The candidate lookup is a span read.** The cut asks `repos/` for events "sharing a ref, or
   title+artist"; that equality is what the first weeks of data tune (`docs/02` §2) and belongs in
   tested pure code. `repos/` returns one service's events in `[lo, hi]` with observations, item
   and creators loaded; `domain/matching.py` compares.
3. **Lane 1's repos list misses what ADR-0003 forces**: a per-service lock (SQL, so
   `impl-database`'s), deletes (observation, empty event, orphan item), a bulk known-key check,
   ok-run-by-SHA, live-only-events, latest-runs-per-source. The lists are in Lanes 2 and 6.
4. **`SourceAdapter` cannot be shaped by 4a**: a file has no cursor. The pollers (4c-4e) shape it,
   `docs/02` §2 describes all three, so I fix it now (`Batch`); they may add members.
5. **`/totals` becomes three paths** (rows differ by subject). Lane 6 gates on Lanes 1 + 3 as its
   header says, not on Lane 2 as "Order and parallelism" has it: its tests seed via `models/`.
6. **Decision 3's "split YouTube Music" and "filter private plays in totals" need a column**
   (`header`, `incognito_mode` are `raw`-only): Lane 1 need not wait, Lane 6 ships unfiltered.
7. **A generated file in `web/`**: `web.yml` fails an `openapi.json` change without a regenerated
   `schema.d.ts`, and the map gives `web/` to `impl-frontend`. I run `npm run generate:api-types`
   in Lanes 3 and 6 (no hand edit) unless the director prefers the session does.

## Lane 2 — The ingestion seam (2a un-gated; 2b gated on Lane 1)
**2a, pure, `<pkg>/domain/`:**
- `vocab.py`: `StrEnum`s `DurationBasis`, `ItemKind`, `CreatorKind`, `CreatorRole` with §7's check
  values, and `type EntityId = uuid.UUID`, decision 1's one line. A test pushes every member
  through the repos, so drift from Lane 1's literal checks fails a test, not a review.
- `draft.py`: frozen dataclasses `Ref(namespace, value)`, `CreatorHint(name, kind, role, position,
  ref)`, `ItemHint(service, kind, title, detail, creators)`, `Catalogue(length_ms, isrc, artists,
  payload)`, `DraftEvent` (§2's nine fields), `Batch(drafts, cursor=None, dropped={})`.
  `__post_init__` refuses a naive or non-UTC time, `measured` without `duration_ms` and the
  reverse, ms negative or over int32, a `record_key` over 512 chars, `raw` over 64 KB; titles and
  names are truncated (500, 300). An adapter counts a `ValueError` as `rejected`.
- `precedence.py`: `STREAM_OF` (Takeout and Portability are one stream) and `resolve(observations)
  -> Resolved(item_id, started_at, duration_ms, duration_basis)` in ADR-0003's orders. The ADR
  ranks the item only as "highest-ranked"; I read it as export, Google history, extension, poller,
  name-only Last.fm last (`docs/02` §3). **Director: confirm.**
- `matching.py`: `MatchWindows` (§2's windows and which end each pair compares; a parameter),
  `name_key(text)` (NFKC, casefold, strip; adapters build name refs with it) and
  `pair_in_order(slots, drafts, windows)`: greedy two-pointer over both sides by time within one
  same-play key (item id, or title plus album artist); a slot already holding the draft's stream
  is no candidate; never nearest-first.
- `<pkg>/services/sources.py`: `SourceAdapter` gets `key`, `service`, `fetch(cursor) ->
  Iterator[Batch]` (oldest first); `Batch.cursor` is the position they cover, `None` writes none.

**2b, `<pkg>/services/ingest.py` and `catalogue.py`:**
- `ingest(session, adapter, *, file_sha256=None, clock=utcnow) -> RunSummary(run_id, outcome,
  counts, already_imported)`: the one entry for importers, `poll.py` and any later endpoint. An
  `ok` run with that SHA returns before `fetch`; the run row commits first; one transaction per
  batch; on error roll back, mark the run `failed` (class, 300 chars) in a fresh transaction, raise.
- Per batch: (1) service lock; (2) drop stored and in-batch repeated `record_key`s; (3) resolve refs
  to items and creators (a Last.fm name ref takes the one item with that title and album artist,
  else a stand-in); (4) read the span, padded by the widest window and longest duration, and
  `pair_in_order`; (5) re-source: an export draft deletes the Last.fm/poller observations of the
  event it joins, a live draft meeting an export event is refused, live-only events inside the
  export's span are counted at run end; (6) insert, `resolve` and write each touched event, delete
  emptied events and orphan stand-ins; (7) `catalogue.store_facts(...)`, the one cache write (Lane 5
  reuses it); (8) `batch.cursor`; (9) commit, here only. Counts: `new`, `duplicate`, `matched`,
  `resourced`, `refused`, `unmatched_live` + `dropped`.
- **Needs from Lane 1** (shapes, not names; ORM rows with relationships loaded, mapped to domain
  values here): source get-or-create and write-cursor; run start, finish, ok-with-sha;
  `lock_service` (Postgres advisory xact lock, no-op on SQLite); observations known-keys, insert,
  delete; items by refs, create, single-by-title-and-creator, delete-if-unreferenced; creators
  resolve-or-create and link; events in-span, create, set-columns, delete-if-empty,
  live-only-in-span; cache upsert; relationships `Event.observations`, `Observation.item_ref`,
  `Item.creator_links`.
- Tests: `test_domain_*.py` (every arrival order of export, poller and scrobble resolves the same
  event; back-to-back plays pair k-th with k-th; a relinked URI pairs by name); `test_ingest.py`
  (re-ingest adds nothing, in-batch repeats, null-item event, a failure on draft 3 leaves neither
  observations nor cursor, re-sourcing both ways); a Postgres-only race test. If otherwise:
  decision 1 bigint changes `EntityId` only; decision 3 changes nothing here.

## Lane 3 — Sign-in, backend half (gate: decision 2 only)
Stateless under the leaning, a signed cookie: no table, no migration (a session table: Lane 1's).
- `<pkg>/services/auth.py`, stdlib only: `verify_password(plain)` against `owner_password_hash`
  (scrypt, constant-time), `issue_session(now)` (`{"sub", "exp"}`, HMAC-SHA256 with
  `session_secret`), `read_session(token, now) -> bool`. Revoking everywhere is rotating the
  secret. `python -m constellate.hash_password` prints the hash to paste: no plaintext in `.env`.
- `config.py`: `owner_password_hash`, `session_secret` (>= 32 bytes), `session_ttl_days=30`,
  `session_cookie_secure=True`; unset fails closed (every login 401). `api/deps.py`:
  `require_session` over `APIKeyCookie(name="constellate_session", auto_error=False)` raising
  `Unauthenticated`: 401 in the envelope, no new `ErrorCode`, the scheme in `securitySchemes`;
  every router but health takes it.
- `api/routers/auth.py`: `POST /auth/login {password <= 256 chars} -> 200 MeResponse{subject:
  "owner"}` + `Set-Cookie`; `POST /auth/logout -> 204` (open, idempotent); `GET /me -> MeResponse`.
  Cookie: HttpOnly, `SameSite=Strict`, `Path=/api`, `Secure` per setting; with JSON-only bodies
  that is the CSRF bound M2's writes inherit. Brute force: scrypt's cost, then 10 failures per 10
  minutes in process memory answer 401 unchecked.
- `tests/conftest.py`: `client` carries a cookie from `issue_session` (secret patched on
  `settings`), `anon_client` is a second client without. `test_auth.py`: each cookie attribute;
  wrong password, tampered and expired cookies are 401 envelopes; a round trip through `/api/me`
  (the jar honours `Path`); every OpenAPI operation has `security` unless on a three-name
  allow-list, so a later router cannot forget it. Contract additive (three paths, two schemas, a
  scheme, 401 on operations); Lane 7: any 401 means clear the session and show sign-in.
- If otherwise: a bearer token swaps the reader and drops login/logout and the cookie settings;
  Caddy basic auth deletes this lane and `/me`, leaving the API open on loopback.

## Lane 4a — `spotify-export` importer (gate: 2b), and the shape 4b-4e follow
- `<pkg>/sources/spotify_export.py`: `SpotifyExportFile(name, data: bytes)` (a `SourceAdapter`),
  `parse_record(rec) -> DraftEvent | None`, `iter_export_files(path)` over a zip, directory or file:
  members `Streaming_History_Audio_*.json`, read in memory under a 64 MB cap, never extracted.
  Entry point `<pkg>/importers/spotify_export.py` (`python -m constellate.importers.spotify_export
  <path>`): per file `sha256`, `ingest`, print counts, exit 1 on failure; `__init__` docstring-only.
- Mapping: `record_key = spotify-export:<uri>@<ts>`; `started_at = ts - ms_played`; `measured`;
  track: ref `spotify:track`, `detail {"album"}`, creator the *album* artist (kind `artist`, role
  `album-artist`, ref `spotify:artist-name` = `name_key`); episode: `spotify:episode`, the show as a
  `show` creator with ref `spotify:show-name` (my reading of `docs/02` §3); chapter:
  `spotify:chapter`, the audiobook as `show`; no recognised URI: null item. `raw` is the record
  less `ip_addr` (keeping it: one line); `offline_timestamp` is never read, only kept in `raw`.
  `ms_played` 0 is a play. `Streaming_History_Video_*` is skipped and counted: fields undocumented.
- Tests: `tests/fixtures/spotify_export_sample.json`, synthetic (the repository is public; no real
  plays, `ip_addr` in `203.0.113.0/24`), through `ingest`: a second run is `already_imported`, a
  re-split file all `duplicate`, counts sum to the records read; the owner's file closes #15.
  If otherwise (decision 3): dropping private, podcast or audiobook plays is one counted skip each.
- **4b `youtube-takeout`**: same pattern on `watch-history.json` (folder and file names are
  localised: a `--member` override); `google-watch:<video id>@<time>`; `start_only`; ads dropped
  and counted; id from `titleUrl`'s `v=`, channel from `subtitles[0]` (`youtube:channel`); no URL:
  null item, key `google-watch:-@<time>`. The owner's file settles §7's three unknowns. Parse
  helpers 4e reuses sit in a leaf importing only `domain/`.
- **4c `lastfm-scrobbles`**: pages arrive newest first, so it collects all since the cursor and
  yields oldest-first batches, `cursor = {"from": newest uts}`; first run looks back 30 days;
  `lastfm:<artist>|<title>@<start>`, `to_end`, name ref `lastfm:track`; the 100 MB cap, the credit
  and a delete-all path (`services/retention.py`, shared with 4d's disconnect) are its.
- **4d `spotify-poller`**: tokens in a file at a configured path, never a table; a bounded run skips
  itself while another holds an advisory lock; the open play is the cursor, sent with zero drafts
  after each sample; an observation only on close; `Catalogue` carries length, ISRC, artists.
  **4e** shares 4b's parser and keys, cursor `{"start_time"}`, built only if the spike passes.

## Lane 6 — Read API (gates: Lanes 1 and 3)
- Files: `<pkg>/api/routers/{events,totals,sources}.py`, `api/cursor.py` (base64url JSON of
  `(started_at, id)`; malformed is `Malformed`), `api/schemas.py`, `services/{events,totals,
  sources}.py` (validation, the clock for the 30-day rule), `config.timezone` (IANA, default `UTC`,
  validated at start; Windows needs a win32-marked `tzdata` dependency). Routers take `RESPONSES`
  and `require_session`.
- `GET /events?cursor&limit(50, 1..200)&since&until&service&item_id&creator_id` -> `EventPage{items,
  next_cursor}`, `started_at desc, id desc`, said in the description. `EventOut{id, started_at,
  duration_ms|null, duration_basis, length_ms|null, item: ItemOut|null}`; `ItemOut{id, service,
  kind, title, detail: {str: str}, creators: [CreatorOut{id, kind, name, role}]}`. `length_ms` is
  the cached length, absent past 30 days; clients read it by basis (`to_end` estimate, `start_only`
  upper bound). Descriptions say events change after they are written.
- `GET /totals/periods?bucket=day|week|month&since&until&service` -> `{timezone, bucket, items:
  [PeriodTotal]}` ascending, unpaginated, range bounded (`day` over 400 days is 422).
  `GET /totals/creators?kind&...` and `GET /totals/items?kind&...` take `service&since&until&
  sort=time|plays&limit` and return `{items: [SubjectTotal], omitted_count}`: a ranked top-N with
  `limit` only (<= 200, default 50), since the Conventions' cursor is for lists that enumerate (its
  keyset would be `(rank, id)`); `omitted_count` counts events with no item.
- Every row: `measured_ms` (basis `measured`), `estimated_ms` (`to_end`, fresh length),
  `upper_bound_ms` (`start_only`, fresh length), `unknown_count` (all else, null-item events
  included), `event_count` (a test: the buckets sum to it); period rows add `period_start: date`.
- `GET /sources` -> `{items: [SourceStatus{key, service, last_success_at|null, last_run,
  recent_runs (10)}]}`, `RunOut{id, started_at, finished_at|null, outcome|null, counts: {str: int},
  error|null}`. Contract additive; units ms, instants `Z`, dates `YYYY-MM-DD`: Lane 7's hand-off.
- Needs from Lane 1 (`now` a parameter): events list-page with item, creators, cached length; totals
  by period (bucket, zone), creator, item; latest runs per source; sources list. Tests seed via
  `models/` (`tests/seeds.py`); period bucketing is `date_trunc` at the zone: Postgres-only cases.
- If otherwise: decision 1 bigint makes `id` an `integer` (settled before this lands); a music
  split adds a `product` filter once Lane 1 promotes `header`; a per-event zone stays `docs/02` §8.

## Lane 5 — Enrichment and the ISRC merge (gates: Lanes 1, 2b)
`sources/youtube_data_api.py` (`videos.list`, 50 ids a call, the owner's key) behind a second
protocol `CatalogueAdapter.lookup(refs)` (it yields facts, not drafts); `services/enrich.py`
refreshes rows over 25 days and deletes those past 30 through `catalogue.store_facts`, with an
`ingest_run` under source `youtube-data-api` for `/sources`; entry `python -m constellate.enrich`.
Spotify `GET /tracks/{id}` and `services/merge.py` (ISRC merge) trail 4d. No contract change.

## Not in this plan, and verification
Not here: an upload endpoint; an item `url`; the YouTube gap-capped estimate; a cursor on top-N
lists; a session table; edits to `docs/03` ("Not decided here", the `unauthenticated` row) and the
`CLAUDE.md` files under `api/`, the session's. Verify from `api/` with its venv: `ruff check . &&
ruff format --check .`; `pytest -q` (SQLite; CI adds Postgres); `python scripts/export_openapi.py
--check`; from the root `python scripts/check_layering.py`; Lanes 3 and 6 add `npm run
check:api-types` from `web/`.
