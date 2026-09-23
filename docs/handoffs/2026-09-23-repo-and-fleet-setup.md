# Repository and agent-fleet setup
**Summary:** Created `Atomtomate/constellate`, mounted the shared fleet, seeded the record and its scripts, and recorded the owner's first direction: the tracker first.
**State:** Open — the owner corrects the scope; the data-source research, the domain model and the stack ADR are M0's remaining bullets.

## What was done

- The private repository `Atomtomate/constellate`, with `main` as its only branch, head
  branches deleted on merge, and the wiki off. The name was offered with four alternatives
  and confirmed by the owner the same day (Q-A, answered).
- The fleet `Atomtomate/agents` as a submodule at `.claude/agents/`, at its `main` of
  2026-09-23; the overlay `.claude/agents.local.md`, which says *not yet* wherever the
  project has no answer and names the open question that will give one.
- The record: `docs/00`, `07`, `08`, the ADR index and `ADR-0001`, the handoff, friction,
  digest and investigation READMEs carried over from the sibling project with their history
  attributed rather than restated.
- The owner's direction of the same day — *a tracker for Spotify and YouTube: what, how
  long and when* — written into `docs/00` as the meaning of v1, into `docs/07` as M1 with
  the atlas moved to M2 and M3, and into `docs/08` as Q-C and Q-D reframed around events
  and data sources.
- `scripts/`: the record scripts and their tests from the sibling project, minus its product
  checks; the constants that named that project rewritten; `gates.py` trimmed to the one
  area this tree has. The two gate hooks and `post-checkout`, and the `Record` workflow.
- Two user-level boards, linked to the repository; the `agents` label; milestones `M0` to
  `M4` mirroring the roadmap.

## How it was verified

- `python scripts/check_docs.py` and `python -m unittest discover scripts/tests` pass on
  the tree as committed.
- `python scripts/check_board.py --fetch` reports the milestones mirroring the roadmap and
  no open issues.
- `python .claude/agents/check_definitions.py` passes on the mounted fleet.

## What remains open

- M0's bullets: the data-source research (`docs/01`), the domain model (`docs/02`), the
  stack ADR and with it the ownership map. Each becomes an issue on the product board with
  milestone `M0` once the owner has read the corrected scope; the research is dispatched to
  standby sessions the same day, each on a branch of its own.
- The nightly worktree sweep (`scripts/README.md`) is not registered on this machine; it
  earns its place once worktrees exist.
- No `docs/ideas/` capture surface yet; the sibling project's is worth copying the day the
  first idea arrives.

## Needs a decision

- **The scope** in `docs/00-vision-and-scope.md`: every section marked *proposed* was
  derived from two short messages and is to be corrected, not accepted by silence.
- **The stack** (Q-B): the leaning is the sibling project's — Python and FastAPI, Postgres,
  React and Vite — because the tracker is a poller, a store and a site, and the fleet's
  implementers already know that cut. An ADR follows the owner's word.

## What carried it

The sibling project's `.claude/agents.local.md`, read whole before anything was written
here: it is the list of what a generic definition will ask this repository for, and every
*not yet* in the overlay is a section of it that this project could not yet answer.
