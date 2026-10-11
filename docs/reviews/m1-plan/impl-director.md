# impl-director plan — M1's first lanes (the tracker)

*Authored at the plan-before-code round for M1, after the scaffold (`a7cfbe4`, PR #9) merged.
The director cuts across layers and writes no code (fleet "Plan before code"); each lane's own
plan comes back to this file's author before that lane codes. Ownership follows
`.claude/agents.local.md`'s map; the build order schema → API + contract → clients
(ADR-0002) holds throughout. The domain model is `docs/02-domain-model.md`; the seam is
ADR-0003.*

*Amended by `impl-director-check-1.md` (round 1, 2026-10-11), after reading the three specialist
plans. The amendments, marked `[C1]` below: `event.service` added to Lane 1; the candidate
lookup made a span read matched in `domain/`; re-sourcing pinned to Lane 2 (not 4a/4c); the
`SourceAdapter` shaped by all documented sources, not the first; `/totals` split into three
paths with top-N rankings; local-day fields added to the read contract; the Last.fm credit's
display moved to Lane 7; Lane 7's parallelism corrected; and decisions 2–3 sharpened.*

*Amended again by `impl-director-check-2.md` (round 2, 2026-10-11), after the two plan reviewers.
The `[C2]` amendments below: four findings go to the owner (decisions 6-9 - the host Q-E, an owner
column, the null-item/`event.service` record rewrite, and recording each answer before its code);
name-key equality taken out of SQL; the configured zone moved off `/me` onto the read responses;
the local-day expression made one `repos/` helper; the `/sources` read split from the seam module;
Spotify video plays stored not skipped and the YouTube-Music split dropped from M1; a plain-format
export lane added; Lane 8 re-gated to schedule every unattended job; the extension's exclusion made
conditional on the #11 spike; the `CatalogueAdapter` protocol recorded; and the codegen-ownership
claim corrected (the overlay already blesses it).*

## Open decisions for the owner (settle before the lanes they gate; one message)

1. **The key type of every table (#10).** Gates Lane 1, and Lane 1 gates the whole milestone,
   so this is the first thing to settle and the cheapest. `Owned` in `models/base.py` offers
   app-minted UUIDv7; `docs/02` §7 sketches `bigint generated always as identity`.
   **Leaning: UUIDv7, app-minted, uniform across every single-key table.** The atlas (M4) needs
   public, stable, shareable ids across devices and imports, a time-ordered key keeps the
   `event` index local, and 16 bytes against 8 is nothing at this scale (~500k events/decade).
   The one counter-argument is index size on the two high-volume tables (`event`,
   `observation`); it does not outweigh a single uniform scheme. If `bigint` wins instead,
   `Owned` loses its `id` and `ids.py` goes until something needs it. **Settle before the
   migration is written: afterwards it rewrites every FK.** [C1: both specialists stressed this.]

2. **The sign-in scheme** (`docs/03` "Not decided here"; M1 needs it). M1 is private, single
   user. The scaffold already put `unauthenticated` (401) in the closed `ErrorCode` set so the
   contract's enum does not move when sign-in lands. **Leaning: one owner password in config,
   exchanged for an HTTP-only session cookie; a `RequireSession` dependency guards every endpoint
   but `/health*`; the 401 travels in the error envelope with code `unauthenticated`.** [C1: the
   sub-choice the leaning left implicit, named now so one message settles it — a **stateless
   signed cookie** (HMAC over the secret, no table, revoke-all by rotating the secret) or
   **revocable stored sessions** (an `auth_session` table). Leaning: the stateless cookie — a
   single private user needs no per-session revocation, and it keeps Lane 3 off Lane 1. If stored
   sessions win, they add a separate migration `0003_auth_session` and three repo functions as an
   `impl-database` small task that does **not** block Lane 1/0002.] "Port the sibling's scheme"
   is a build from its description, not a copy: its code was deliberately not ported by the
   scaffold and is outside the worktree, so no specialist has read it. Gates Lane 3.

3. **The `docs/02` §8 import choices** (before Lanes 4 and 6; the null-item half is **decision 8**,
   which gates Lane 1 - the rest live in `raw` or are already allowed by §7 and do not block Lane 1). **Leanings, from the M0
   consolidation handoff:** import everything the export holds — private-session plays,
   podcasts, audiobooks, Spotify video plays — and filter in totals, since a dropped record
   never returns; strip `ip_addr` on import,
   keep `conn_country`; one configured time zone for local-day buckets; an unidentifiable watch
   is an event with a null item (§1, now decision 8). `header` and `incognito_mode` stay in `raw` and are
   promoted to columns later if a total needs them — cheap, so Lane 1 need not wait on this.
   **[C1: two consequences of the null-item leaning, surfaced here so they settle with it.** (a)
   Under the null-item leaning the `event` gains an immutable `service` column (Lane 1), so the
   timeline's service filter and per-service totals can place a watch that names no item; under
   the *placeholder-item* alternative that column is unnecessary, because the placeholder carries
   the service. (b) The `kind` filter (track/episode/chapter/video) ships in M1 and is how
   podcasts/audiobooks are filtered in totals; the **private-session** and **YouTube-Music-split**
   filters need `incognito_mode`/`header` promoted to columns first, so totals ship *unfiltered*
   for those two until a later migration promotes them — not M1 scope.]** **[C2: the null-item /
   `event.service` consequence (a) is now **decision 8** (it gates Lane 1 and carries its own record
   rewrite); the leaning no longer asks to split YouTube Music in M1 (direction review 5) - `header`
   is kept in `raw` for a later migration; and 4a stores Spotify video plays rather than skipping
   them (see Lane 4a).]**

4. **Owner-provided inputs that gate *verification* only, never the code** (each lane is built
   and tested against fixtures drawn from the documented schemas): request the extended Spotify
   streaming history at the account privacy page (#15, up to a month to arrive); check YouTube
   History and its auto-delete, then request a JSON Takeout (#16); connect Spotify to Last.fm
   and obtain a Last.fm API key (#12); register a Spotify developer app and sign in for the
   sampler, Premium already confirmed (#13); confirm the Google account is in the EU,
   Switzerland or the UK and over 18, then grant `myactivity.youtube` for 180 days for the spike
   (#11). **These are owner actions, not decisions — but they decide when each lane can close.**

5. **YouTube's daily-capture path turns on the #11 spike, which is the owner's to run.** Pass:
   Data Portability is the daily source and the host must encrypt at rest (Q-E); the extension
   stays deferred. Fail: scheduled Takeout carries freshness and the extension's case
   strengthens (Q-F). **Leaning: run the spike early; it touches no store code and unblocks the
   YouTube daily-capture lane either way.** **[C2: a failed #11 spike means scheduled Takeout is a
   hand download up to two months late, so M1's "done when" for YouTube cannot hold as written; a
   fail puts Q-F - the extension in M1, for the same-day desktop signal - or an amended done-when to
   the owner (`docs/00`; `docs/01-data-sources-youtube.md` §6).]**

6. **Where it runs (Q-E), whose store half falls due inside M1 (direction review 1).** Lane 1 is
   the first table migration, and after it ADR-0002's cost-free switch to SQLite is gone; M1's
   "done when" needs an unattended host, and Q-E is open "until M1 needs it". **Leaning: the
   sibling's PC, Postgres a service that starts with the machine.** Settle the store half - "will
   the host keep Postgres running as a service?" - before Lane 1; if it cannot, the store is
   SQLite and ADR-0002 is revised, not worked around (`docs/08` Q-E; ADR-0002 Consequences). The
   rest (the scheduler fires signed out, encryption at rest if 4e passes) settles before Lane 8
   closes. A session/`infra/` step brings the host up, verified by the done-when.
7. **An owner column from day one (direction review 2).** `docs/08`'s "Smaller, for later" and
   `docs/00`'s deferred-multi-user row ask whether the log carries an owner column now; Lane 1 is
   day one, and the database plan parks it under "Not in this plan" without asking - which the
   root `CLAUDE.md` forbids for a `docs/08` question. **Leaning: no column.** One user is the
   scope, `docs/00` defers multi-user, and `docs/02` §8 already says nothing depends on it; the
   retrofit is a migration, taken if the scope changes. Settled, the answer moves to `docs/08`'s
   Answered.
8. **A null item, hence `event.service` - and the record it rewrites (direction review 3).** This
   is decision 3's null-item half, pulled out because it alone **gates Lane 1** (it sets 0002's
   shape: a nullable `item_id` and an immutable `event.service`), and because `event.service` is
   an event column written once, not resolved - which contradicts `docs/02` §1 ("a total per
   service reads the item's service"), §6 ("none of them names a service or a format"),
   ADR-0003's four resolved columns, and the overlay's "the event carries no source ... never
   written directly". **Leaning: the null item with `event.service`, and the record rewritten as a
   Lane 1 precondition** (`docs/02` §1 and §6, the overlay's invariant, and a dated note on
   ADR-0003 that `service` is fixed at creation - not a source, since matching never crosses
   services). The alternative is a **placeholder item** per unidentifiable record: `event.item_id`
   stays NOT NULL, `event.service` is dropped, and per-service totals join observation to source.
   Settle before the migration.
9. **Each answer written down before the code that builds on it (direction review 4).** The plan
   folds the stale record lines inside each lane's code PR; the owner's answers must be written
   first (root `CLAUDE.md`: "an answered question in `docs/08` first, code second"). **Leaning: a
   record step heads each gated lane** - before Lane 1, quote and date the key-type and import
   answers in `docs/02` §8 and close #10; before Lane 3, record the sign-in scheme as a short
   `docs/03` section (an ADR if the owner prefers the sibling's precedent - M1 is private, single
   user, so a section suffices); the import answers in §8 head Lane 4; and the item-precedence
   rank goes into `docs/02` §2 as ADR-0003's detail. Not a new product choice but where each
   answer lands.

Not owner decisions, stated so a specialist does not put them to the owner: **importers are
commands** (`python -m constellate.…`), entry points reaching data through the one ingestion
service, not a second write path and not endpoints — so they do not touch the contract (an
upload screen is M2+ polish). **[C1: also the specialists' own, confirmed not the owner's — the
item-precedence order (backend's reading of ADR-0003's "highest-ranked": owner's own records
first — export, then Takeout/Portability, then extension, then poller, then name-only Last.fm —
a tunable rule in `domain/`, like the windows); mapping an audiobook's author to the `show`
creator kind (`docs/02` §6 settles it, no new kind); the SQLite inability to test
`date_trunc`-at-zone totals (a Postgres/CI hand-run, not a design change).]** Director's calls, a
sketch; if a later reviewer argues otherwise and the direction holds, that stands over this.

## The cut: who owns what, in order, with the gates

### Lane 1 — The schema (the backbone), `impl-database`. Gate: decision 1 (#10).

The one migration that turns `docs/02` §7's sketch into the schema, plus its `models/` and the
`repos/` queries **Lane 2's steps 1–5 call** — not the later lanes' queries. Everything else in
M1 waits on this hand-off.

- `models/` + one Alembic revision (`down_revision` = `0001_scaffold`) for the core log tables,
  exactly `docs/02` §7: `source`, `ingest_run`, `item`, `item_ref`, `creator`, `creator_ref`,
  `item_creator`, `event`, `observation`, `catalogue_cache`. Load-bearing shape the hand-off
  fixes: `observation.record_key` unique; `item_ref` unique `(namespace, value)`;
  `creator_ref` PK `(namespace, value)`; `event` nullable `item_id`, indexes on `started_at`
  and `(item_id, started_at)`, and the `duration_basis` check that `measured` ⇔ `duration_ms`
  is not null; `catalogue_cache` keyed by `item_ref_id`; `source.cursor` a JSONB the adapter
  owns. Key type per decision 1. **[C1: `event` gains an immutable `service` column, set at
  creation from the draft's source's service and never re-resolved. It is not a *source* on the
  event (ADR-0003's invariant holds — a service is single per event because matching never
  crosses services, whereas a source is not); it is what lets a null-item event be filtered and
  bucketed by service, which reading service through the item cannot do. Dependent on decision 8 (it
  gates Lane 1, and the `docs/02` §1/§6 + overlay + ADR-0003 record edits it needs are a Lane 1
  precondition): dropped if the owner chooses a placeholder item.]**
- `repos/` for Lane 2's steps 1–5 only (the specialist drafted the signatures; the capabilities
  the hand-off names): find-item-by-ref / create item+ref from a hint; resolve-or-create creators
  and their `item_creator` links; the **per-service advisory lock** (SQL, so `impl-database`'s, a
  no-op on SQLite); the **bulk** drop-by-`record_key` check (step 1 as a batch); insert an
  observation; read all of an event's observations to re-resolve its columns; the re-sourcing
  deletes (an event's live observations by source id, empty-event and orphan-item pruning);
  ok-run-by-SHA before parsing; upsert/read a `catalogue_cache` row with the 30-day as-absent
  rule; read/write a `source.cursor`. **[C1: the candidate-event lookup is a *span read* — the
  service's events in a time window with their observations, item and creators loaded — and the
  same-play comparison (ref, or title+album-artist name-key) and in-order pairing live in
  `domain/matching.py`, not in SQL. The matching windows and the name-key equality are tunable
  rules (ADR-0003; `docs/02` §2), so they may not be buried in a repo. The repo may narrow by
  item id where a ref is known, but no name-key matching is SQL. [C2: the same rule removes the
  name-key equality from the item-resolution lookup for a Last.fm name ref (architecture review 1,
  `find_items_by_name`'s casefold `=`): the repo narrows by the creator the ref resolves to (items
  linked as album-artist to the creator whose `spotify:artist-name` ref is `name_key(artist)`), and
  a `domain/` function picks the one whose `name_key(title)` matches - SQLite's ASCII-only `lower()`
  must not be a third answer. The database and backend lane plans change to match.]**
- **[C1: the timeline/totals repos (Lane 6), the disconnect/undo deletes (Lanes 4c/4d), and the
  enrichment/merge repos (Lane 5) are *small `impl-database` tasks briefed when their lane plans*,
  not in the Lane 1 PR — the permanent SQL line below. The specialist sketched their signatures;
  none is coded until its lane needs it.]**
- Register the revision in `test_migrations.py` (`NO_ROWS` with a reason, or `_COVERED`).
- **Session folds #17 in this same PR** (record, not a specialist): delete `docs/02` §7's SQL,
  point §1 at where the schema now lives, **[C1: and add the `event.service` and null-item rows to
  §1's Event table]**; fix `alembic/CLAUDE.md`'s "one empty revision" and `api/tests/CLAUDE.md`'s
  "No Postgres-only migration cases exist yet", both stale after this PR. `python
  scripts/check_docs.py` must pass.

Hand-off to every downstream lane: the model classes and the `repos/` method signatures. The
SQL line between this lane and `impl-backend` is permanent — **any query a later backend lane
needs is a small `impl-database` task, briefed by that lane's stated need**, never a query
written in `services/`.

### Lane 2 — The ingestion seam, `impl-backend`. Gate: Lane 1 (its `domain/` half, un-gated, may run beside Lane 1). [C1]

The one persist path (ADR-0003; `docs/02` §2). No source adapter is needed to build or test it.
**[C1: splits into 2a (pure `domain/`, un-gated) and 2b (the orchestration in `services/`, gated
on Lane 1), so `domain/` can be built beside Lane 1. Backend's call.]**

- `domain/` (2a): the `DraftEvent` type (fields per `docs/02` §2: `source`, `record_key`,
  `item_ref`, `item_hint`, `started_at`, `duration_ms`, `duration_basis`, `raw`, `catalogue`),
  the three bases, the pure resolution rules — precedence for item, start, duration and basis
  (ADR-0003's order), and the one-to-one, in-order pairing with per-pair windows as parameters
  (the windows are not part of the decision; `docs/02` §2 tables them) — **[C1: and the `Batch`
  shape and the candidate comparison the span read feeds.]** No I/O. The vocabulary `StrEnum`s
  live here and a test pins them equal to `models/`'s CHECK literals (the two specialists' agreed
  no-drift guard; one source, a guard, either shape).
- `services/sources.py`: give `SourceAdapter` its members. **[C1: shaped by *all* the documented
  sources (`docs/02` §2), file and pollable — `fetch(cursor) -> Iterator[Batch]` with the cursor
  optional (a file has none) — not shaped by the first adapter (Lane 4a) alone. Later adapters may
  add members, not change them.]**
- `services/` (2b): the single ingestion service running ADR-0003 steps 1–5 in one transaction
  per batch — drop by `record_key`; resolve item and creators; find-or-create the event by the
  span read + `domain/` matching; store the observation; re-resolve the event's columns; write
  `catalogue` to the cache, never the log. It takes the per-service lock and commits the `source`
  cursor with the observations it covers, oldest first; the run row commits before the first
  batch, so a rolled-back batch cannot carry the `failed` record away with it.
- **[C1: re-sourcing (`docs/02` §4; ADR-0003's amendment) is Lane 2's, not 4a/4c's — the cut
  named it only under 4c. The one service's rule: an export observation joining an event deletes
  that event's live (Last.fm/poller) observations; a live draft that would join an event already
  holding an export observation is refused, not stored; live observations in the export's covered
  span that no export draft matched are kept and counted in the ingest run.]**

Hand-off to Lanes 4 and 5: the `DraftEvent`/`Batch` type and the ingestion entry function every
adapter, importer and the poller call.

### Lane 3 — Sign-in, `impl-backend` then `impl-frontend`. Gate: decision 2. Parallel to Lanes 1–2.

- Backend (`api/`, `services/`): the session mechanism (stateless signed cookie under the
  leaning, no table), `/auth/login`, `/auth/logout`, `/me`, the `RequireSession` dependency on
  every endpoint but `/health*`, and the 401 in the envelope. `api/tests/` `client`/`anon_client`
  fixtures diverge here, as `api/tests/CLAUDE.md` foretells. **[C2: `/me` carries only the subject; the configured `time_zone` moves off `/me` onto the
  **read responses** that the zone shaped (Lane 6) - the zone is the read model's fact and `/me`'s
  shape must not move with the sign-in scheme (architecture review 2). The cookie's attributes (`HttpOnly`; `SameSite` Strict or Lax; `Path`;
  `Secure` off on the dev http origin, on in prod) are backend's as the setter, aligned with
  frontend before Lane 3 lands; the one constraint is that a same-origin `fetch` carries it,
  which Strict and Lax both do.]** Regenerate `api/openapi.json` and the generated `schema.d.ts`
  (below). **Session folds the record edits this lane makes stale**: `docs/03`'s "Not decided
  here" sign-in line and the `unauthenticated`-row note; `api/CLAUDE.md`'s auth settings. **[C2: the scheme is recorded in `docs/03` (or an ADR, the
  owner's call - decision 9) *before* this lane's code, not folded in the same PR.]**
- Frontend (`web/`): a sign-in route, the 401 → clear-session wiring, a route guard.

Build this before Lane 6 ships so the read endpoints land already protected.

### Lane 4 — Sources, `impl-backend`. Gate: Lane 2. Order: backfill before live (roadmap rule 3).

Each is an adapter under `sources/` producing `DraftEvent`s into Lane 2's service, run as a
command (importers) or via `poll.py` (pollable). Code and tests use fixtures; the owner's real
data closes the lane (decision 4).

- **4a `spotify-export` (#15), first — the record and the richest draft.** Files, no cursor, a
  file re-offered recognised by its SHA on `ingest_run`; `record_key`
  `spotify-export:<uri>@<ts>`; start `ts − ms_played`; basis `measured`; album in `item.detail`;
  album-artist as the `spotify:artist-name` creator ref. **[C1: an audiobook chapter's author is
  the `show` creator kind (`docs/02` §6), not an owner question.]** Mind `offline_timestamp`'s
  unit change. Done when a real export imports through the one service, a second import of the
  same file adds nothing, and the ingest-run counts are shown. **[C2: the import-everything leaning
  means 4a parses `Streaming_History_Video_*` and stores those plays too (in `raw`, a null item
  where no catalogue item is recognised, counted) rather than skipping them - a record skipped in a
  file whose SHA has an `ok` run never returns (decision 3's own reason; direction review 5). The
  backend lane plan's skip changes to match.]**
- **4b `youtube-takeout` (#16).** Files, no cursor; `record_key` `google-watch:<video id>@<time>`
  (the Portability path produces the same key); basis `start_only`; drop ads; keep
  `header` in `raw` (the YouTube-Music / YouTube split is a later migration, not M1 - no column, no
  filter; decision 3 [C2]); strip the localised "Watched"; channel id from
  `subtitles[0].url`; removed/private → event with null item. Settles the three §7 unknowns
  (Shorts, Music `titleUrl` host, whether `time` is the start) on the owner's Takeout.
- **4c `lastfm-scrobbles` (#12) — the live tail, works with no Spotify app.** Pollable;
  cursor = newest scrobble time; `record_key` `lastfm:<artist>|<title>@<start>`; basis `to_end`;
  name ref `lastfm:track`; the two Last.fm matching windows (`docs/02` §2); the 100 MB cap and a
  delete-all-Last.fm path for termination (§4). **[C1: the required Last.fm credit and link are a
  *display* obligation — Lane 7's (a footer and the sources screen), since an event carries no
  source for a row to mark; 4c owns only the data-side terms.]** Re-sourcing to the export is
  Lane 2's, so this gates on Lane 2, not on 4a. Settles the three unknowns in #12 on the owner's
  scrobbles.
- **4d `spotify-poller` sampler (#13) — optional, on top, for measured time.** Via `poll.py`: a
  bounded sampling run, 30 s playing / 3 min idle, one open play as the cursor, an observation
  emitted only on close; split the track object (URI + times → observation; length, ISRC,
  artists → cache); store the last successful run; a working disconnect that deletes every Web
  API observation and cache row as a set within five days; the six-month sign-in warning.
  Nothing in the log may depend on it (§4). **[C2: 4d's Spotify connect (OAuth) and disconnect are
  **commands** (`python -m constellate.…`), not endpoints, in M1 - an endpoint would be the first
  write path outside Lanes 3 and 6 (M2+ polish); architecture review follow-up.]**
- **4e `google-portability` (#11 spike, then the adapter if it passes).** The spike (owner-run,
  decision 5) decides the path; the adapter, if built, feeds the same `google-watch:…` keys as
  4b into the one service with a `start_time` cursor (`docs/02` §2).

### Lane 5 — Enrichment cache + ISRC merge, `impl-backend`. Gate: Lanes 1 + 2. Additive precision.

The `videos.list` job (lengths/category as cache, 50 ids a call, refresh rows over 25 days,
treat >30 days as absent, delete unrefreshed at 30) and Spotify `GET /tracks/{id}` enrichment,
plus the merge-of-two-URIs-on-one-ISRC service op (§3). Writes only `catalogue_cache` and
re-points refs; **the log never depends on it**, so it can trail the read lane. **[C1: each cache
row carries the id of the Spotify Web API source that supplied it (the poller's), or the
disconnect's delete-as-a-set misses it (§4); a merged item's cached length is the longest fresh
length across its refs.]** Needs the owner's YouTube Data API key and the Spotify app. **[C2: the
`videos.list` source sits behind a second protocol, `CatalogueAdapter` (it yields catalogue facts,
not drafts, and writes only the cache through the one cache write), placed in `services/sources.py`
beside `SourceAdapter` (architecture review 4). Recorded before the code: a sentence in `docs/03`'s
`sources/` row and its "One ingestion path" that a catalogue-only source has its own protocol and is
not a second *log* write path - the log never depends on the cache (`docs/02` §4) - the session's
edit (direction review 9). Lane 5 closes only once its refresh-and-delete job is **scheduled**
(Lane 8): a 30-day delete run only by hand breaks YouTube's retention policy (direction review 7).]**

### Lane 6 — Read API: the timeline and the totals, `impl-backend`. Gate: Lanes 1, 3. Fixture-testable without Lane 4.

The contract's main M1 additions. Concrete hand-off to the client:

- `GET /events` — the timeline, keyset cursor per `docs/03` Conventions, ordered `started_at`
  desc, `id` desc. Each row carries `item` (**nullable** — a watch that names no item; title,
  service, kind, creators), `started_at` (UTC `Z`), **[C1: `local_date` (the configured-zone
  date, so the timeline's day headings match the totals buckets — the client must not recompute
  local days),]** `duration_ms` (nullable), `duration_basis` (`measured`|`to_end`|`start_only`),
  and `length_ms` where the cache has a fresh length (the client reads the estimate by basis).
  **[C1: filters — `since`/`until` as *local dates*, `service`, `item`, `creator`, and `kind`.
  A null-item event carries its `service` (Lane 1), so a service filter keeps it; it has no item
  or creator to match those filters.]**
- **[C1: `GET /totals` is three paths, because the row shapes and pagination differ (backend's
  call, frontend's single `?group=` sketch declined):** `GET /totals/periods?bucket=day|week|month`
  (an ascending series, unpaginated, over a range-bounded window; carries the `timezone`),
  `GET /totals/creators?kind&…` and `GET /totals/items?kind&…` (**top-N by `limit`**, bounded with
  a documented default, **no cursor** — a keyset over a computed sum shifts as events arrive, a
  reasoned departure from `docs/03`'s cursor convention confined to aggregates; the session notes
  it in `docs/03`'s Conventions). Each row carries the four numbers of `docs/02` §1 —
  `measured_ms`, `estimated_ms`, `upper_bound_ms`, and the count of events with no number — plus
  `event_count` (the buckets sum to it); creator/item rows carry the subject's `id` so the client
  links to the filtered timeline; the response carries the count of null-item events it left out.
  All filter by `service`, `since`/`until` (local dates) and `kind`.]** Local-day buckets use
  decision 3's configured time zone.
- `GET /sources` — last successful run and the ingest-run counts per source, which ADR-0003
  requires "stored and shown."

**[C1: the exact field names are backend's and frontend's to finalise *before the contract
commits* — they must agree one name each for the per-row no-number count and the per-response
left-out count. The required fields are above.]** Session folds `web/CLAUDE.md`'s stale sentences
(see Lane 7) and the `docs/03` cursor-convention note with this lane.

**[C2: three placements the architecture review fixed.** (1) The configured time zone is carried
on the **read responses it shaped** - `EventPage` and `/totals/periods`, one agreed spelling, and
`/sources` if its clock times need it - **not on `/me`** (Lane 3): the zone is decision 3's
read-model fact, and binding it to the session couples the client's day-rendering to the sign-in
scheme (were auth moved to a proxy, `/me` would vanish and the zone need a new home). (2) The
local-day expression is **one `repos/` helper**, used by the period buckets, the timeline's
`local_date` and every local-date filter, the service passing in the zone - so a heading and a
bucket cannot disagree, and the two are not split between Postgres `date_trunc` and Python
`zoneinfo` (`api/src/constellate/CLAUDE.md`'s "a rule needed by two queries is a shared `repos/`
helper"; its §54 line sending the local day to `domain/` is the session's to reconcile - a
follow-up). (3) The `/sources` status read lives in `services/source_status.py`, **not**
`services/sources.py`, which stays the adapter seam (`SourceAdapter`, and Lane 5's
`CatalogueAdapter`) and nothing else (`docs/03`; `api/src/constellate/CLAUDE.md`). The backend
lane plan changes to match (the 2a/6 modules and the zone carrier).]**

### Lane 7 — Web client, `impl-frontend` (`web/`). Gate: see below. Own worktree. [C1]

A timeline screen, a totals screen, a source/ingest-status view, and the sign-in screen,
each a route under `routes/` reaching the generated client through `hooks/` → `api/` per
`web/CLAUDE.md`. **[C1: "runs from the start, only `schema.d.ts` waits" does not hold — a typed
hook or route cannot compile before its response type exists. So two PRs: W2 (sign-in + the
error/session plumbing) gates on **Lane 3's** contract; W3 (the three screens, one commit each)
gates on **Lane 6's** contract and W2. Pure `lib/` may be drafted early, unmerged. The session
asks Lanes 3 and 6 to land their response schemas and regenerated `openapi.json` in their lane's
*first* commit, so the client is unblocked without waiting for the whole lane.]**

- **[C1: the Last.fm credit and link live here — a footer in the signed-in layout and on the
  sources screen (a rendering duty, not 4c's).]**
- **[C1: the scaffold's `Health` *screen* is retired when the timeline lands (W3); the
  `/health*` *endpoints* stay for the probes. No diagnostics screen — `/sources` answers "is
  capture working".]**
- **[C1: the device target ADR-0002 left as "phone-friendly" is made concrete in `web/README.md`
  (frontend's): phone-first, one widening breakpoint.]**

**[C1: the session files product-board issues for Lanes 3, 6 and 7 — the consolidation handoff
filed none for the read API, the totals, the sources view or sign-in — each with its route,
endpoint and done-criteria, before the lane starts.]** Session folds `web/CLAUDE.md` (its owner):
name `lib/` and `components/` and their rules, drop the `health` and "nothing needs a DOM yet"
sentences, name the new layering check.

### Lane 8 — The scheduled tasks (#14), session/`infra/`. Gate: Lane 4c exists; partially blocked by Q-E (decision 6).

The task definition and its installer committed under `infra/` (no specialist owns it), the four
Task Scheduler facts verified and recorded where ADR-0002 names them, the `infra`-area tests
asserting the settings. The definition can be written now; "fires after a reboot with nobody
signed in" cannot be shown until Q-E names the host — so this lane drafts now and closes with Q-E.
**[C2: this lane schedules *every* unattended job, not only the optional poller (direction review
7): the Last.fm poll (4c, the backbone), the enrichment refresh-and-delete (Lane 5, a YouTube
retention obligation), the Portability pull (4e, if the spike passes) and the Spotify poller (4d, if
the owner registers the app). It gates on **4c**, not 4d - gating on the optional poller leaves the
backbone unscheduled if the owner never registers the Spotify app (#13). `docs/08` Q-E's "with the
daily jobs beside it" is what this covers.]**

### Lane 9 - The plain-format export (`docs/00` v1 criterion), `impl-backend`. Gate: Lane 1. Entry point, no contract. [C2]

**[C2: added - the cut named it in neither a lane nor "Not in scope" (direction review 6).** A
command (`python -m constellate.export`) that reads the log through `services/` and writes a
plain-format dump of the owner's own records and the events they resolve, leaving out the cache
and every live observation by construction (`docs/02` §4). It is `docs/00`'s v1 success criterion
- "the whole log can be exported, in a plain format, at any time" - and §4's long-term copy: once
the live tail (4c) runs, database backups last at most five days, so without the export no copy of
the log is older than that, which breaks the vision's "kept for years ... never dependent on
either service". An entry point, so `impl-backend`'s, and it adds nothing to the contract; it
should land before the live tail is relied on continuously. The session records it in `docs/07` as
M1 scope (it was silent).]**

## Order and parallelism

Settle decisions 1–3. Then Lane 1 (the gate). Lane 2's `domain/` half (2a) and Lane 3 start
before Lane 1 lands (2a needs nothing; 3 needs decision 2); Lane 2b waits on Lane 1. Lane 4's
adapters gate on Lane 2; Lane 6's reads gate on Lanes 1 and 3 (its tests seed through `models/`,
so it can run beside 2b). Within `impl-backend` the lanes serialise unless the session runs two
backend worktrees, as the scaffold did ("at most two opus runs at once"). **[C1: Lane 7's W2 gates
on Lane 3's contract and W3 on Lane 6's — the client does not "run from the start"; only pure
`lib/` can be drafted ahead.]** Lane 5 trails; Lane 8 drafts alongside and closes with Q-E.
**With decisions 1–3 answered, every lane's code is built and tested against fixtures with no
further owner input; the owner's exports, credentials and the #11 spike close the lanes, they do
not unblock the code.** **[C2: the order now also reflects the round-2 folds - decision 6's store
half and decision 8 (the null item, hence 0002's shape) settle *before* Lane 1 alongside decision
1; decision 9's record steps head Lanes 1, 3 and 4; Lane 8 gates on 4c (every unattended job), not
4d; and Lane 9 (the export) gates only on Lane 1 and should precede continuous reliance on the live
tail.]**

## Contract impact

**Additive only; nothing breaking for a generated client.** New paths — `/events`,
`/totals/periods`, `/totals/creators`, `/totals/items`, `/sources` (Lane 6) and `/auth/login`,
`/auth/logout`, `/me` (Lane 3) — and their new response schemas. No field is removed, renamed, or
made newly-required on an existing operation. **[C1: `/events` rows carry a nullable `item`,
`local_date` and `length_ms`; the configured `time_zone` is carried on the read responses
(`EventPage` and `/totals/periods`), not `/me` (architecture review 2); the totals rows carry the
four numbers,
`event_count` and (creator/item) the subject id, the response the left-out count; filters add
`kind` and local-date ranges; the ranked totals are top-N by `limit`, not cursor-paginated — a
reasoned exception to `docs/03`'s cursor convention, confined to aggregates and noted in
`docs/03`.]** Sign-in adds a security scheme and `401` responses to operations but **no new
`ErrorCode`**: the scaffold already closed `unauthenticated` into the enum for exactly this.
Importers and the poller are entry points and add nothing to the contract. Regenerate
`api/openapi.json` and then `web/src/api/schema.d.ts` in the same commit as any surface change
(standing constraint). **[C1: the backend lane that changes the contract runs `npm run
generate:api-types` and commits the regenerated `schema.d.ts` in its own PR — `web.yml` triggers
on `api/openapi.json` and fails on a stale `schema.d.ts`, and the map forbids a cross-lane
hand-off just to run codegen. This is a mechanical regeneration, not authoring `web/` code; it is
**not** a gap - the overlay's "Regenerate after any change to the API surface" already tells the
lane that changes the surface to commit both `api/openapi.json` and the regenerated `schema.d.ts`
with the change (`.claude/agents.local.md`). [C2: the earlier "(friction filed)" was wrong twice -
no note was written and the overlay already blesses this - so the claim is withdrawn (direction
review follow-up).]**

## Not in scope (so no lane builds it helpfully)

The atlas and all of M2 — favourites, ratings, notes, themes, constellations, recommendation
lists, websites as a source (`docs/02` §5); the calendar and M3 (Q-G); the browser extension and
`extension/` (Q-F), narrowed to desktop seconds-watched later - **[C2: out of scope only while the
#11 spike passes; a failed spike reopens Q-F (the extension in M1) or an amended done-when to the
owner, decision 5 (direction review 8)]**; a cross-service "work above items"
(§6); an upload endpoint for imports (M2+ polish); the account-data package (names, not an input);
**[C1: promoting `incognito_mode`/`header` to columns and the private-session / YouTube-Music-split
totals filters they enable — a later migration, so totals ship unfiltered for those two (decision
3); any revocable `auth_session` table unless decision 2 chooses stored sessions;]** any `docs/08`
§8 point the owner does not settle now stays as written (e.g. a per-event time zone). Branch
protection on `main` and the root `CLAUDE.md` `docs/ideas/` row are prior bookkeeping tracked in
their own handoffs, not this plan's to cut.

## Verification (by command)

- API, local (no Postgres), from `api/` with its venv: `ruff check . && ruff format --check .`;
  `pytest -q` (SQLite in memory); `python scripts/export_openapi.py --check`.
- Record/layering, from the repo root: `python scripts/check_layering.py` (no violations);
  `python -m unittest discover scripts/tests`; `python scripts/check_docs.py` (for #17's edits).
- Migrations, CI's alone and run by hand against the development Postgres before pushing
  (`api/alembic/CLAUDE.md`): `alembic upgrade head && alembic downgrade base && alembic upgrade
  head`, then `alembic revision --autogenerate` producing an empty diff. **[C1: the `date_trunc`
  at-zone totals cases are Postgres-only (CI or by hand), since SQLite has no `date_trunc`.]**
- Web, from `web/`: `npm ci`; `npm run check:api-types`; `npm test`; `npm run build`.
- Per issue (what proves the feature): a real export/Takeout imports through the one service and
  a second import of the same file adds nothing, with the ingest-run counts shown (#15, #16); the
  scrobble tail ingests and its basis and windows are confirmed on real data (#12); the sampler
  runs under the task and a disconnect deletes its rows as a set (#13); the spike's two exports
  eight days apart (#11); the task fires after a reboot with nobody signed in (#14); the plain-format export writes the
  owner's records and resolved events and leaves out the cache and live observations (Lane 9).
- M1 "done when" (roadmap): a week of real listening and watching is in the log with nothing
  typed, and the totals match what the owner remembers.
