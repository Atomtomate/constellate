# impl-director plan check — M1, round 2

*2026-10-11. Folding the two plan reviews (`pr-direction-review-plan.md`, nine findings + two
follow-ups; `pr-architecture-review-plan.md`, four findings + two follow-ups) into the plan of
record. Each finding verified against the file it cites before acting. `impl-director.md` is
amended in place, the amendments marked `[C2]`; lane plans are not edited here (changes they must
make are named below). `gh` not called (rate-limited).*

## Direction review — findings

1. **Q-E falls due inside M1 (host).** Verified: ADR-0002 Consequences makes the free SQLite switch
   cost nothing only *before the first migration*, and Lane 1 is it; `docs/07` done-when needs an
   unattended host; `docs/08` Q-E is "open until M1 needs it", on no list. **To the owner, decision
   6**, leaning the sibling's PC + Postgres-as-a-service; store half before Lane 1, the rest before
   Lane 8; a session/`infra/` host step added to the plan.
2. **Owner column from day one.** Verified: `docs/08` "Smaller, for later" and `docs/00`'s
   multi-user row ask it; the database plan parks it silently; the root `CLAUDE.md` makes it the
   owner's. **To the owner, decision 7**, leaning no column.
3. **`event.service` contradicts the record.** Verified: `docs/02` §1 ("a total per service reads
   the item's service") and §6 ("none of them names a service or a format"), ADR-0003's four
   resolved columns, overlay's "never written directly" — the C1 fold added only a §1 table row.
   And it *does* gate Lane 1 (it sets 0002's shape). **To the owner, decision 8**: null item +
   `event.service` with the record rewritten as a **Lane 1 precondition** (leaning), vs a
   placeholder item. Decision 3 corrected ("none blocks Lane 1" was wrong); Lane 1's `event.service`
   note re-pointed to decision 8.
4. **Answers folded with the code, not written first.** Verified against root `CLAUDE.md` ("an
   answered question in `docs/08` first, code second"). **To the owner, decision 9** (where each
   answer lands), and the plan now heads Lanes 1/3/4 with a record step.
5. **Leaning the lanes do not build.** Verified: backend plan skips `Streaming_History_Video_*`
   though the leaning imports everything, and "split by `header`" has no column/filter/step in M1.
   **Settled (director):** 4a stores video plays (null item, counted) not skip; the YouTube-Music
   split is dropped from M1 (`header` kept in `raw`); decision 3's leaning text corrected. Lane
   plan change: backend 4a un-skips the video file; 4b keeps `header` in `raw`, does not split.
6. **Plain-format export in no lane and not out of scope.** Verified: `docs/00` v1 criterion,
   `docs/02` §4 long-term copy, `docs/07` silent. **Settled (director):** added **Lane 9**, a
   `python -m constellate.export` command, gate Lane 1, no contract; session records it in `docs/07`.
7. **Lane 8 scheduled only the optional poller.** Verified: `docs/02` §4 daily refresh/delete,
   `docs/08` Q-E "with the daily jobs beside it". **Settled (director):** Lane 8 now schedules every
   unattended job and gates on 4c, not 4d; Lane 5 closes only once its refresh-and-delete is
   scheduled.
8. **Extension ruled out even on a failed spike.** Verified: `docs/00` defers it *conditionally*,
   `docs/01-data-sources-youtube.md` §6. **Settled (director):** "Not in scope" line made
   conditional on #11 passing; decision 5 extended to put Q-F / an amended done-when to the owner on
   a fail.
9. **`CatalogueAdapter` recorded nowhere.** Verified: backend plan 167-172; root `CLAUDE.md` /
   `docs/03` "one ingestion path". **Settled (director):** Lane 5 names it, placed in
   `services/sources.py` (see architecture 4); the session records in `docs/03` that a catalogue-only
   source has its own protocol and is not a second *log* write path (the log never depends on the
   cache, §4) — a clarification within ADR-0003's existing cache/log split, not a new decision.

## Architecture review — findings (all director-settled placements)

1. **Name-key equality still in SQL (`find_items_by_name`).** Verified: C1 removed the candidate
   twin but left this one; `docs/02` §2 makes name-key a tunable rule, SQLite `lower()` is
   ASCII-only. Lane 1/2 amended: the repo narrows by the resolved creator/album-artist link, a
   `domain/` function picks by `name_key(title)`. Lane plan change: database drops the casefold `=`,
   backend's step 3 calls the `domain/` matcher.
2. **Bucketing zone served from `/me`.** Verified: the zone shaped `/events` and `/totals` yet came
   from the session router, whose home moves with the sign-in scheme. Settled: the zone rides the
   **read responses** (one spelling), not `/me`; Lanes 3, 6, 7 and the contract section amended.
   Backend/frontend finalise the exact carrier.
3. **Local day had no owner.** Verified: buckets placed in `repos/`, `local_date` and date filters
   unplaced; `api/.../CLAUDE.md` §54 sends local day to `domain/` while ADR-0002 puts buckets in
   the DB. Settled: **one `repos/` helper** owns the local-day expression for buckets, `local_date`
   and filters; the §54 line is the session's to reconcile (follow-up).
4. **`/sources` read in the seam module.** Verified: `services/sources.py` would both declare
   `SourceAdapter` and import `repos/` for a status read. Settled: the read is
   `services/source_status.py`; `services/sources.py` stays the seam (`SourceAdapter`,
   `CatalogueAdapter`). Lane plan change: backend's Lane 6 module list.

## Follow-ups (verified, not plan steps)

- **Direction f/u 1 (codegen gap):** verified — no friction note exists and the overlay *already*
  tells the surface-changing lane to commit both files. Plan's "(friction filed)" / "owner should
  bless" claim **withdrawn** (R12b); no note warranted.
- **Direction f/u 2 (overlay Q-D line):** not reproduced — overlay line 42 already reads "after the
  Data Portability spike … Q-F", not "if Q-D calls for one". Nothing to do; the reviewer was stale.
- **Architecture f/u 1:** the `api/.../CLAUDE.md` §54 vs ADR-0002 tension — folded into
  architecture 3; the CLAUDE.md edit is the session's.
- **Architecture f/u 2:** 4d connect/disconnect have no door — settled as **commands** in M1 (not
  endpoints); plan amended.
- **`spotify:show-name` creator ref** (direction Decisions note): a record follow-up — `docs/02`
  §3's ref list should gain it when 4a lands. Nobody's lane here; flagged to the caller.

Nothing declined outright: findings are accepted (director) or deferred (owner) as above.

## Owner decisions, as they now stand (one message)

1. **Key type (#10).** Leaning UUIDv7, uniform. Before the migration (rewrites every FK after).
2. **Sign-in scheme.** Leaning a stateless signed HttpOnly cookie (no table). Stored sessions add a
   separate `0003_auth_session`, not blocking Lane 1.
3. **`docs/02` §8 imports.** Leaning: import everything (video plays stored, not skipped); strip
   `ip_addr`, keep `conn_country`; one configured zone; `header`/`incognito_mode` stay in `raw` so
   private-session and YouTube-Music-split totals ship unfiltered until a later migration (no split
   in M1). The null-item half is decision 8.
4. **Owner inputs** (verification only): #15 export, #16 Takeout, #12 Last.fm, #13 Spotify app, #11
   spike.
5. **Run the #11 spike early.** A fail puts Q-F (extension in M1) or an amended done-when to the
   owner.
6. **Host (Q-E).** Leaning the sibling's PC, Postgres a service. Store half before Lane 1; scheduler
   signed-out and encryption-at-rest before Lane 8.
7. **Owner column.** Leaning: no column (one user; `docs/00`/`docs/02` §8 defer it).
8. **Null item + `event.service`** (record rewritten as a Lane 1 precondition) vs placeholder item.
   Leaning: null item + `event.service`. Gates Lane 1.
9. **Where each answer is recorded, before its code.** Leaning: key-type + imports to `docs/02`
   §8 (+ close #10) before Lane 1; sign-in to a `docs/03` section (ADR if preferred) before Lane 3;
   item-precedence to `docs/02` §2. A sign-off, not a new choice.

## Lane order and gates, as they now stand

Settle decisions 1, 6 (store half), 8 before Lane 1; then the record step (decision 9), then
**Lane 1** (schema). **Lane 2a** (`domain/`, un-gated) and **Lane 3** (decision 2) run beside Lane
1; **Lane 2b** waits on Lane 1. **Lane 4** adapters gate on Lane 2 (backfill before live: 4a → 4b →
4c → 4d; 4e on the #11 spike). **Lane 6** gates on Lanes 1 + 3; **Lane 5** trails Lanes 1 + 2b and
closes only when its job is scheduled. **Lane 7**: W2 on Lane 3's contract, W3 on Lane 6's + W2.
**Lane 8** gates on 4c and schedules every unattended job; closes with Q-E (decision 6). **Lane 9**
(export) gates on Lane 1, before continuous reliance on the live tail.
