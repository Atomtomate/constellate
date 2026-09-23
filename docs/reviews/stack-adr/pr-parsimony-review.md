Reviewed at b3aeb20eb0c2

**Verdict:** Somewhat heavier than the work it does. None of the extra weight is in the decision
itself. It is in how the decision was carried into the record: the project's state and
ADR-0002's rules are each written at several sites, and two sets of those copies already
disagree on the day they were written. About 40 lines can go, and after that a transition or a
new constraint touches one place instead of several.

### 1. "Arrives with the scaffold PR" is written at about fifteen sites, not once per file
- **What** — the overlay's banner (`.claude/agents.local.md:16-18`) says pending files are named
  as arriving, then each site says so again: `:37-38`, `:71-72`, `:78-79`, `:80-81`, `:83`,
  `:178`, `:181-182`. So does `docs/03-architecture.md:97-100` under its banner at `:5`, and
  `CLAUDE.md:10` and `:53`.
- **Why it recurs** — every arrival leaves markers the next PR must hunt down: the scaffold,
  `web/`, `extension/` if Q-D needs it, Q-C's invariants, Q-E's rig. "With the stack ADR" still
  survives at `scripts/gates.py:12`, `scripts/README.md:61`, `CLAUDE.md:102`, `docs/CLAUDE.md:10`:
  direction findings 3 and 4 found those stale lines, and this pattern is what produces them.
- **The smaller version** — each file gets one line naming what is absent until the scaffold
  merges, and every section states its target in the present tense. A check can carry the
  staleness half: `scripts/check_docs.py` failing when a path on that line exists would have
  counted all four survivors. The other half, dropping the copies, is a deletion, so it is prose.
- **Net effect** — about 8 lines. A transition edits one line per file instead of fifteen sites.

### 2. ADR-0002's structural rules are stated in three living files, and the copies disagree
- **What** — `CLAUDE.md:125-133` states four constraints. `docs/03-architecture.md:48-69` says
  they are the root's, then restates them as "three rules". The overlay restates the contract
  rule (`.claude/agents.local.md:65-67`, "Regenerate" again at `:70`), says "three seams" at `:77`
  and lists four at `:156-158`. The copies disagree on "TypeScript" (`CLAUDE.md:132` against
  `docs/03:67-69`, direction finding 1's lines) and on whether there are three rules or four.
- **Why it recurs** — PR #4's ingestion-seam ADR (`docs/adr/0003-the-ingestion-seam.md:148`)
  says item identity "becomes a standing constraint with Q-C's answer": by this pattern, thrice.
- **The smaller version** — the root holds the rules, with its two contract bullets merged into
  one ("the committed contract is the only path to data"), making three. `docs/03`'s seams point
  there and keep only what the root does not say: no page one import from the database,
  idempotent ingestion, who owns the draft's fields and the key. Its one-language paragraph goes.
  The overlay keeps the file and the command, and drops its list.
- **Net effect** — about 11 lines. A constraint is added or fixed in one file, so the TypeScript
  fix happens once and cannot reopen.

### 3. The overlay restates three rules the fleet's definitions own
- **What** — `.claude/agents.local.md:35-36` (split by files so two can run at once) is
  `.claude/agents/CLAUDE.md:162-163`. `:68-69` (the build order) is
  `.claude/agents/impl-director.md:25-32`, which the previous overlay credited to the fleet.
  `:81-82` (the reviewer reads the imports itself) is
  `.claude/agents/pr-architecture-review.md:59-60`, cited "per its definition" and then restated.
- **Why it recurs** — a definition changes in `Atomtomate/agents` and reaches this repo as a
  pointer bump that nothing compares with the overlay, so the copy here drifts without anyone
  noticing. The overlay is also modelled on the sibling's, so the next consuming repo inherits
  the copies. The overlay's own `:11-12` rules this out.
- **The smaller version** — delete the three sentences. At most, keep "the fleet's build order
  holds" under the section heading.
- **Net effect** — about 5 lines. A change to a fleet rule is then one edit, in the fleet.

### 4. ADR-0002 keeps its acceptance to-do list and a verbatim copy of the map it moved
- **What** — `docs/adr/0002-the-stack.md:227-232` lists the accepting PR's work, which this PR
  has done. The rest is the handoff's (`docs/handoffs/2026-09-23-stack-adr-draft.md:45-49`), and
  the two disagree (direction finding 3's lines). The appendix table `:277-281` is identical to
  `.claude/agents.local.md:40-44`, `:283-285` repeats `:59-61` and `:294-298` restates `:46-57`.
  The overlay calls itself the map's only home (`:13-14`) and says "the map is ADR-0002's" (`:36`).
- **Why it recurs** — it does not: PR #4's ingestion-seam ADR has neither. Raised for size, and
  because the next map change (`extension/`, after Q-D) goes in the overlay while `:36` sends
  readers to the ADR's frozen copy.
- **The smaller version** — delete `:227-232`: deleting beats direction's rewrite, because the
  handoff already holds the rest. The appendix keeps `:287-292` (the argument for `sources/` and
  `poll.py`) and the gates table (no other home until the scaffold). One line replaces the rest:
  "moved to the overlay's File ownership on acceptance". `:36` reads "decided by".
- **Net effect** — about 18 lines. One copy of the map, one owner, and no to-do list in the ADR.

**Follow-ups**
- `.claude/agents.local.md:46-57`: the two partition rules are copied from the sibling's overlay
  (`docs/adr/0002-the-stack.md:294-296`). Two copies is below the bar for abstracting. If a third
  consuming repo copies them, they belong in the fleet's `impl-director.md`.

**What carried it**
- A tree-wide grep for "arrive(s) with", "until it" and "once the", run to test whether finding 1
  recurs. It turned up the founding PR's four surviving markers, which direction's report had
  found one at a time as stale lines.
