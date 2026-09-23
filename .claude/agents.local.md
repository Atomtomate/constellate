# `agents.local.md` — this repository's answers to the generic fleet

The agents in `.claude/agents/` are a **generic fleet**, shared across repositories and
carrying no knowledge of this project (ADR-0001). This file is where that knowledge lives
instead: a generic definition reads `../agents.local.md` for anything specific to *this*
repo, so the fleet stays reusable and this repo keeps control of its own facts. It is a
sibling of the submodule (`.claude/agents/`) and of the per-agent memory
(`.claude/agent-memory/`, created when its first entry is earned), by one rule — knowledge
goes where its subject is.

Where a fact already has a home in this repo, this file **points at it** rather than
copying it; a rule stated twice is a rule that will eventually contradict itself. What is
stated here in full is what has no other home — the file-ownership map and the board
numbers.

**This project is at M0: no code, no stack, no schema.** Several sections below therefore
say *not yet* rather than answer, and name the question in
[`docs/08-open-questions.md`](../docs/08-open-questions.md) that will answer them. An agent
that finds one of those sections empty reports it, as its definition says, rather than
inventing the answer.

## Modes

| Mode | Declared by | What it expects of the session |
|------|-------------|--------------------------------|
| attended | nothing; the default | The owner is in the loop: a decision only they can take is asked, with a leaning, and the turn waits. |
| unattended | `git config --worktree constellate.mode unattended` in the lane's worktree (this clone has `extensions.worktreeConfig` on) | Nobody will say continue: the turn does not end with the review pass unrun, a decision only the owner can take is filed as an issue rather than waited on, and `scripts/hook_stop.py` enforces the first of those. |

`scripts/mode.py` reads the key for both hooks; anything but `unattended` is attended.

## File ownership (the implementation specialists)

**Not yet.** The map is written by the PR that accepts the stack ADR (Q-B), because the
paths are the stack's. Until it exists:

| Agent | Owns | Never touches |
|-------|------|---------------|
| `impl-database` | *(no ground yet)* | — |
| `impl-backend` | *(no ground yet)* | — |
| `impl-frontend` | *(no ground yet)* | — |

`impl-director`, asked to cut implementation work before this table is filled, reports
that the task cannot be cut along an ownership map that does not exist — that is a finding
about the task, per its definition — and names Q-B as what blocks it. Record work (docs,
scripts, this overlay, the `CLAUDE.md` files) needs no specialist and is done from the
session.

## The contract, and the order

**Not yet.** The fleet's build order is schema → API and contract → clients; whether this
project has an API contract at all, and of what kind, is the stack ADR's (Q-B). When it
does, this section names the contract file and the command that regenerates it.

## Layers, architecture, and the standard

**Not yet.** No layer document and no layering check exist. `pr-architecture-review` runs
the check its definition names only where this overlay names one; here it says so in its
report and reads the imports itself, per its definition. The first architecture document is
`docs/03-architecture.md`, written with the stack ADR.

## Project docs and record

Where the written direction lives, for the agents that read it — chiefly `impl-director`
and `pr-direction-review`:

- Vision and scope, with the out-of-scope table:
  [`docs/00-vision-and-scope.md`](../docs/00-vision-and-scope.md).
- Roadmap and milestones — what each contains and what is deferred:
  [`docs/07-roadmap.md`](../docs/07-roadmap.md).
- Open questions not yet decided: [`docs/08-open-questions.md`](../docs/08-open-questions.md).
- Decisions: [`docs/adr/`](../docs/adr/), each with a Status (Accepted / Proposed /
  Superseded / Parked).
- Parked research, off the roadmap and not to influence a design decision until unparked:
  [`docs/investigations/`](../docs/investigations/).
- The domain model: `docs/02-domain-model.md`, **not yet written** (Q-C).
- What is in flight — open PRs with the record files they carry, handoff items still open,
  friction notes unprocessed: `python scripts/open_work.py --fetch`
  ([`scripts/README.md`](../scripts/README.md)). The director reads it for what shares the
  request's files or issues; every session sees it at start through the hook there.

**When the diff is work on the agent setup itself** — this overlay, a `CLAUDE.md`, the
scripts under `scripts/` — the product docs are silent on it; its direction is the agents
board below, the fleet's `.claude/agents/CLAUDE.md`, and ADR-0001.

The friction and handoff channels (`docs/friction/`, `docs/handoffs/`) are the fleet's own
conventions; the fleet `CLAUDE.md` states them, and each directory's README states its
header contract.

**Record index.** The index of either directory is derived, not stored —
[`docs/handoffs/README.md`](../docs/handoffs/README.md) and
[`docs/friction/README.md`](../docs/friction/README.md) state each one's contract; this
overlay owns only who writes which line. The closing step writes a handoff's header and
edits no table; folding one rewrites its own `**State:**` to `Folded YYYY-MM-DD — …` naming
where its content and open items went. The retro processing a friction note rewrites that
note's own `**Retro:**` line — and so does a session that acts on a note at the owner's
direction. `python scripts/record_index.py [handoffs|friction|all] [--open]` prints the
index on demand.

## Review reports

PR readiness is the root [`CLAUDE.md`](../CLAUDE.md#working-agreement)'s rule; here it
means `gh pr create --draft` when a brief says "open the PR", and `gh pr ready <n>` from
the session once the pass below is folded and its reports are committed — or, while the
PR's base has not merged, `gh pr edit <n> --add-label reviewable`, and `gh pr ready <n>`
once it has.

A reviewer's brief is `python scripts/review_briefs.py`'s output, never freehand; what a
brief may carry — the head it was written at, the diff measured, the report's shape and
cap — is that script's to fix, and `scripts/README.md`'s row for it is the fuller
statement. An agent told to write its report to a file (fleet `CLAUDE.md`, "Every agent has
its own context" — which owns the rule that the path is the agent's own working tree, and
that the caller carries the file onto a branch checked out elsewhere) writes it to
`docs/reviews/<branch>/<agent>.md`, `<branch>` being the branch name with a leading
`claude/` dropped, the spelling `scripts/reviews.py` derives. Plain Markdown naming files
in backticks, never as links, since `scripts/check_docs.py` walks `docs/` and a relative
link that does not resolve fails CI; its first line and its cap are the brief's, and
`check_docs.py` holds it to them. The reports are committed after the fold or with it,
never before; a commit after them that changes more than Markdown is work the pass never
saw, and the PR is a draft until a second wave has seen it. A second wave over a change the
first never saw is briefed `--since` the head the first read; the earlier report is renamed
`<agent>-<ordinal>-wave.md` before the next runs, because `failure_ledger.py` reads the
tree and not the history.

**The retro's ledger.** `python scripts/failure_ledger.py` prints, since the last retro
handoff, the half of `retro.md`'s "Read first" list that this repo's files and git hold. A
retro's predictions are a numbered list under a heading named exactly `Predictions`, and a
review report's verdict line and `### N.` headings are what the script reads from it.

## Domain invariants the reviewers enforce

**None decided.** The root [`CLAUDE.md`](../CLAUDE.md#standing-constraints)'s standing
constraints hold none about the product yet; the domain model (Q-C) produces the first,
and the reviewer-facing checklist is written here when it does. Until then a reviewer holds
a change against [`docs/00-vision-and-scope.md`](../docs/00-vision-and-scope.md)'s scope
and non-goals alone.

## The boards

- **Product work** → GitHub **project 7** ("Constellate"), with a roadmap milestone.
- **Agent-setup work** → GitHub **project 8** ("Constellate agents"), label `agents`, no
  milestone.

`check_board.py` enforces the split. `gh` is on PATH on the dev machine (root
[`CLAUDE.md`](../CLAUDE.md#environment-gotchas)); the closing-step board rules are the
fleet's to state, and the commands that drive both boards are `scripts/README.md`'s
"Driving the boards".

## Toolchain

- The record scripts under `scripts/` are stdlib Python on a bare interpreter — Python 3.13
  on the dev machine and in CI. No venv exists yet.
- The product toolchain is the stack ADR's (Q-B). Until then the only test command is
  `python -m unittest discover scripts/tests`, and there is no linter.

## The running stack (for `ops`)

**There is no rig.** Nothing is deployed, `infra/stack.py` does not exist, and the three
facts the `ops` definition reads back from here — the main checkout to run stack commands
from, the rig's milestone, the test login — have no values. `ops` has nothing to operate
until M1 needs a public URL (Q-E); invoked before then it should say so and stop.

- **Main checkout** — `C:\Users\Atomt\Documents\favorites_tracker`, for when there is
  something to run from it.
- **The rig's milestone** — none.
- **Test login** — none.
