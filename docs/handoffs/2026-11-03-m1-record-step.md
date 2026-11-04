# M1's record step: the owner's answers in the files that own them
**Summary:** The ten answers of 2026-10-19 and 2026-11-03 went into the files that own them, quoted from the ask results rather than a relay, with new ADR-0004 and dated revisions on ADR-0001, ADR-0002 and ADR-0003; four edits to the root `CLAUDE.md` were refused by the permission check and wait on the owner (#31).
**State:** Open — PR #27 waits for the coordinator's merge; the director then re-cuts, with #28 gating Lane 1, and #31 waits on the owner.

## What was done

Started 2026-11-03, finished 2026-11-04. Documents only, and nothing under `api/`, `web/` or
`docs/reviews/m1-plan/`. PR #27's body lists each answer and where it landed. Beyond the brief's
list, each because an answer made it false: ADR-0001's "in a PR of its own", `docs/00`'s multi-user
row, `docs/03`'s local-day zone, and two lines of `docs/01`. `docs/02` §2 also gained the item rank
that the plan's decision 9 sends to this step, marked as the specialists' reading.

## The owner's answers, as asked

Verbatim from the ask results in the coordinator's transcript, read at the source, because the
brief's and the issue comments' versions of the questions are condensed. "(Recommended)" is part of
the label; the two without it, the owner column and sign-in, went against the leaning. Seven are
quoted where they landed: the key type, the owner column and the import set in `docs/02` §8; the
null item in `docs/02` §1; Q-E in `docs/08`; sign-in in ADR-0004; the pointer bump in ADR-0001. No
other file holds the questions of these three, the first two because #31 waits:

- **2026-10-19.** "The digest asks you to confirm or correct what the coordinator has been doing on
  your 2026-10-05 words: merging ready PRs without your review, and answering trivial held questions
  itself after five days. Which is the rule from here?" Chose "Confirm: coordinator merges ready PRs
  (Recommended)": "Ready means the gates are met; you review on main by revert. Trivial held
  questions get the recommended option after a stated wait; real decisions are filed as issues with
  a leaning and wait for you."
- **2026-11-03.** "Branch protection on main, now the repository is public? The consolidation
  handoff's leaning: protect main, require the Record check, forbid force-push, no required approval
  so the coordinator can still merge." Chose "Protect as leaned (Recommended)": "I apply it now via
  gh: required status check Record, no force-pushes, no deletions, no required reviews. Nothing
  changes for the merge rule you confirmed."
- **2026-11-03.** "The digest's third recommendation: the status banners at the top of the root
  CLAUDE.md and the overlay restate status that docs/07's done markers and docs/08 already hold, and
  each went stale within a week. Drop them, or keep them?" Chose "Drop the banners (Recommended)":
  "The root CLAUDE.md and the overlay point at docs/07 and docs/08 for where the project stands; one
  home per fact, no instruction-file PR per milestone."

## How it was verified

- Each answer against the ask result in the coordinator's transcript, and the protection against
  `gh api repos/Atomtomate/constellate/branches/main/protection`: `record` required, no force-push,
  no deletion, no reviews, `enforce_admins` off.
- `check_docs.py` and the gates on every commit; CI on PR #27; the closing scripts in its report.

## Review pass

Four reports under `docs/reviews/m1-record-step/`, all at `da0e453`: tech six findings, direction
eight, parsimony two, architecture none. Each was checked at the file. The fold is five commits, and
PR #27's body says what each finding became.

## Dismissed

- Direction 5, tech's follow-up: the root's "a fleet definition, typically". A retro's "merge after"
  pair keeps it true.
- Direction 7: the root's `infra/` row, true while Q-E's other half is open; and a native service
  beside the development Docker server, since the ask's options put the sibling PC and "This dev
  machine" apart.
- Tech's follow-up on `scripts/pr_body.py`: it describes that same retro pair.
- Direction's follow-up on Lane 9's export in `docs/07`: a milestone's scope is not changed in
  passing, so it is the re-cut's, below.

## What remains open

- **#31, waiting on the owner:** four root `CLAUDE.md` edits, with their exact text, and whether to
  turn on `enforce_admins`.
- **#28 gates Lane 1:** which tables carry `owner_id`, and what it holds.
- **#30:** `reviews.py` reads the pointer as the record; stale `.py` docstrings go with it. The
  pointer trails the fleet by eight commits (its retro of 2026-10-16) and this close did not move
  it: its reports were already committed, so the move would have read as stale. The next close does.
- **#29:** the promotions from `raw`, on M2 as a leaning.
- **#20 and #21 stay open** for their done-whens' second halves. #20 gained two questions.
- **The director's re-cut, no issue:** `impl-director.md` still has the stateless cookie and no
  `owner_id`. Lane 9's line in `docs/07` and `spotify:show-name` in `docs/02` §3 are from its
  check-2.
- **The lanes', no issue:** `Owned`'s docstring (Lane 1); `api/src/constellate/CLAUDE.md`'s seam
  line (Lane 5).
- **The digest's, for the retro:** its first recommendation's mode swap, its second's sentence for
  `docs/CLAUDE.md`, and its part (b). The owner's answers did not reach them.

## Traps

- The root `CLAUDE.md` cannot be assumed editable from a lane:
  `docs/friction/2026-11-03-root-claude-md-edits-refused.md`.
- The pre-push gate can hang: `docs/friction/2026-11-03-pre-push-hung-on-fsmonitor.md`.

## What carried it

The ask results in the transcript. Reading them turned a relay into the owner's words, and each
option's own text named the files, which is what let the instruction-file edits rest on the owner.
