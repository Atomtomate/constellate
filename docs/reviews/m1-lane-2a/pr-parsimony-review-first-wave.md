Reviewed at beb11317c061

**Verdict:** About right. Roughly 500 source lines and 450 of tests for the seam five adapters share, and nearly all of it is paid for by ADR-0003 or `docs/02-domain-model.md` §2; three small things are worth doing before Lane 2b builds on these shapes.

### 1. One observation, two value types
- **What** — `ObservationFacts` (`precedence.py:57`) and `Play` (`matching.py:72`) are the same stored observation as two pure functions read it: four fields are identical (`source`, `item_id`, `started_at`, `duration_ms`), and the branch's own test copies them across (`test_domain_matching.py:178`).
- **Why it recurs** — Lane 2b builds both from every stored row and every draft (`Play.from_draft` makes one; nothing makes the other), and each later rule that reads one more per-observation fact must pick a type to grow or grow both. The shared concept is "an observation as the domain sees it": the two differ in what they additionally read (basis versus names), not in why they change.
- **The smaller version** — one frozen `Play` holding `source`, `item_id`, `started_at`, `duration_ms`, `duration_basis`, `title=None`, `creator=None`; `resolve` takes `Iterable[Play]`; `from_draft` fills the basis from the draft; `ObservationFacts` goes. `Slot` and `Resolved` stay.
- **Net effect** — about 12 source lines (the class, its docstring, the per-test conversion) and 2b writes one row-to-value mapping instead of two. It is cheapest now, before 2b depends on both.

### 2. The choice among candidate slots is machinery no test observes
- **What** — `_meeting` (`matching.py:143`) returns the earliest instant a draft meets a slot, and `pair_in_order` keeps a `best = (meeting, s)` tuple (`:170-179`) to take the candidate with the earliest instant. On a scratch copy, swapping `<` for `>` at `:175` left all 53 domain tests green, and so did `min` for `max` in `_meeting` (the 17 matching tests). No test has two in-window candidates, so the code cannot be told from first-match or from latest-match.
- **Why it recurs** — it does not recur by itself, but pairing is what the first weeks of data tune (`docs/02` §2), and the next editor cannot tell which of these lines the "in order" rule rests on.
- **The smaller version** — `_meets(draft, slot, windows) -> bool` (an `any` over the slot's plays) and the first unclaimed, stream-free slot that `_meets` takes, via `next(...)`. The docstring already says "earliest unclaimed slot": state that slots arrive oldest first, which a span read ordered by `started_at` gives. A slot's resolved start and the instant compared can differ by minutes, so if order-independence is wanted the code stays and a test pins it (two in-window slots, listed newest first) instead; the author's call, but as written the lines carry no checked behaviour.
- **Net effect** — about 7 lines and the "meeting instant" concept; or, on the other path, one test that makes the existing lines load-bearing.

### 3. `resolve` is the one place that knows `EntityId` is a UUID
- **What** — ties between item ids go through `o.item_id.int` and `uuid.UUID(int=min(naming)[1])` (`precedence.py:103-105`, and `import uuid` at `:8`), though `vocab.py:11-13` promises that changing the key type "is one line", and decision 1's alternative is a bigint, where `.int` raises.
- **Why it recurs** — it does not; it is the single site that makes the one-line claim false.
- **The smaller version** — `naming = [(_rank(ITEM_ORDER, stream), o.item_id) ...]` and `item_id = min(naming)[1] if naming else None`. A `UUID` orders by its integer, so the result is identical (all precedence tests pass unchanged on a scratch copy).
- **Net effect** — 2 lines and the `uuid` import; flipping `EntityId` no longer touches `domain/` beyond `vocab.py`.

**What carried it:** mutating a scratch copy of `domain/` and running its tests, which turned finding 2 from a suspicion into a fact.
