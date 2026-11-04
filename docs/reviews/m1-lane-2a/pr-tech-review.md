Reviewed at 659aee0c1fa1

**Verdict:** Fix before merge. The fold put the observed end on the draft but gave it no column in
the observation that stores it, so the export–poller pair it repairs still fails once the poller's
side is read back from the database. The same pause error is still in the export–Last.fm pair.

### 1. Medium: the observed end the fold adds has no column, so a stored poller play has none
- **file:line** `docs/02-domain-model.md:116-118`, `:626-636`: `ended_at` is on the draft (`:211`,
  `domain/draft.py:125`), but §1's Observation fields and §7's `create table observation` lack it.
  Lane 1's plan builds "§7's columns" (`docs/reviews/m1-plan/impl-database-plan.md:46`, `:88-89`).
- **Failure:** the poller's play is stored weeks before the export arrives, so at import the poller
  side of every pair is read from a row. With no end in the row it is `Play("spotify-poller", ...,
  ended_at=None)`, and `pair_in_order([Slot((it,))], [export], MatchWindows())` gives `(None,)` for
  every play, paused or not (run on the branch). A slot with no scrobble (every podcast episode)
  keeps the unmatched live observation (`docs/02` §4), so the play counts twice: the first wave's
  finding 1, now for unpaused plays too. The plan's candidate lookup ("some observation of it
  starts inside `within`", `:96-97`) compares starts, so it misses a paused poller play first.
- **Confidence:** certain that the record has no place for it; likely that Lane 1 builds without it.
- **Fix:** `ended_at timestamptz` in §7's observation and §1's fields, the END pairs' candidate
  window taken on `ended_at`. Then a 2b test pairs the export with a paused poller play read back.

### 2. Low: the export–Last.fm pair still compares the export's start, which a pause moves
- **file:line** `api/src/constellate/domain/matching.py:59-60` (`docs/02-domain-model.md:259`):
  ±1 min at `Moment.START`. The export's start is `ts − ms_played`, which is `ended_at −
  duration_ms`, the instant `draft.py:111-113` and `docs/02:211` now call wrong by any pause.
- **Failure:** the first wave's paused play (180 s from 12:00:00, `ts` 12:10:00) and a scrobble at
  12:00:00: `pair_in_order([Slot((scrobble,))], [export], MatchWindows())` gives `(None,)`, as does
  a 90 s pause (run on the branch). With the poller running, the export pairs through the poller's
  slot. Without it (offline plays, poller downtime, `docs/02` §4's "live tail without a Spotify
  app"), the unmatched scrobble is kept and the play counts twice: measured, then `to_end`.
- **Confidence:** certain about the behaviour; how often a pause runs past a minute, only the
  owner's data can say.
- **Fix:** a pause only moves the true start earlier, so let the window reach further before the
  export's start than after it, and add the paused play as its test.

## What carried it

Searching the repository for `ended_at` once the fold was read. Every hit was in the draft, the
play, the tests or §2's draft table, and none was in the observation or §7's DDL. That raised the
question of where the stored side's end comes from, and it led to finding 1.
