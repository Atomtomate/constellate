# Fleet pointer bump: c01588d to 3970c09, Atomtomate/agents#18 to #22
**Summary:** Moved the `.claude/agents` submodule to the fleet's head, the merge of Atomtomate/agents#22, in PR #8; one sentence here goes stale with it, the root `CLAUDE.md`'s count of the agents a session reaches, which the scaffold PR #9 fixes at its rebase.
**State:** Folded 2026-10-11 — PR #8 merged; the root `CLAUDE.md`'s agent count landed in the scaffold PR (#9), which counts `qa`; the board's M5 finding cleared when the consolidation PR (#19) put M5 in `docs/07`; the mode-default note is recorded as not worth an issue, the manual and the overlay agreeing as read.

## What was done

Started 2026-10-06, finished 2026-10-11.

- `.claude/agents` from `c01588d` to `3970c09`, the fleet's head: twenty-one commits,
  Atomtomate/agents#18 to #22, in two commits here. `a707f3a` goes to `a1c04fa` (#18 to #21),
  the brief's first target; `6ef1bf2` goes on to `3970c09` (#22) at the coordinator's direction
  of 2026-10-06. What each PR changed is in those messages and PR #8's body. The first message's
  "agents#22 ... is not carried" was true when written, and the second says it no longer holds.
- Checked the overlay, the root `CLAUDE.md`, `docs/CLAUDE.md`, the rest of the record and the
  scripts against both ranges. One sentence goes stale: the root `CLAUDE.md`'s "The other seven
  are reachable", which `qa` makes eight. Nothing else: no file here names `memory/README.md`, the
  manual's "Subagent" section or Sonnet 4.6; `## Subagent` is the only heading the fleet lost,
  and nothing here linked or quoted it; the two anchors the record links into the manual resolve;
  no script depends on the plan-report names #18 and #21 dropped; the overlay's
  `.claude/agent-memory/` stays true, and its "running stack" already answers what `qa` reads.
- The root `CLAUDE.md` sentence is not edited here. The coordinator asked for the edit, and this
  session does not change a `CLAUDE.md` at another session's request without the owner's word.
  The owner was asked in this session on 2026-10-06; the question went unanswered and did not
  survive the session's restart. On 2026-10-11 the coordinator moved the fix to the scaffold PR
  (#9), which edits that file anyway.
- No overlay edit, so the merge order of the open branches that edit it is unaffected. PR #8 and
  PR #9 share no file.

## How it was verified

- The pre-commit and pre-push gates passed on every commit, and CI on every push.
- The headings of the fleet's changed definitions diffed across each range, then a grep of
  everything outside the submodule for the removed names, the old model pins, the plan-report
  file names and the agent roster's counts.
- The closing scripts, on 2026-10-11: `check_prs.py --fetch`, `check_memory.py`,
  `check_docs.py` (43 files), the scripts' tests (338, OK) and `worktree_status.py --current`
  consistent; `open_work.py --fetch` says the pointer holds the fleet's `origin/main`;
  `check_board.py --fetch` as below; `failure_ledger.py` has no retro handoff to read since,
  there having been no retro yet.

## What remains open

- **The root `CLAUDE.md`'s agent count.** "Four agents are entry points ... The other seven are
  reachable" is stale from this bump: `qa` is the eighth reachable agent, run after a milestone or
  when the owner asks and never per PR, its findings reaching the board through the calling
  session's close. The scaffold PR (#9) carries the fix at its rebase.
- **The mode default.** The manual now says "Unattended is the standing mode whenever the owner
  is not steering" (agents#18, the owner's decision of 2026-09-14). The overlay's Modes table
  calls attended "the default", declared by nothing. Read together they agree: the manual says
  when to declare unattended, the overlay how. But a delegated lane like this one runs attended
  unless its brief says otherwise. Whether the overlay should say that a delegated lane declares
  unattended is the coordinator's call, and not edited here.
- **`check_board.py --fetch`: "GitHub milestone M5 is not in the roadmap".** This predates the
  lane: the owner's renumbering of 2026-10-06 (calendar M3, constellations M4, apps M5) reaches
  `docs/07` in the consolidation PR, which owns that file.

No issue filed for any of them: the brief scoped this lane to the bump and its report, and the
coordinator places them.

## Traps

- `scripts/README.md`'s closing order runs `worktree_status.py --current --remove`, and the sweep
  is not scoped to the current worktree. On 2026-10-11 it would delete
  `.claude/worktrees/planning-session-standby-08cfb5`, another session's: clean, on `main`, and
  idle 142 hours, past the 24-hour guard that kept it on 2026-10-06. A lane told to leave other
  worktrees alone runs `--current` without `--remove`.
- `git restore` runs `.githooks/post-checkout`, a file checkout being a checkout, and its
  `git submodule update --init` resets a submodule moved but not yet staged to the commit the
  index records. Stage the pointer before any `restore`, or check `git submodule status` after.
- A target that changes after the first push becomes a second commit: folding it into the first
  means a force-push, which this session's permission check refuses. Check the fleet's
  `origin/main` before the first push, not after.

## What carried it

The brief named the target commit, the files to check and that the overlay's merge order
matters, so the staleness question had a cost attached before it was asked. The heading diff
between the fleet commits turned "does any anchor here break?" into one command per range.
