Reviewed at 659aee0c1fa1

**Verdict:** Mostly yes. The fold closes the first wave's three direction findings and writes its
two new rules into `docs/02` §2 before the code. Each rule stops one section short of the noun it
changes (the observation, the ingest run), and Lane 1, stacked on this PR, already builds there.

### 1. The observation now has an observed end, and `docs/02` §1 lists its fields without one
- **What** — Matching compares a *stored* play's `ended_at` with a draft's, but the Observation's
  field list and §7's decided-since sentence, which Lane 1 builds from, never name the column.
- **Where** — `api/src/constellate/domain/play.py:17-18`, `matching.py:72`, `:93`; against
  `docs/02-domain-model.md:116-118`, `:549-552` and the new draft row at `:211`;
  `docs/reviews/m1-plan/impl-director.md:150` ("exactly `docs/02` §7").
- **Why it matters** — The poller's observation is usually stored months before the export's
  draft (ADR-0003's Consequences), so the export–poller pair reads the poller's end from the row.
  Without the column every such play is two events, the double count tech's first-wave finding 1
  fixed. Lane 1's uncommitted tree (`C:\wt\constellate-lane-1`) already adds
  `observation.ended_at`: the schema follows a column the record does not hold.
- **Suggested resolution** — Doc, in this PR: `ended_at` in §1's Observation fields (on main's
  text from #33, which rewrote that sentence) and in §7's decided-since sentence. Then a Lane 2b
  `test_ingest.py` case pairing an export draft with a stored poller observation.

### 2. "Not marked ok" makes a run with a rejected record `failed` by elimination, unrecorded
- **What** — The rule says what such a run is not. The outcomes are `ok` and `failed`, so it is
  `failed`, a rolled-back run's value. §1's Ingest run lists no `rejected` count and states the
  hash check without a condition.
- **Where** — `api/src/constellate/domain/draft.py:163-167`; `docs/02-domain-model.md:217-222`,
  whose "(§4)" lands on the re-sourcing miss at `:442`, not the run; against `:181-188`,
  `:571-573`, `impl-backend-plan.md:57-58`; Lane 1's uncommitted `models/ingest.py:15-19`, `:37-41`.
- **Why it matters** — `failed` comes to mean both "rolled back" and "stored all but N". A poll
  that stored fifty scrobbles and rejected one stops being the "last successful poll per source"
  that `docs/adr/0002-the-stack.md:223-225` shows, though nothing failed. Lane 1 and 2b settle it
  by default. The first wave named `:185`; the fold stopped at §2.
- **Suggested resolution** — Record the outcome in §1's Ingest run first. Leaning: `ok` still
  means committed, `rejected` joins the counts at `:184-185`, and the hash check skips no run that
  rejected a record; then a 2b `test_ingest.py` case re-reading such a file. If `failed` is meant,
  say so at `:217-222`, with what it does to the health signal.

### 3. `precedence.py` still says a new source's place is there, but the map moved out
- **What** — The source-to-stream map now lives in `streams.py`. `precedence.py` still calls a
  new source "an adapter, a source row *and its place here*", and `stream_of` says "no place in
  the precedence orders".
- **Where** — `api/src/constellate/domain/precedence.py:3-5`, `streams.py:20-35`; against
  `docs/adr/0003-the-ingestion-seam.md:103`, "its place in the precedence order".
- **Why it matters** — The ADR's promise holds; its pointer does not. The next Google path joins a
  stream, so its whole place is one line of `_STREAM_OF_SOURCE`, outside `precedence.py`. A new
  stream needs a member, a rank in each order and maybe a window. The module names neither case.
- **Suggested resolution** — Code: a test that every `Stream` member ranks in `ITEM_ORDER` and
  `START_ORDER`, so a stream without its place fails. Then the sentence moves to `streams.py`,
  naming the map and the orders, and the message says the source has no stream.

**Decisions**
- Draft and `Play` carry `ended_at`; export and poller compare observed ends: recorded (§2).
- The observation stores `ended_at`: silent; `docs/02` §1 and §7 do not name it (1).
- A record that cannot become a draft is counted as rejected, the batch goes on, the run is not
  ok: recorded (§2). Which outcome that run gets, and what it does to the hash check: silent (2).
- U+0000 and NaN reject a record rather than being stripped: recorded (§2, "text the store cannot
  hold").
- No service on `ItemHint`; the adapter's one service goes to item, creators and event: recorded
  (`draft.py:8-10`; `docs/02` §1).
- `Stream` as an enum in `streams.py`, one `Play` for both rule sets: recorded (fold commit);
  where a new source now goes: silent (3).
- Item ties by the smallest id, compared as itself: recorded (`precedence.py`; PR body).
- The vocabulary guard is Lane 1's, its CHECKs built from the members: recorded (`vocab.py:3-5`),
  within the plan's "one source, a guard, either shape" (`impl-director.md:208-210`).
- `docs/01`'s matching is in order, never nearest first: recorded (ADR-0003, amendment 2).

**What carried it**
- Lane 1's uncommitted `models/ingest.py` (`RunOutcome`: `ok`, `failed`) read beside §2's new
  "not marked ok": the open wording is already being built as a value (finding 2).
