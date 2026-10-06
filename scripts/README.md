# `scripts/` — the closing step's checks

Repo-wide tooling for the closing step (`.claude/agents/CLAUDE.md`, "Finishing a task")
and for the `retro` (`.claude/agents/retro.md`), which runs them once to know the state of
the record. Each script here is a check that step **runs rather than re-derives by
reading** — a question with a countable answer, answered the same way every run — or a
listing it reads instead of assembling by hand, the rows whose Exit says it lists or prints.
The modules here that are not scripts are imported by the scripts and import none of them,
and no script imports another: that is the whole layering, and a shared thing goes in a
module of its own beside them rather than into a script — `reviews.py` (the reviewer
roster, the report's shape and where the pass stands), `git_cmd.py` (the one place a
*script* here spawns git, with the caller's `GIT_*` names dropped so `cwd` decides which
repository answers; `tests/` keeps its own, needing an author identity), `mode.py` (the
run's mode, read once), `pr_body.py` (what a PR body declares about other work),
`record.py` (the handoff and friction header contract), `report.py` (how a check ends),
`trunk.py` (which ref stands for `main`) and `gh_json.py` (every `gh` command the scripts
send, written once).

These scripts and their tests were copied from the owner's board-game tracker on
2026-09-23 (ADR-0001 names the commit), with that project's product checks left out. A fix
to one copy is carried to the other by hand until `docs/08-open-questions.md`'s "Smaller,
for later" decides whether the generic half moves into the fleet repository.

What lives here obeys three rules:

- **Stdlib-only Python**, run on a bare interpreter. No venv, nothing installed —
  `pathlib`, `re`, `json`, `subprocess`, `argparse`.
- **Report, never fix.** A script prints what is inconsistent, in a form a person or an
  agent can act on, and exits non-zero. Repairing the record is the closing step's; a script
  that silently repaired it would be worse than the reading it replaced. The line is the
  record and the working tree: a script changes neither. **The one exception is
  `worktree_status.py --remove`**, which deletes merged worktrees and the husks a
  half-finished removal leaves behind — only behind the flag, and only where the record
  survives without them. Refreshing `origin/main` under `--fetch` (`trunk.refresh`) is on
  the reading side of that line. How a check ends — the notices it will not fail on, then
  each finding under its prefix, then a count or a `consistent` line, then the exit
  status — is `report.py`'s, written once so no script drifts in how it reports; a run that
  could not happen at all ends through `report.abort` instead, which is not a finding.
  Those two are a script's only ways out with 1, and `scripts/tests/test_report.py` fails
  one that leaves `main` any other way, or whose Exit column below disagrees with which of
  them it calls — that column is machine-read, so its two openings are load-bearing.
- Anything that needs `gh` takes its JSON from files, so it can be tested on a saved
  snapshot, or fetches it with `--fetch` — except `review_briefs.py`, which asks the PR's
  base, `hook_stop.py`, which asks for the branch's open PR at every turn end and reads no
  answer as no PR, and `close_report.py`, which has nothing to say without the open PRs and
  so fetches them unless given a file. `gh` is on PATH on the dev machine; the scripts look
  there first and then at its Windows install path (`gh_json.py`).

| Script | Answers | Exit |
|--------|---------|------|
| `check_memory.py` | Does every memory note have one line in `MEMORY.md`, does every line name a file that exists, does every `[[wikilink]]` resolve, does each note's frontmatter `name` match its filename? Reads the memory directory outside the repository that `DEFAULT_DIR` names. | 1 on a finding |
| `check_docs.py` | Does every relative Markdown link (and `#anchor`) resolve; does every `ADR-NNNN` mention name a file; does each ADR's Status line agree with `docs/adr/README.md`; is every `Q-<letter>` in `docs/08-open-questions.md` spent once, open or answered; does every handoff and friction note carry the header its contract fixes; does neither README hold a table row; does a handoff whose State claims to be open name a branch git has already merged; is every review report that opens `Reviewed at <sha>` within the cap `reviews.py` states, and every handoff dated from `record.HANDOFF_CAP_FROM` within `record.HANDOFF_CAP` lines; does every digest carry its `**Covers:**`/`**Supersedes:**` header and stay within `record.DIGEST_CAP`; does every file under `docs/investigations/` that states a `**Status:**` say it is *parked*? | 1 on a finding |
| `check_layering.py` | Do imports under `api/src/constellate/` follow the layers `docs/03-architecture.md` states — `api/` → `services/` → `repos/` → `models/`, `domain/` importing none of them, `sources/` reached only through the interface `services/` declares and importing only `domain/` and the leaves, `main.py` and `poll.py` entry points nothing imports; does SQL stay in `repos/` but for the readiness probe's `select 1`; does only `logging_config.py` configure logging? Which modules outside the layers count as leaves is derived from what reaches them, not listed — its docstring says how. | 1 on a violation; an `allowed:` line is a sanctioned exception and does not fail the run |
| `check_board.py` | Is every open issue on the board its label puts it on and no other — project 7 with a roadmap milestone, or project 8 with the `agents` label and none; is every closed issue's board item in Done and no Done item still open; are the GitHub milestones exactly the roadmap's (`## M… —` headings in `docs/07`); does a roadmap milestone marked done still have open issues? | 1 on a finding |
| `worktree_status.py` | For every git worktree: is its tree clean or does it hold uncommitted or untracked work, how far has its branch drifted from its upstream, and does `main` already hold its HEAD (`on main`, else `ahead N of main`)? Is each worktree's `core.hooksPath` one of this clone's own `.githooks` — the relative form the root `CLAUDE.md` asks for, or the absolute one the desktop app writes into the worktrees it creates — so `.githooks/post-checkout` populates the agent-fleet submodule there? A session runs it with `--current` to confirm its own worktree is clean before it declares done — the nearest worktree holding cwd — mechanically, not in prose; the retro runs it with `--remove` to audit every worktree, where clean plus `on main` is the removal candidate. Under `--remove` it deletes that candidate rather than naming it, and sweeps `.claude/worktrees/` for the leftovers git no longer lists; with `--merged FILE` or `--fetch` it reclaims a branch whose PR was squash-merged, which only GitHub can vouch for. A worktree git will not read at all is `UNREADABLE`, never `clean`. | 1 when an in-scope tree has uncommitted or untracked work or git cannot read it — except under `--unattended`, where uncommitted work is reported and not gated because that run owns none of those trees; 1 when `--current` is given from outside every listed worktree; 1 when a worktree removal `--remove` decided on failed. Printed and not gated: a leftover directory that will not delete; unpushed commits; a `core.hooksPath` finding; the `main` column |
| `check_prs.py` | Is every open PR that is not a draft actually ready by the root `CLAUDE.md`'s working-agreement rule: a "Review pass" section in its body that is neither empty nor a placeholder, the four reviewers' reports under `docs/reviews/<branch>/` among its changed files unless that section says the pass was not run and why, no commit since those reports that changes more than Markdown (under `--fetch`), a base of `main`, and no "merge after #N" naming a PR still open? And, over the 200 most recently merged PRs, has every one merged into a branch other than `main` reached `main` since? A "merge after" naming another repository — `<owner>/<repo>#N` — is resolved by asking that repository under `--fetch`. It also prints, without failing on it, which ready PR is standing on the rule's own exemption and the reason it gives. | 1 on a finding; a notice is printed, never counted |
| `open_work.py` | Lists the open work the record names — the newest digest, how far the `.claude/agents` pointer is behind the fleet's `main` (refreshed under `--fetch`), unfolded handoffs' "What remains open", the friction notes in `docs/friction/` whose `**Retro:**` header is still `Unprocessed` and the ones git holds off `main`, `docs/08`'s "Smaller, for later", the next roadmap milestones' bullets — next to the open issue titles, so matching them is done once over one screen; and the open PRs, each with the issues it closes and any handoff, friction note or review report it carries; and which two open PRs change a file in common, so the merge order is decided rather than discovered. | always 0; it lists |
| `close_report.py` | What the session is leaving open, as the block it ends with: every open PR, one line each, with what it waits on — a `Blocked: <reason>` its body states, a "merge after" still open, a base that is not the trunk, a pass still owed, or the owner. Fixed columns and one line counting them, so the close neither forgets what is standing nor retypes it as prose. `check_prs.py` gates the PRs that are *not* drafts; every one here was outside it. | always 0; it prints — 1 only when `gh` will not list the open PRs |
| `record_index.py` | Prints the handoff and friction indexes, from the `**Summary:**`/`**State:**` or `**Agent:**`/`**Summary:**`/`**Retro:**` header `record.py` reads out of each file rather than a stored table — `[handoffs\|friction\|all]`, oldest first, `--open` for just the ones still active. | always 0; it prints |
| `failure_ledger.py` | Prints, since a named handoff or digest (`--since`; default the newest `*-retro*.md`), the half of `retro.md`'s hand-read list that this repo's files and git hold: the digests added since, each with its Recommendations; that handoff's "Predictions" and "Needs a decision"; every handoff since with its "Review pass", "Not verified", "Traps", "Known, not fixed", "Dismissed" and "What carried it" sections in full; every friction note since with the verdict on its `**Retro:**` line; every review report since with its verdict, finding headings, length and the commit it names; every commit since titled "Act on … review"; every PR merged into `main` since with the lines it added by kind; and the record files added since and deleted again. "Since" is git's, not the calendar's. | always 0; it prints — 1 only when the cut handoff cannot be found |
| `review_briefs.py` | Prints the four reviewers' briefs for a branch from the only things a brief may carry — the branch and PR, the worktree and its head, the PR's base (asked of `gh`, or `--base`), one paragraph on what the branch is, the diff measured against `origin/<base>`, what the caller reports, the report path the overlay's rule derives, the report's shape and cap (`reviews.py`), and the owner's remedy order, code before test before check before prose. `--since SHA` briefs a second wave over the commits after the head the first wave read. The axis stays the definition's. The one thing here that is not a check. | always 0; it prints, or writes `--out DIR/<agent>.md` — 1 only when `gh` cannot say what the PR is based on and no `--base` was given |
| `gates.py` | Which areas does this change touch — `record`, the whole tree; `api`; `web`; `infra` — and do the checks their CI workflows would run pass here first? `--staged` asks it of a commit, `--branch` of what the branch changes against the merge base; `--quick` keeps to the checks fast enough for every commit. `AREAS` holds each area's trigger paths in GitHub's own spelling, and `scripts/tests/test_gates.py` fails when a workflow's `paths:` and that list disagree, or when a local check's command is not on a `run:` line of its workflow — so the hook and the build cannot drift apart on what a change needs checked. A check whose toolchain is not installed here is a notice, not a finding; what CI alone runs — the Alembic checks, which need a live database — is named on the result line (`Area.ci_only`). | 1 on a failing check |
| `hook_stop.py` | Runs from the `Stop` hook in `.claude/settings.json`, after every reply: blocks the stop, once, when a handoff, friction note or digest sits in the tree and in no commit, when `check_docs.py` fails, when the branch has commits after its review reports that change more than Markdown (the pass is stale), when an open PR on the branch has no pass and no "Not run" reason, or — in a worktree whose `constellate.mode` is `unattended` — when the branch has code and no pass at all; a report of the pass in the tree and in no commit is a pass in flight, which it does not block. A dirty tree as such is `worktree_status.py --current`'s to gate at the close, not this hook's. | always 0; a block is JSON on stdout |
| `hook_session_start.py` | Runs from the `SessionStart` hook on a new or cleared session: prints the worktree's mode, every worktree's state, the handoffs still open and `open_work.py --fetch` into the session's context, so drift one session left is seen at the next start rather than at a retro. Without `gh`, the record half alone. | always 0 |

**`check_docs.py` and `check_layering.py` also run in CI**, in
[`.github/workflows/record.yml`](../.github/workflows/record.yml), beside the scripts' own
tests; neither needs `gh`, a token or a database. All three run *before* CI too, from
`.githooks/pre-commit` by way of `gates.py` — which is the point of the pair.
`check_memory.py` and `check_board.py` cannot go there at all and are the closing step's
alone: `check_memory.py` reads memory notes that live outside the repository, and
`check_board.py` reads two user-level project boards, which the workflow's own token cannot
see.

Run from the repository root, in this order:

```
python scripts/check_prs.py --fetch
python scripts/check_memory.py
python scripts/check_docs.py
python scripts/check_layering.py
python -m unittest discover scripts/tests
python scripts/worktree_status.py --current --remove   # the closing gate, and the sweep
python scripts/check_board.py --fetch
python scripts/open_work.py --fetch
python scripts/record_index.py all
python scripts/failure_ledger.py          # the retro's inputs since the last retro
python scripts/close_report.py            # last: the block the session ends its reply with
python scripts/review_briefs.py --branch <branch> --pr <n> --worktree <path> --what what.md [--known known.md]
```

`check_prs.py` goes first because its `--fetch` refreshes `origin/main` (`trunk.refresh`;
`open_work.py --fetch` does the same, later in the list). `check_docs.py` has no `--fetch` —
CI runs it on a fresh checkout and it needs no network — so it reads the ref as it finds it,
and against a stale one goes lenient without saying so; running it after a refresher is what
keeps a local answer honest. `worktree_status.py` is in the same position for the same
reason, and `--remove` is the one run that cannot live with a stale reading and refreshes the
ref itself. Which ref stands for `main` — `origin/main` when git has it — is `trunk.py`'s.

**`--remove` can also run unattended, nightly**, as a Windows scheduled task, so a worktree
can disappear overnight with no session involved — the sessions that strand worktrees are
the ones that never reach a close. It is **not registered on this machine yet**; it earns
its place once worktrees exist. Registering it is the one step that lives on the machine
rather than in the repository, so it is written out here — it must pass `--fetch`, without
which the squash-merged worktrees, most of what there is to sweep, are left behind:

```
schtasks /create /tn constellate-worktree-sweep /sc daily /st 04:00 /f /tr "python <repo>\scripts\worktree_status.py --remove --unattended --fetch"
```

`check_board.py` also accepts `--issues`, `--board`, `--agents-board` and `--milestones`
files, `check_prs.py` a `--prs` file (always needed without `--fetch`) plus a `--merged`
file for the merged-PR check, and `open_work.py` `--issues` and `--prs` files, holding the
output of

```
gh issue list --repo Atomtomate/constellate --state all --limit 200 --json number,title,state,milestone,url,labels
gh project item-list 7 --owner Atomtomate --format json --limit 200
gh project item-list 8 --owner Atomtomate --format json --limit 200
gh api "repos/Atomtomate/constellate/milestones?state=all"
gh pr list --repo Atomtomate/constellate --state open --limit 200 --json number,title,headRefName,baseRefName,isDraft,body,url,files,closingIssuesReferences
gh pr list --repo Atomtomate/constellate --state merged --limit 200 --json number,title,baseRefName,headRefName,headRefOid,mergeCommit,url
```

## Driving the boards

Two user-level projects, both linked to the repository, each with a `Status` field of
`Todo`, `In Progress` and `Done`: **project 7, "Constellate"**, for product work, and
**project 8, "Constellate agents"**, for the agent setup and the `CLAUDE.md` files — an
issue belongs there when it carries the `agents` label, and takes no milestone, because
the milestones are the product roadmap's.

```
gh project item-add <7|8> --owner Atomtomate --url <issue url>
gh project item-list <7|8> --owner Atomtomate --format json --limit 200     # item ids
gh project item-delete <7|8> --owner Atomtomate --id <item id>
gh project view <7|8> --owner Atomtomate --format json                      # the project's node id
gh project field-list <7|8> --owner Atomtomate --format json                # Status field and option ids
gh project item-edit --project-id <node id> --id <item id> --field-id <Status field id> --single-select-option-id <option id>
```

Closing an issue on GitHub moves its item to Done through the project's own workflow;
In Progress is set by hand with `item-edit`. `item-add` returns before `item-list` shows
the item, so a check run straight after an add can report the issue off the board; run it
again. GitHub milestones mirror the roadmap's headings; create a missing one rather than
filing without. If `gh` reports a missing `project` scope, `gh auth refresh -s project`
restores it, and until then the board half of a close cannot run: say so in the handoff and
do the rest.
