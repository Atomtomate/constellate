# Fleet pointer bump: c01588d to a1c04fa, Atomtomate/agents#18 to #21
**Summary:** Moved the `.claude/agents` submodule to the fleet's merge of Atomtomate/agents#21 in PR #8; nothing outside the submodule needed editing, and the fleet's #22, merged after the target, is not carried.
**State:** Open — PR #8 waits for the coordinator's merge; the next pointer bump carries Atomtomate/agents#22.

## What was done

- `.claude/agents` from `c01588d` to `a1c04fa`: eighteen commits, Atomtomate/agents#18 to #21.
  What each PR changed is in the commit message and PR #8's body.
- Checked the overlay, the root `CLAUDE.md`, `docs/CLAUDE.md`, the rest of the record and the
  scripts for anything the fleet diff makes stale. Nothing is: no file here names
  `memory/README.md`, the manual's "Subagent" section or Sonnet 4.6; `## Subagent` is the only
  heading the fleet lost, and nothing here linked or quoted it; the two anchors the record links
  into the manual resolve; no script depends on the plan-report names #18 and #21 dropped; the
  overlay's `.claude/agent-memory/` stays true, `ops.json` being the fleet's one memory file.
- No overlay edit, so the merge order of the two open branches that edit it is unaffected.

## How it was verified

- `python scripts/check_docs.py`: consistent, 42 Markdown files. `python -m unittest discover
  scripts/tests`: 338 tests, OK. The pre-commit and pre-push gates passed.
- The headings of the fleet's `CLAUDE.md`, `README.md`, `ops.md`, `retro.md` and both plan
  reviewers diffed between `c01588d` and `a1c04fa`; then a grep of everything outside the
  submodule for the removed names, the old model pin and the plan-report file names.
- The closing scripts, from the worktree: `check_prs.py --fetch`, `check_memory.py` and
  `worktree_status.py --current` consistent; `check_board.py --fetch` and `open_work.py --fetch`
  as under "What remains open".

## What remains open

- **Atomtomate/agents#22** (`3970c09`, the 2026-10-06 retro and a new `qa` agent) merged on the
  fleet's `main` after this target; `open_work.py` reports the pointer three commits behind. Its
  bump makes the root `CLAUDE.md`'s roster stale ("Four agents are entry points", "The other
  seven"), since `qa` is a twelfth agent. `qa` reads the overlay for how the product runs, which
  "The running stack" answers for now with "There is no rig".
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
  is not scoped to the current worktree. `.claude/worktrees/planning-session-standby-08cfb5`,
  another session's, is clean and on `main`; only the 24-hour idle guard keeps it (last touched
  eleven hours ago). A lane told to leave other worktrees alone runs `--current` without
  `--remove`.
- The fleet's `main` moved between the brief and the bump. A brief that names its target commit
  stays right; check the fleet's `origin/main` anyway, and name what is not carried.

## What carried it

The brief named the target commit, the three files to check and that the overlay's merge order
matters, so the staleness question had a cost attached before it was asked. The heading diff
between the two fleet commits turned "does any anchor here break?" into one command.
