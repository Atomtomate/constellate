Reviewed at 65e93951b0ee

**Verdict:** Changes needed. Two rules produce wrong totals as written: the repeat-play match and
the ISRC merge. Spotify re-sourcing only works when the export arrives last. The other three
findings are smaller gaps. There is no code yet, so each fix below is a rule restated now, plus
the test M1's ingestion must carry.

### 1. Nearest-first matching on `played_at` splits a repeated track into three plays

- `docs/02-domain-model.md:226`, `:230-232` (ADR-0003 `:64-65`): export and `recently-played` are
  paired by the smallest gap between `ts` and `played_at`. When `played_at` is the start (S26), the
  first export play's end falls exactly on the second play's start, so it takes the wrong partner.
- **Failure:** a 3-minute track played twice back to back, `played_at` the start: R1 12:00:00,
  R2 12:03:00; export E1 `ts` 12:03:00, E2 `ts` 12:06:00; window length + 1 min = 4 min. E1's
  nearest is R2 (0 s, against R1's 180 s), and E2 is then 6 min from R1, outside the window.
  Three events for two plays: {E1, R2}, {E2}, {R1}. R1 is "kept and counted" (`:389-391`), so the
  total gains an estimated play and an API record stays indefinitely. Global greedy matching picks
  the same pairs, and the poller and `recently-played` pair (`:227`) fails the same way when the
  later play is matched first.
- **Confidence:** certain, for the rules as written.
- **Fix:** within each URI, pair plays in order (the k-th play of a run with the k-th), not by
  nearest timestamp. Test: a track repeated back to back, with `played_at` at either end, gives
  two events.

### 2. The ISRC merge can only fire between URIs whose cache rows exist at the same time

- `docs/02-domain-model.md:276-282`, `:377-384`: a URI's ISRC is compared on arrival and then
  deleted, because "an ISRC not yet compared" is the only reason to keep the row, and every row goes
  at 30 days. A later URI with the same ISRC therefore has nothing to compare against.
- **Failure:** the backfill fetches URI A's ISRC in week 1, finds no match and deletes the row.
  Months later Spotify relinks the recording and the poller plays URI B (`linked_from` is gone,
  Spotify §4). B's ISRC arrives, A's is no longer cached, and B becomes a second item. The song's
  totals split, which is exactly the case the rule exists for. The backfill alone hits this:
  20,000 tracks at about 600 requests a day takes about five weeks (Spotify, brief finding 3),
  longer than a row lives.
- **Confidence:** certain.
- **Fix:** when an ISRC arrives, re-fetch the ISRCs of candidate items that share the owner-recorded
  title and album artist. Otherwise keep the ISRC as a durable merge key and add that reading to
  §8's terms questions. Test: a URI whose ISRC matches an item with a deleted row still merges.

### 3. Re-sourcing deletes API observations only when the export arrives second

- `docs/02-domain-model.md:386-388` (also `:247-249`, ADR-0003 `:80-81`): deletion fires "when an
  export observation joins an event". An API observation that joins an event already holding its
  export observation is never deleted.
- **Failure:** the poller's machine sleeps (ADR-0003 `:47`). Meanwhile the owner requests an export
  from a phone, and it can arrive within four hours (S4). On wake, the export is imported first. The
  next `recently-played` poll then returns up to 50 plays newer than its cursor, and some are older
  than the export's end. Each one joins its already-exported event and stays, so API data is kept
  indefinitely, against ADR-0003 `:120`. A late poller observation would also outrank the export's
  start (`:240`), against `:388-389`, which says the event's start rests on the owner's own record.
- **Confidence:** likely.
- **Fix:** make it an invariant of step 4, whatever the draft's source: an event with an export
  observation holds no Web API observation. Test both arrival orders.

### 4. The disconnect's one-transaction delete collides with atlas rows on an API-only item

- `docs/02-domain-model.md:397-399` against `:419-422`: a disconnect deletes "items left with
  nothing else", but atlas rows hold foreign keys to items.
- **Failure:** in M2, the poller sees a new track, whose item takes its title from the API
  (`:115-116`). The owner favourites it, then disconnects before the next export. Deleting the item
  can go three ways, and each breaks a stated rule:
  - the favourite's foreign key blocks it, aborting the delete the terms require within five days;
  - the delete cascades and removes the owner's own favourite;
  - the favourite counts as "something else", so the item and its API-sourced title outlive the
    disconnect.
- **Confidence:** likely.
- **Fix:** name the outcome, e.g. keep the item, with a placeholder title until an export names it.

### 5. With one transaction per draft, the `recently-played` cursor can skip plays after a crash

- `docs/02-domain-model.md:199`, `:208`, `:256-258`: transactions may be "per draft", and the cursor
  is a high-water mark (newest `played_at`, `:151`). "A crash re-reads rather than skips" therefore
  holds only if a poll's drafts are stored oldest first, and nothing says so.
- **Failure:** a poll returns R3, R2, R1. The run stores R3 first, which moves the cursor to R3's
  `played_at`, then crashes. The next poll asks for plays `after` R3, so R2 and R1 are never
  fetched. Unless the poller saw them, they stay missing until the next export, weeks later.
- **Confidence:** likely.
- **Fix:** use one transaction per poll for cursor sources, or store oldest first. Test: kill the
  run after its first draft, and the next run stores the rest.

### 6. Long-lived backups keep re-sourced API observations indefinitely

- `docs/02-domain-model.md:345-347`, `:399-401`: backups are handled for the cache (its own schema,
  left out of backups) and at a disconnect. API observations, though, live in `observation`, and
  every backup cut before re-sourcing still holds them.
- **Failure:** a monthly backup kept for a year holds each poller and `recently-played`
  observation, `context` included, a year after the export replaced it. ADR-0003 `:120` says
  "kept only until the export replaces them", the reading the amendment was made for.
- **Confidence:** likely.
- **Fix:** keep backups no longer than the export cadence, or state in §8 that backups are outside
  the rule, and why.

## Follow-ups

- `docs/02-domain-model.md` `:403-408` and the handoff cite the Spotify research at `3623499`.
  Its branch tip `ec00a85` now reads both Policy §III clauses as plausibly reaching the tracker
  and adds a path with no Spotify app. That paragraph should be re-read against the new tip.

## What carried it

Reading the Spotify research's §2 and §4 (`git show origin/claude/spotify-data-source:...`)
beside the model's matching table. S26's `played_at`, which may be either end of a play, is what
turned "nearest first" into a double count I could construct.
