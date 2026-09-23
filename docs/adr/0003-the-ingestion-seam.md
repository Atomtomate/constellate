# ADR-0003 — The ingestion seam: one event per play, resolved from kept observations

- **Status:** Accepted
- **Date:** 2026-09-23
- **Accepted:** 2026-09-23, by the owner, over a last-writer-wins upsert

## Context

The stack ADR (`0002-the-stack.md`, option A accepted by the owner) fixes **one ingestion
path**: every adapter under `sources/` produces the same draft event, and one service persists
it. It leaves the draft's shape to Q-C, and names "how a polled play and an exported play are
recognised as the same play" as the thing that shapes the service's idempotency key. The domain
model, [`docs/02-domain-model.md`](../02-domain-model.md), answers Q-C. This ADR takes the one
part of it that is expensive to reverse and states it alone, so it can be argued alone. What
forced it, from the two data-source documents (`01-data-sources-spotify.md`,
`01-data-sources-youtube.md`, cited by section and source number):

- **Every source has two paths, and they see the same play differently.** Spotify has the
  extended-history export: it covers the account's lifetime, measures listened milliseconds, and
  stamps the time a play *ended*. It also has the Web API. `recently-played` holds only completed
  plays, has no listened time, and its `played_at` may be either end. The playback poller
  measures listened time to within its interval (Spotify §1, §2, §4). YouTube has Takeout and the
  Data Portability API, two paths to one store with the same records and no duration, and a
  possible browser extension that measures the seconds watched on desktop (YouTube §2, §3). One
  play can therefore arrive as three different records, with different times and different
  numbers.
- **The same record also arrives many times.** A re-requested Spotify export repeats every
  earlier play. Polls of `recently-played` overlap by design. Takeout on a schedule is a full
  archive every time, not a delta (YouTube §2).
- **The best number arrives last.** The poller's estimate is in the log the same day; the
  export's measurement comes weeks or months later (Spotify §1, S3, S6). Any rule that keeps the
  first record, or the latest one, is wrong for one of the two orders.
- **The item's length may not stand in the log.** YouTube's developer policies allow API data to
  be stored for 30 days at most (YouTube §4, S27). A duration "taken from the video's length"
  therefore cannot be copied onto a play. The play has to record *why* it has no measured number,
  and read the length from a cache when a total needs it.
- **Spotify's Web API data may not be kept indefinitely.** Spotify's Developer Terms forbid
  storing "Spotify Content" indefinitely, and that includes the listening events the poller
  captures. They also require an app to delete a user's data within five days of a disconnect,
  and they give no retention period (Spotify §6; S38 §IV, §V, Appendix A §5(c)). The export
  comes from the privacy page, not through the Platform, so its fields may probably be kept
  (Spotify §6, inferred there). A path with no Spotify app would take the live tail from
  Last.fm instead, whose scrobbles carry names but no URI (Spotify §6).
- **Parsers will be wrong at first, and inputs are slow to replace.** Takeout's title verb is
  localised (YouTube §2, S15). The export's `offline_timestamp` changed units (Spotify §1, S4).
  Whether `played_at` is a start or an end is undocumented (S26). A Spotify export takes up to a
  month to arrive.
- **The poller fires on a machine that sleeps**, as a one-shot command under the OS scheduler
  (the stack ADR). A run can crash halfway, and two runs can overlap.

## Decision

**Every source's record of a play is stored once, verbatim and never changed, as an
*observation*. The play is an *event* whose columns — item, start, duration and duration basis
— are resolved from its observations by a fixed precedence, so the best number wins whatever
order the records arrive in.**

In full:

- **A record delivered again is dropped by its `record_key`**, a unique identity taken from the
  upstream record, not from the path that delivered it. Takeout and the Data Portability API
  produce the same key for the same watch; a re-requested export produces the key its first copy
  had.
- **A record of a play already known joins that play's event.** A new observation attaches to the
  event it also sees: the same item ref within a time window set per pair of streams, one-to-one
  and in order (within one item, the k-th play in one stream pairs with the k-th in the other),
  and never two observations from one stream on one event. Where the two records share no ref —
  a Spotify track that was relinked, or a Last.fm scrobble, which names no URI — the match falls
  back to title, artist and time. If nothing matches, the observation starts a new event. The
  windows are parameters that are tuned on real data; they are not part of this decision.
- **Precedence resolves the event's columns.**
  - Duration: the export, then the extension, then the playback poller.
  - Start: the poller or the extension, which see it; then Takeout's or Portability's `time`,
    probably the start; then the export's `ts − ms_played`, wrong by any time the play was
    paused; last, `recently-played`'s `played_at`, which may be either end, and a scrobble's
    time.
  - Item: the item of the highest-ranked observation that names one.
  - Basis: `measured` if any observation measured the duration, `to_end` if one says the play
    reached its end, and `start_only` otherwise. The event never stores a length.
- **A source's cursor commits in the same transaction as the observations it covers.** A crash
  re-reads rather than skips, and the key makes re-reading harmless. The playback poller emits a
  play only when it closes, so an observation never changes after it is written.
- **Observations are deleted only with the ingest run that brought them**, to undo a bad import,
  **or where their source's terms require it** (`docs/02-domain-model.md` §4). Their events are
  then re-resolved from what remains, and an event left with no observation is deleted.

The draft's fields, the matching table and the tables themselves are in `docs/02-domain-model.md`
§2 and §7. They are the detail of this decision, not further decisions.

## Consequences

**What becomes easy.**

- Arrival order stops mattering. The export corrects the poller months later with no code of its
  own: its observation attaches, and precedence does the rest.
- A parser fix, a changed precedence or a tuned window is a recompute over stored observations,
  never a new export request.
- Totals read one row per play, from one table, with no duplicate logic in any query.
- Every number can say where it came from: the observation that supplied it, and that
  observation's ingest run.
- A crash and an overlapping run are both harmless.
- A new source is an adapter, a source row and its place in the precedence order. The event
  table does not change (`docs/02-domain-model.md` §6).

**What becomes hard.**

- **Events change after they are written.** A later observation can change an event's start or
  duration months afterwards. Nothing may snapshot a total or promise that an event's duration is
  final, and the API contract says so.
- **Matching is a heuristic and can be wrong.** A false match folds two plays into one and
  undercounts. A missed match leaves one play as two and double-counts. The windows are
  inferences until the owner's first weeks of data tune them. The ingest run's counts (new against
  matched) are the signal to watch.
- **Ingesting is more than inserting.** Each draft needs a lookup of candidate events. At
  hundreds of plays a day that costs nothing; the first backfill of a lifetime export is the slow
  case, and it runs once.
- **Two writers to one service could race** and create two events for one play. Ingestion takes a
  lock per service, so a Spotify export import and the Spotify poller run one after the other.
- **Every record is kept verbatim, for years**, and with it whatever personal data it carries,
  such as the export's `ip_addr`. The stack ADR's size estimate already allows for keeping raw
  records. Whether to strip fields on import is open in `docs/02-domain-model.md` §8.
- **Spotify's live plays are kept only until the export replaces them.** When the export
  re-sources an event, the poller's more exact start and its playlist context go with the deleted
  observation, and no later change of precedence can reach them. A disconnect deletes every Web
  API observation at once, and the plays since the last export return only when the next export
  arrives. The seam carries both because an event re-resolves from whatever observations remain.

*Amended 2026-09-23, after the owner accepted this ADR as proposed, and awaiting the owner's
confirmation.* The amendment makes three changes.

1. Spotify's Developer Terms (Spotify §6), which arrived with the acceptance, add the Context
   bullet on Spotify, the second reason to delete observations, and the bullet above. This is
   the change that needs the owner: it deletes records that no recompute can restore.
2. Matches pair in order, not nearest first. `played_at` may be a play's start, and nearest first
   then splits a track played twice back to back into three plays
   (`docs/reviews/domain-model/pr-tech-review.md`, finding 1).
3. The title, artist and time fallback now covers any two records that share no ref. A Last.fm
   scrobble needs it: the Spotify research's latest §6 names Last.fm as the live source for a
   path with no Spotify app.

None of the three changes the decision's sentence. The first narrows it.

**What is expensive to reverse.**

- **The split itself.** Every total, the timeline and the API contract read events resolved from
  observations. Going back to one row per record would rewrite all of them. No data would be
  lost, because the observations are a superset of what any other design keeps, but all the work
  built on the split would be.
- **The `record_key` scheme**, per adapter. A key too coarse silently drops a distinct record,
  which is then never stored; a key too fine turns one record into two events. Each adapter's key
  is tested on the owner's first real export before its first backfill.

**Item identity is not part of this decision.** The seam needs only that one item ref names one
item, and it works under any grouping of refs into items, because a merge or a split re-points
refs and re-resolves the affected events. The grouping is `docs/02-domain-model.md` §3's. The
owner chose no cross-service merging (2026-09-23). That needs no ADR of its own; it becomes a
standing constraint with Q-C's answer.

## Alternatives considered

- **One row per record, with duplicates flagged.** Every record becomes an event row, and a
  duplicate carries a flag or a pointer to the row that counts. The insert is simpler. It lost
  because the resolution this ADR does once moves into every reader: each total, each query and
  each client must filter by the flags. "The export wins" becomes flipping flags across rows
  whenever a better record arrives, and whether a row is a play or a copy of one depends on a
  flag that every consumer must remember.
- **An upsert where the last writer wins.** One row per play, and each new record overwrites its
  fields. It is the simplest possible. It lost because arrival order runs backwards for quality.
  A `recently-played` poll that lands after the export would overwrite a measured duration with
  none. The losing record's facts, such as the poller's playlist context and the extension's
  playback rate, are gone. (For Spotify's Web API, its terms now remove the poller's record once
  the export arrives. That is the amendment below, and the reason still holds for every source
  whose terms allow keeping its records.) Nothing records why a number is what it is. Its
  repaired form, *overwrite only when the new source ranks higher*, fixes the first fault but
  still discards the records that lost. A parser fix or a change of precedence would then need
  a re-import, and the Spotify export takes up to a month to arrive.
- **Deduplicate by key only, and count one stream per service.** For example, totals would read
  only the Spotify export. It needs no matching. It lost because the export is weeks to months
  late, which fails "a day's listening and watching is in the log by the next morning"
  ([`docs/00-vision-and-scope.md`](../00-vision-and-scope.md), success criteria).
