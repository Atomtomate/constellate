Reviewed at 659aee0c1fa1

**Verdict:** About right, and lighter than the first wave found it: the fold took first-wave findings 1 and 3 whole (one `Play`, no `uuid` arithmetic, `ItemHint.service` gone) and pinned finding 2's slot choice with a test that fails when `<` becomes `>`. What it added (`ended_at`, `rejected`, the NUL walk, `streams.py`) is paid for by `docs/02` §2 and the first wave's correctness findings. Two small residues of the merge and the pin remain.

### 1. `resolve` keeps a `(play, stream)` pair list beside `Play.stream`
- **What** — `precedence.py:59` builds `seen = [(o, stream_of(o.source)) ...]` and unpacks the pair in four comprehensions (`:64`, `:68`, `:73`, `:76`), while `Play.stream` (`play.py:31`) is the same lookup. The pair existed because `ObservationFacts` had no stream; the merge into one `Play` removed the reason and left the shape.
- **Why it recurs** — the next rule `resolve` or Lane 2b's recompute adds reads a stream, and has two spellings to pick from: the pair, or the property `matching.py` already uses.
- **The smaller version** — `seen = list(observations)`, `o.stream` in the comprehensions, and `stream_of` leaves `precedence.py`'s imports. On a scratch copy all 64 domain tests pass, including the unknown-source one, which still raises from the property.
- **Net effect** — zero lines (the file is 83 either way); one import and one tuple shape go, and the module has one way to ask a play its stream.

### 2. Residue of first-wave finding 2: the slot-index tie never decides, and `min` inside a slot is unpinned
- **What** — `pair_in_order` compares `(meeting, s) < best` (`matching.py:130`), but `s` only grows through the loop, so on equal meeting instants the held best already has the smaller index: `meeting < best[0]` is the same rule. Separately `_meeting`'s `min(meets)` (`:108`) is not observed: `max` there leaves all 64 domain tests green, because the new `test_the_earliest_meeting_slot_wins_...` uses one-play slots. Both on a scratch copy; the `<` to `>` swap now fails that test, so the cross-slot choice is pinned.
- **Why it recurs** — it does not; the windows are what the first weeks of data tune, and this is the line an editor changes then.
- **The smaller version** — compare on the instant alone (`best: tuple[datetime, int]`, `meeting < best[0]`), and give the test one slot holding two meeting plays, as `test_a_draft_pairs_with_a_slot_through_any_one_of_its_plays` already builds, set against a slot of one.
- **Net effect** — about zero lines and one tie rule fewer to reason about; the within-slot `min` stops being a free choice.

**What carried it:** mutating a scratch copy of `domain/` and re-running its tests, as in the first wave: it showed the fold's new test kills `<` to `>` but not the index tie or `max`, and that finding 1's smaller form passes unchanged.
