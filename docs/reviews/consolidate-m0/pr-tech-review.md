Reviewed at 6e8c8a387ade

**Verdict:** Changes needed, all of them small. The two script fixes are correct and tested (339
tests pass; `check_docs.py` and `check_board.py --fetch` are consistent). Three derived copies say
something different from their source, though: a new standing constraint, a checklist line and
two scope lines. Also, an open handoff's State line is false once this branch merges.

### 1. The new standing constraint forbids the stand-in title that `docs/02` prescribes for every live play

- **`CLAUDE.md:139`**: "titles and names come from the owner's own records" is stated without
  exception. `docs/02-domain-model.md:114-118` allows one: "a Spotify track the Web API or
  Last.fm reported before any export named it carries that title until the export's replaces it".
  `:413-414` relies on the same exception.
- **Failure:** In M1 the export lags weeks to months, so every Spotify play captured live gets its
  item's title from a Last.fm scrobble or the poller (issue #12). The implementer reads the root
  file first and has to choose: leave every live item untitled until an export arrives, or break a
  constraint that "needs an ADR, not a commit". A reviewer holding the constraints reports the
  correct adapter as a violation.
- **Confidence:** likely
- **Fix:** Append the exception to the clause: "…, except that a live play titles its item until
  the export names it (`docs/02` §1)".

### 2. The reviewer checklist and issue #12 both leave out Last.fm's deletion on termination

- **`.claude/agents.local.md:162-166`**, `:178-182`: the deletion line lists what the terms
  require, but only the Web API's set and re-sourcing. The retention line gives Last.fm only "its
  100 MB cap, credited and linked". Last.fm's terms also "require deleting all Last.fm Data on
  termination" (`docs/01-data-sources-spotify.md:616`; `docs/02-domain-model.md:420-421`, `:440`).
- **Failure:** Issue #12, filed by this branch, repeats the same three terms and leaves out
  deletion. A `lastfm-scrobbles` adapter built to #12 therefore has no termination path, and it
  passes a review against this checklist. If the path were built, the line's "deleted only …"
  list would make it read as unlicensed.
- **Confidence:** likely
- **Fix:** Add "and Last.fm's, all of it, on termination" to the deletion list and to the
  retention line, and add the same sentence to #12's body.

### 3. `docs/00` and Q-D's answer make the extension unconditionally "later", and the source says that holds only if the spike passes

- **`docs/00-vision-and-scope.md:81`**, **`docs/08-open-questions.md:88`**: "Later, and only for
  the seconds watched on desktop: the history's other paths capture what and when without one".
  `docs/01-data-sources-youtube.md:325-334` conditions this on the Data Portability spike: "Fail:
  … freshness becomes the extension's job", and "the case for building it in M1 is stronger".
  This branch's own Q-F (`docs/08:32-34`) keeps the condition.
- **Failure:** If #11 fails, scheduled Takeout delivers "up to two months late" (`docs/01-…-youtube.md:191`).
  That fails 00's "by the next morning" criterion, and the out-of-scope row, which exists so
  "nobody quietly builds" what it lists, still rules the remedy out of v1. #11's done-when updates
  `docs/08` only, so `docs/00`'s row stays wrong.
- **Confidence:** likely
- **Fix:** Write "if the Data Portability spike (#11) passes" into both lines, or name
  `docs/00`'s row in #11's done-when.

### 4. The calendar handoff's State line becomes false when this branch merges

- **`docs/handoffs/2026-10-05-calendar-idea.md:3`**, `:41-42`, `:51`: it still asks the owner
  where the idea "sits in the roadmap", which this branch records as decided on 2026-10-06. It also
  says the root `CLAUDE.md`'s table "gains a `docs/ideas/` row in the consolidation PR", but this
  branch deliberately leaves that row out.
- **Failure:** After the merge, `record_index.py --open` and `open_work.py` show the next
  coordinator an open roadmap question that is already settled. They also report that the row
  promised here is in place, when nothing adds it.
- **Confidence:** certain
- **Fix:** Rewrite the State line: the roadmap place is decided (M3), the first three questions
  are still open, and the row waits on the owner (this branch's handoff, Needs a decision).

**Follow-ups**

- `scripts/check_prs.py:7`: the docstring still says GitHub "cannot enforce the rule on a private
  repository on the free plan". The repository is public, and the root `CLAUDE.md` now says so.

**What carried it**

Reading `docs/02-domain-model.md` §1 and §4 in full, not just the diff. Each derived line in the
checklist and the constraints was checked against the paragraph it condenses. Finding 1 turned up
at §1's "The one stand-in", and finding 2 at §4's Last.fm paragraph.
