Reviewed at 6e8c8a387ade

**Verdict:** Slightly heavy, and in prose, not code: the two script fixes are as small as they can be. The weight is the same decisions written out in three to six documents, which this diff has already let drift.

### 1. The capture paths are written out in full in `docs/00`, `docs/07` and `docs/08`, and the copies already disagree

- **What** — Spotify's and YouTube's path lists appear at `docs/00-vision-and-scope.md:59-67`, `docs/07-roadmap.md:46-52` and in Q-D's Answered entry (`docs/08-open-questions.md:78-90`). The extension's "later" is a fourth and fifth copy (`docs/00:81`, Q-F at `docs/08:28-34`) and "never depends on the poller" a sixth (overlay checklist, `.claude/agents.local.md:175`). Q-D calls Last.fm "the backbone", `docs/00` and `docs/07` "the live tail". `docs/00` and Q-D defer the extension unconditionally, and Q-F conditions it on the spike: first-wave tech #3 and direction #1 are this drift, reported from two sides.
- **Why it recurs** — Yes. Spike #11 flips YouTube's daily capture and needs an edit in five places. Every later source (the calendar's feeds, Q-G) gets the same triple of scope, roadmap and answer.
- **The smaller version** — Q-D's entry, which `docs/CLAUDE.md` makes the decision's dated home, keeps the one list of paths and says who chose each. That is also the one place to fix direction #1's missing YouTube attribution. `docs/00` keeps the fields captured, then "by the paths Q-D chose; the log never depends on the poller". `docs/07`'s two M1 bullets name the deliverable and cite Q-D.
- **Net effect** — about 12 lines. The spike's outcome becomes one edit, and nothing has to be reconciled.

### 2. The reviewer checklist copies the root constraints it already binds reviewers to, and `docs/02` §4's figures

- **What** — `.claude/agents.local.md:170-174` restates `CLAUDE.md:137-143` almost word for word and cites the root as its source, though `:153` already makes a reviewer hold every standing constraint. `:162-165` and `:178-182` carry `docs/02` §4's figures (five days, 30 days, 100 MB), which `docs/02`, ADR-0003 and Q-E hold too. These two bullets are where the first wave found the copy out of step with its source (tech #2, direction #4).
- **Why it recurs** — Yes. The section's rule is "a change to one updates its line here in the same PR", a sync that no script checks. Each new standing constraint or terms change adds a line to keep in step. The overlay's own opening (`:11-12`) says it points rather than copies.
- **The smaller version** — The "derived copy" is argued (a reviewer wants a condensed list), but that covers what only the checklist carries (`:159-169`, `:175-177`). Drop `:170-174`. Cut the deletion and retention bullets to the invariant plus a pointer: "retention and deletion follow each service's terms as `docs/02` §4's table has them", with no figures. The remedy is prose because no script can compare condensed prose with its source; deleting the copy removes the obligation instead of adding a check. Tech #2's fix adds a clause to the surface this removes.
- **Net effect** — about 9 lines, and the next terms change is one edit in `docs/02`.

### 3. Both banners state project status that `docs/07` and `docs/08` already hold, and the scaffold PR is rewriting one now

- **What** — `CLAUDE.md:10-14` (M0 closed, M1 under way, "the scaffold is M1's first PR", the open questions as a list) and `.claude/agents.local.md:16-22` (M0 done, "a file that arrives with the scaffold PR", the one section still *not yet*) are status, which the roadmap's done markers and `docs/08`'s "Still open" own.
- **Why it recurs** — Yes, at every milestone and every answered question. This diff exists because the old "The project is at M0" went false six days earlier. `origin/claude/scaffold` rewrites the overlay's paragraph and its "arrives with the scaffold PR" sentences again, and the handoff expects conflicts there. Q-E's answer is next.
- **The smaller version** — The scaffold branch's overlay wording is already status-free ("A section that still says *not yet* names the question that will answer it"); take it. The root banner points: where the project stands is `docs/07`'s done markers, and what is undecided is `docs/08`'s "Still open". It loses a cold agent's orientation by one hop, and that is the sentence that rots. The owner approved a banner here, not this wording, so this is for the owner's call.
- **Net effect** — about 3 lines, and no instruction-file edit at the next milestone.

**What carried it**

`git diff origin/main...origin/claude/scaffold -- CLAUDE.md .claude/agents.local.md`: it showed the banner already being rewritten and gave the status-free wording for finding 3.
