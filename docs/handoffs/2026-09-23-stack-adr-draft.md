# The stack ADR, drafted as Proposed
**Summary:** Drafted ADR-0002 (Proposed) arguing Q-B's options, with a recommendation and a draft file-ownership map, for the owner to decide.
**State:** Open — the owner's decision on the stack; then the PR that accepts it and carries the map into the overlay.

## What was done

Branch `claude/stack-adr`, from `main` at `07710fd`, in its own worktree; a draft PR against
`main`. Briefed by the coordinating session; no code, no scaffold, no issue.

- `docs/adr/0002-the-stack.md`, Status Proposed. Its Context pulls the requirements from `00`,
  `07` and `08` (Q-B, with Q-C to Q-F) and the constraints the fleet imposes: three implementers
  split by file ownership, a contract the clients generate from, a layering the architecture
  reviewer can check. It weighs three stacks — (A) the sibling project's as is, (B) Python only
  with pages rendered on the server and SQLite, (C) TypeScript end to end — then what fires the
  poller (APScheduler in the API, a long-running worker, or an OS scheduled task firing a
  one-shot command) and whether the store is Postgres or SQLite. It says the time-series
  concerns are small, and why, so that nobody adds machinery for them.
- The same ADR's appendix drafts the file-ownership map the overlay takes on acceptance, and
  the CI areas `scripts/gates.py` would gain. Neither `.claude/agents.local.md` nor
  `scripts/gates.py` was edited.
- `docs/adr/README.md` lists it under Proposed.

## How it was verified

- `python scripts/check_docs.py` is green, and the pre-commit hook passed on each commit.
- Every line outside a table is at most 100 characters, counted by character, not by byte.
- What the ADR says about the sibling project was read from its files at the time of writing:
  its root, `api/` and package `CLAUDE.md`s, `docs/03-architecture.md`, `docs/04-tech-stack.md`,
  `docs/06-infrastructure-and-ops.md`, `ADR-0013` and `ADR-0015`, its overlay and
  `scripts/gates.py`. Nothing there was written to.
- **Not verified**: the Task Scheduler setting names (`StartWhenAvailable`, `WakeToRun`) are
  from memory of its task XML schema, and the ADR says so. Whoever writes the task checks them.
- The scale estimate (about half a million events over a decade) is an order-of-magnitude
  guess from a heavy day's listening and watching, stated as one; the data-source documents
  may refine it, and nothing in the recommendation turns on it being exact.

## What remains open

- **The owner's decision on the stack.** Below.
- **The PR that accepts it**, once decided: the map into `.claude/agents.local.md` together with
  the overlay's contract and layering sections; `check_layering.py` ported; the gate areas and
  their workflows; `docs/03-architecture.md`; the standing constraints in the root `CLAUDE.md`;
  Q-B moved to Answered. The standard review pass runs there, not on this PR.
- **The two data-source documents may move it.** The ADR's Consequences name the three places:
  whether YouTube needs an extension (the strongest), whether Spotify can be polled and how
  often, and how a polled play and an exported play are recognised as one. Worth re-reading the
  ADR against both documents before accepting it.

## Needs a decision

**The stack (Q-B).** Leaning: **option A, the sibling's stack as is** — FastAPI, SQLAlchemy,
Alembic, Postgres, an OpenAPI contract committed at `api/openapi.json`, React + Vite +
TypeScript — **with the poller as a one-shot command fired by the OS scheduler, and Postgres as
the store.** The strongest reason: it is the only option whose ownership map is already proven,
and M0 is done when an implementation agent can be briefed against one. The condition that would
flip the store: if Q-E cannot promise a database server that starts with the machine, SQLite is
the better store, and it switches at no cost before the first migration.

## What carried it

The overlay's three *not yet* sections — file ownership, the contract, the layering — at the
moment of framing the Context: they turned "which stack" into three constraints every option
could be scored against, which is what made B's and C's costs specific rather than a matter of
taste.
