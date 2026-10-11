# M1: the plan-before-code round, with nine decisions for the owner
**Summary:** The director cut M1 into nine lanes with gates, the three specialists planned theirs and pushed back, the two plan-axis reviewers held the settled plan to the record, and the director folded all thirteen findings; nothing codes until the owner answers decisions one, six and eight, which gate the first migration.
**State:** Open — the owner answers the plan's nine decisions (issues #10, #20, #21 carry the first three); then Lane 2a and the record step can start, and Lane 1 once decisions 1, 6 and 8 are in.

## What was done

- `impl-director` planned M1 from the roadmap, `docs/02`, `docs/03`, the two data-source
  documents and issues #10 to #17, in the worktree `C:\wt\constellate-m1` on `claude/m1-plan`.
- `impl-database`, `impl-backend` and `impl-frontend` each planned their lanes against the cut
  (plans under `docs/reviews/m1-plan/`); the director's first check took fourteen pushbacks
  and declined three with reasons.
- `pr-direction-review` and `pr-architecture-review` reviewed the settled plan as a proposal;
  the director's second check verified each finding at the record line and folded every one
  or put it to the owner. The round is PR #25's content.
- Decisions the round surfaced that the first plan had not: Q-E's store half is due before the
  first migration; the owner column is an open `docs/08` item the schema would settle by
  omission; the null-item leaning needs `event.service`, which the record as written forbids.

## Verified

`python scripts/check_docs.py` on the branch (80 files); the plan reviews ran
`scripts/check_layering.py` on the scaffold (22 modules, clean). No code was written.

## What remains open

- The owner's nine decisions, listed with leanings in the PR body and in
  `docs/reviews/m1-plan/impl-director.md`; #10, #20 and #21 carry the first three.
- Round two between database and backend on the candidate span read's exact signature, and the
  two field names backend and frontend must agree before the contract commits
  (`impl-director-check-1.md`, unresolved).
- A new worktree carries no `api/.venv`; each API lane makes one first (`api/CLAUDE.md`,
  "Running it"), and a brief must not say it exists (the round's friction note).
- `docs/02` §3's creator-ref list gains `spotify:show-name` when Lane 4a lands.

## Needs a decision

The nine, in the PR body. The three that gate Lane 1 and so the milestone: the key type
(#10), Q-E's store half, and the null-item event with `event.service`'s record edits.

## Traps met

- A reviewer's brief that fixes the report's first line must match `scripts/reviews.py`'s
  `Reviewed at <sha>` pattern exactly; a parenthetical after the sha fails `check_docs.py`.
- A plan-review report named `<reviewer>-plan.md` counts as a reviewer report to the scripts,
  by prefix; it is held to the cap and the first line like any other.

## What carried it

Reading each cited record line rather than the reviewer's gloss, in both director checks: the
line in `docs/02` §6 that says no resolved column names a service is what made `event.service`
the owner's decision rather than the director's convenience.
