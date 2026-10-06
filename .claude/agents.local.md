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

**The stack is decided (ADR-0002) and laid out by the scaffold.** The sections it decides —
file ownership, the contract, the layers, the toolchain — are filled below and name what
exists. A section that still says *not yet* names the question in
[`docs/08-open-questions.md`](../docs/08-open-questions.md) that will answer it; an agent
that finds one of those empty reports it, as its definition says, rather than inventing the
answer.

## Modes

| Mode | Declared by | What it expects of the session |
|------|-------------|--------------------------------|
| attended | nothing; the default | The owner is in the loop: a decision only they can take is asked, with a leaning, and the turn waits. |
| unattended | `git config --worktree constellate.mode unattended` in the lane's worktree (this clone has `extensions.worktreeConfig` on) | Nobody will say continue: the turn does not end with the review pass unrun, a decision only the owner can take is filed as an issue rather than waited on, and `scripts/hook_stop.py` enforces the first of those. |

`scripts/mode.py` reads the key for both hooks; anything but `unattended` is attended.

## File ownership (the implementation specialists)

The map was decided by ADR-0002, and this is its only living copy. The line between database and
backend is SQL: `repos/` is the only module that knows it. `<pkg>` is `api/src/constellate/`.

| Agent | Owns | Never touches |
|-------|------|---------------|
| `impl-database` | `<pkg>/models/`, `<pkg>/repos/`, `<pkg>/db.py`, `api/alembic/`, and their tests under `api/tests/` | routers, services, sources, the contract |
| `impl-backend` | `<pkg>/api/`, `<pkg>/services/`, `<pkg>/domain/`, `<pkg>/sources/`, `<pkg>/main.py`, `<pkg>/poll.py`, `api/openapi.json`, `api/scripts/`, and their tests under `api/tests/` | migrations, SQL |
| `impl-frontend` | `web/`, and `extension/` if Q-D calls for one | anything under `api/` |

**A module these rows do not name belongs to the agent whose layer imports it** — to the lower
one where both do, which is the direction the layering already runs — **and a module nothing
imports is an entry point, and `impl-backend`'s**, an importer run as a command included. The
rows name only the modules the scaffold starts with, so the next one added does not need this
table edited to have an owner. `config.py` and `api/pyproject.toml` are the exceptions the rule
does not decide, since every layer depends on them: a setting or a dependency belongs to whoever
is adding it — a migration's to `impl-database`, an endpoint's or a source's to `impl-backend`.

**A break in constructing a `models/` object in a test belongs to whoever changed the model.**
"Their tests under `api/tests/`" divides the suite but not its shared fixtures, which are built
from `models/` objects. `impl-database` fixes the construction — in a fixture or in a test
body, in whichever file it lives, the other agent's included — and nothing else in that file;
the assertions around it, and what the test is about, stay with the file's owner.

No specialist owns `infra/` — the stack script, the Caddyfile, the scheduled task's definition
and its installer — which is edited from the session, nor the record: `docs/`, `scripts/`, the
`CLAUDE.md` files, this overlay.

## The contract, and the order

- The contract is `api/openapi.json`: committed, and checked in CI twice — `api.yml` runs
  `python scripts/export_openapi.py --check` against the code, and `web.yml` runs
  `npm run check:api-types` against the client generated from it, one step further down. What
  it guarantees is the root [`CLAUDE.md`](../CLAUDE.md#standing-constraints)'s standing
  constraints; what its conventions mean — the envelope and the closed `ErrorCode`, cursor
  pagination, UTC times, `X-Request-ID` — is
  [`docs/03-architecture.md`](../docs/03-architecture.md)'s Conventions. The fleet's build
  order — schema, then API and contract, then clients — holds, and is the order the scaffold
  was built in.
- Regenerate after any change to the API surface: from `api/`, with its venv,
  `python scripts/export_openapi.py` (that is `api/scripts/export_openapi.py`; it refuses to
  export from a `constellate` package that is not this checkout's), then from `web/`,
  `npm run generate:api-types`, and commit both files with the change. The pre-push hook runs
  both checks when the change calls for them (`scripts/gates.py`). What a client leans on in
  the contract by name — the error schemas, the request-id header — is `web/CLAUDE.md`'s.

## Layers, architecture, and the standard

- The standard and its reasoning: [`docs/03-architecture.md`](../docs/03-architecture.md) —
  the layer order, where `sources/` and the entry points sit, the three seams, and the API's
  conventions.
- The per-layer rules in detail: `api/src/constellate/CLAUDE.md` — what belongs in which
  layer, the `SourceAdapter` seam, the entry points, the one sanctioned SQL, who configures
  logging.
- The layering check `pr-architecture-review` runs: `python scripts/check_layering.py` from the
  repository root, on a bare interpreter. It derives which modules outside the layers are
  leaves from what reaches them, sanctions the readiness probe's `select 1` by file and
  statement, and holds `sources/` to `docs/03`'s rule — its tests under `scripts/tests/` carry
  a case for each direction of it. `record.yml` and the pre-commit hook run it on every change
  under `api/`.
- The web client's own layer rule is `web/CLAUDE.md`'s, enforced by `web/src/layering.test.ts`
  at `npm test` from `web/`.

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
- The domain model: [`docs/02-domain-model.md`](../docs/02-domain-model.md).
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

**None decided about the domain yet.** The root
[`CLAUDE.md`](../CLAUDE.md#standing-constraints)'s standing constraints hold ADR-0002's
structural ones, and a reviewer holds a change to them. The domain model
(Q-C) produces the first domain invariants, and the reviewer-facing checklist is written here
when it does; until then a reviewer holds a change to those constraints and to
[`docs/00-vision-and-scope.md`](../docs/00-vision-and-scope.md)'s scope and non-goals.

## The boards

- **Product work** → GitHub **project 7** ("Constellate"), with a roadmap milestone.
- **Agent-setup work** → GitHub **project 8** ("Constellate agents"), label `agents`, no
  milestone.

`check_board.py` enforces the split. `gh` is on PATH on the dev machine (root
[`CLAUDE.md`](../CLAUDE.md#environment-gotchas)); the closing-step board rules are the
fleet's to state, and the commands that drive both boards are `scripts/README.md`'s
"Driving the boards".

## Toolchain

- The record scripts under `scripts/` run on a bare Python 3.13, and their commands are
  `scripts/README.md`'s.
- The API package's venv is `api/.venv`, one per worktree; making it is `api/CLAUDE.md`'s
  "Running it".
- The API's commands — tests, lint, the contract export — are `api/CLAUDE.md`'s "Running it".
- The web client's commands are `web/README.md`'s.
- `scripts/gates.py` runs whichever of these the change calls for from the hooks, and a
  toolchain that is not installed in the worktree is a skip it reports, never a failure.

## The running stack (for `ops`)

**There is no rig.** Nothing is deployed, `infra/stack.py` does not exist, and the three
facts the `ops` definition reads back from here — the main checkout to run stack commands
from, the rig's milestone, the test login — have no values. `ops` has nothing to operate
until M1 needs a public URL (Q-E); invoked before then it should say so and stop.

- **Main checkout** — `C:\Users\Atomt\Documents\favorites_tracker`, for when there is
  something to run from it.
- **The rig's milestone** — none.
- **Test login** — none.
