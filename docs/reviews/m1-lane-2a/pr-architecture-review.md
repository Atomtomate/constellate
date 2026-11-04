Reviewed at 659aee0c1fa1

**Verdict:** The fold carried all three first-wave findings and undid none. `ItemHint.service` is
gone, `domain/streams.py` holds the stream vocabulary both rule modules import, and `precedence.py`
no longer imports `uuid`. `python scripts/check_layering.py` is clean (28 modules, exit 0). Two
placements the fold introduced are wrong: the observed end has no holder once a play is stored,
and the merged `Play` brought the draft, and matching's choice of creator, into precedence's input.

### 1. The observed end is on the draft and on `Play`, but nothing that stores a play holds it
- **`api/src/constellate/domain/matching.py:95`**: `_instant(stored, Moment.END)` reads `ended_at`
  off a stored play. Its observation has no place for the value, so Lane 2b can get it only from
  `raw`.
- **The crossing**: `stored.ended_at` is `Play.ended_at` (`play.py:26`), filled only by
  `from_draft` from `DraftEvent.ended_at` (`draft.py:125`). The observation's fields
  (`docs/02-domain-model.md:116-118`) and table (`:626-637`) have no `ended_at`. So 2b's
  row-to-`Play` mapping either passes None, and the export–poller pair never meets, or it reads the
  export's `ts` and the poller's closing sample out of each source's own `raw` shape.
- **The rule**: `docs/03-architecture.md:102-103`, "A source knows an external API or a file
  format". If `services/` parses a source's `raw`, that knowledge crosses the seam. A fact that
  pairing reads back belongs on the observation, "the ground truth" (`docs/02:113`).
- **The fix**: an `ended_at timestamptz` column on `observation`, written from the draft and read
  back into `Play`. This adds a column to Lane 1's schema and model, the same one that
  `pr-tech-review` and `pr-direction-review` ask for.

### 2. The draft-to-play conversion put matching's creator choice into the type precedence reads
- **`api/src/constellate/domain/play.py:6`**, `:36-45`: the merged `Play` imports `DraftEvent` for
  `from_draft`, which holds the name fallback's choice of creator. So `precedence.py` now loads
  the draft through its input type, and the choice exists only for a draft.
- **The crossing**: `precedence.py:12` → `play.py:6` → `draft.py`. At `beb1131`, precedence
  imported only `vocab`, and the choice sat in `matching.py`. It sorts `CreatorHint`s (`:41-45`).
  `same_play` (`matching.py:77-90`) compares what it yields, and a `Slot`'s stored plays need the
  same choice made over the span read's item creators, which are not hints.
- **The rule**: the M1 plan puts "the same-play comparison (ref, or title+album-artist name-key)"
  in `domain/matching.py` (`docs/reviews/m1-plan/impl-director.md:170-173`). Bound to a draft,
  the choice leaves 2b's mapping in `services/` to write the stored half again. Precedence, a
  recompute over stored rows, also ends up knowing the adapter's output.
- **The fix**: move the conversion into `matching.py`, with the creator choice as a function over
  a creator's role, position and name that both the conversion and 2b's mapping call. `play.py`
  then imports only `streams` and `vocab`. This adds a function.

**Follow-ups**

- `api/src/constellate/domain/streams.py:20-27` repeats each source key as a literal beside
  `SourceAdapter.key: str` (`services/sources.py:26`). This predates the fold, which only moved
  it. With Lane 4a's first adapter, add a test that every adapter's `key` has a stream.

**What carried it**

Following `stored.ended_at` from `matching.py:95` out of the diff to what a stored `Play` is
filled from: `docs/02`'s observation fields and table, where it has no holder.
