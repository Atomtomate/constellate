# ADR-0001 — The shared agent fleet is consumed as a submodule, with a project overlay

- **Status:** Accepted
- **Date:** 2026-09-23

## Context

The owner runs a fleet of Claude Code agents — four reviewers with disjoint scopes, three
implementation specialists split by file ownership, a director that plans across them, a
manager, a retro and an operator — together with the process they work under: a written
record of handoffs and friction notes, a standard review pass on every PR, a closing step
that keeps two GitHub boards in step with the record, and a retro that changes the agents at
the level of the class rather than the incident.

That fleet was built inside the owner's board-game tracker and extracted from it into
`github.com/Atomtomate/agents` under that project's `ADR-0019`, precisely so a second
project could use it. The extraction left the definitions generic and moved every
project-specific fact into a file the consuming repository owns, `.claude/agents.local.md`,
which the definitions read by relative path. The boundary rule there is the one this
repository inherits: **knowledge goes where its subject is.**

This is the second project. It starts with no code, no stack and no schema, and one
paragraph of brief. What it needs on day one is the process, not the product: a place for
decisions, a record that a cold agent can read, and the checks that keep both honest.

## Decision

- The fleet is mounted as a **git submodule at `.claude/agents/`**, pinned to a commit, so
  Claude Code loads the definitions from disk and this repository chooses when to move the
  pointer. A definition is edited in the fleet repository and never here.
- This repository's answers to the fleet live in **`.claude/agents.local.md`**: the
  file-ownership map, the board numbers, the review-report rule, the toolchain and the
  rig — or, at M0, an explicit *not yet* naming the open question that will answer it.
- The record conventions and the scripts that enforce them — the handoff and friction
  header contracts, `check_docs.py`, `open_work.py`, `worktree_status.py`, the two hooks,
  the gates — are **copied from the board-game tracker at its commit
  `8c77871a0d02df1756ebe71773fa77d1dab7794f`**, with its product checks
  (`check_layering.py`, `check_reference.py`, the API, web and infra gate areas) left out.
  They are a fork, adapted at the constants that named that project.
- Two user-level GitHub project boards, one for product work with a roadmap milestone and
  one for work on the agent setup (label `agents`, no milestone), as the closing step
  expects; the numbers are the overlay's.
- The committed hooks under `.githooks/` are activated per clone with
  `git config core.hooksPath .githooks`: `post-checkout` populates the submodule in a new
  worktree, and `pre-commit` and `pre-push` run the same checks CI runs.

## Consequences

- **The fleet moves when this repository says so.** A fleet change reaches here as a
  pointer bump in a PR of its own, and `open_work.py --fetch` reports how far behind the
  pointer is. Nothing product-facing depends on the submodule being present: CI clones
  without it, and `check_docs.py` treats its path as a boundary it does not walk.
- **A `git worktree add` leaves the submodule empty**, and a session that starts in that
  worktree is blind to the whole fleet. The `post-checkout` hook fills it; the root
  `CLAUDE.md`'s "Environment gotchas" says how to activate it and what to do when a session
  still scans the roster before the hook has run.
- **The implementation agents cannot run yet.** Their ground is a file-ownership map, and
  the map is the stack's; until the stack ADR (Q-B) writes it, `impl-director` reports
  that work cannot be cut, and record work is done from the session. The reviewers, the
  manager and the retro work from the first commit. *Revised 2026-09-23: ADR-0002 settled the
  stack and filled the map in `.claude/agents.local.md`, so the implementation agents can now
  be briefed against it.*
- **`scripts/` is a fork and will drift from its source.** Whether the generic half moves
  into the fleet repository is recorded under "Smaller, for later" in
  `docs/08-open-questions.md`; until it is decided, a fix to one copy is carried to the
  other by hand.
- **`ops` has nothing to operate.** No rig exists; the overlay says so and the agent should
  stop when invoked. That changes when M1 needs a public URL (Q-E).

## Alternatives considered

- **A vendored copy of the definitions.** Simplest to read, and it drifts from the fleet the
  day after it is copied — the thing the extraction was done to prevent.
- **A Claude Code plugin.** Cannot carry the per-repository overlay the definitions rely on,
  and the board-game tracker's `ADR-0019` rejected it for the same reason.
- **No fleet, and an ordinary CLAUDE.md.** Cheaper for the first week. The brief is broad
  and the owner's stated way of working is a written record with agents held to it; the
  fleet is that record's enforcement, and starting without it means retrofitting it onto a
  history that was never written down.
