# Coordinator handoff: M0 closed, the scaffold merged, M1 planned and waiting on the owner
**Summary:** The coordinator session of 2026-09-23 to 2026-10-18 hands over with everything merged that could be without the owner — the scaffold, the consolidation, the fleet bump, the first digest and M1's plan round — and M1's code gated on nine decisions the owner has not answered.
**State:** Open — the next coordinator starts from the owner's answers; nothing codes before decisions 1, 6 and 8 of the M1 plan; the dev machine's Python is broken until the owner repairs it.

## Where things stand (2026-10-18)

- `main` is `25d1516`. Merged since the last coordinator handoff (#7): the fleet pointer bump
  #8 (pointer `3970c09`: specialists and the parsimony reviewer on Sonnet 5.5, the `qa`
  agent), the M0 consolidation #19, the scaffold #9 (`api/`, `web/`, the gates, the record),
  the scaffold's close #22, the first digest #24 (`docs/digests/2026-10-11.md`) and M1's
  plan-before-code round #25 (`docs/reviews/m1-plan/`). No PR is open but this handoff's.
- Issues: M1's #10 to #17, #20 and #21 on project 7; #18 and #23 on the agents board. The
  owner has commented on none; the one comment on #21 is the coordinator's.
- The owner was absent from 2026-10-06 to 2026-10-18 bar one word, "continue", on 10-11. On
  that word the coordinator answered two trivial held questions itself (two table rows, the
  `qa` roster sentence) and merged the ready PRs on the standing word of 10-05. The digest
  calls that word a paraphrase and asks the owner to confirm or correct it; its five
  recommendations are the retro's first list.

## Resume sequence

1. Get Python back (Traps, first bullet); nothing under `scripts/` or `api/` runs without it.
2. Read `docs/digests/2026-10-11.md`, then `docs/reviews/m1-plan/impl-director.md` as amended
   by `impl-director-check-2.md`, then the owner's answers wherever they arrive (issue
   comments, chat). Nothing below starts before the answers exist in the record: the standing
   constraint, and the plan's decision 9.
3. The plan's nine decisions, with the director's leanings in the PR body of #25: 1 the key type
   (#10), 2 sign-in (#20), 3 the import choices (#21), 4 the owner's inputs that close lanes,
   5 the #11 spike early, 6 Q-E's store half before Lane 1, 7 the owner column, 8 the null-item
   event with `event.service`'s record edits, 9 each answer written before its code. Decisions
   1, 6 and 8 gate Lane 1 and so the milestone.
4. With the answers: a record step first (docs/02 §7–§8, docs/03 for `CatalogueAdapter`,
   docs/08 for Q-E's store half, the ADR an answer may need), then Lane 2a (pure `domain/`,
   ungated) and Lane 1 (the schema) through `impl-director`'s hand-offs; the specialists' plans
   are in the same directory and name what each needs from the others.
5. Before a retro: the `manager` has run (#24); the `retro` runs on its list. The two
   unprocessed friction notes of 10-06 and the one of 10-11 are its queue.
6. Register the nightly worktree sweep (#18): seven merged worktrees under `C:\wt` sit past
   the sweep's one-day guard and `worktree_status.py --remove --fetch` clears them.

## Decisions the owner still owes beyond the plan's nine

Confirm or correct the coordinator's merging of ready PRs (digest, recommendation 2); the
status banners (recommendation 3); whether a pointer bump rides in a close commit
(recommendation 4); branch protection on `main` (#19's handoff carries the leaning); archiving
the finished sessions, which needs the owner's word per session.

## Sessions

All idle and finished: "Constellate: consolidation" (#19), "standby_session_5" (#8, #22,
#24), "Planning session standby" (#6), "Constellate: domain model" (#4), "Constellate: YouTube
data source" (#2), "Constellate: Spotify data source" (#3); "Standby session" and "Standby
session 6" never briefed. Any may be cleared on the owner's word. Names and ids come from the
`sessions` skill's table, never from memory; its dump is `.claude/sessions.json`, ignored.

## Traps met

- **After the 2026-10-18 restart the Microsoft Store Python cannot run**: its alias
  `python.exe` under `WindowsApps` fails with "cannot find the file" from Git Bash and
  PowerShell alike, the package's own binary refuses direct execution, and every venv made from
  it fails the same way, while `Get-AppxPackage` reports the package Ok. The hooks and every
  record script need it. Repairing an app execution alias or reinstalling Python 3.13 from the
  Store is the owner's; this handoff went in past the hooks (`--no-verify`) with CI's record
  workflow as the check, and the closing scripts did not run.
- The PC crashed twice on 2026-10-11 within an hour, both under the heaviest agent load the
  machine had carried, and once more before 10-18; nothing was lost because every step was
  committed. Fewer agents in parallel is the one knob on the session's side.
- A pre-push hook stalls on a record test's `git fetch` while another project's pushes run
  their hooks; stop that one fetch (the hook's python child's child) and the push proceeds.
- A `SendMessage` to a session mid-`AskUserQuestion` queues until the owner answers; a
  question held in a session does not survive their absence. File decisions as issues with
  the leaning instead.
- A quoted heredoc past a few kilobytes fails to parse in the Bash tool and nothing in the
  chained call runs, or silently alters an escape; the Write tool, then `--body-file`.
- A worktree made by `git worktree add` has no `api/.venv`; a brief must not say it does.
- A record-only PR's Review pass section must open with `Not run:` and a colon for
  `check_prs.py` to take the exemption; a plan-review report named `<reviewer>-plan.md` counts
  as a reviewer report to the scripts and must open `Reviewed at <sha>` with nothing after.
- `gh` hit a GraphQL rate limit once; `gh api rate_limit` says when it resets.

## What carried it

Workflows with a plan-compliance critic beside the command verifier; two review waves whose
reviewers converged from opposite sides; the plan round's second check reading each cited record
line rather than the reviewer's gloss; and the digest, which read the whole record and said
what no single session could see.
