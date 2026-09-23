# The stack ADR, drafted and accepted
**Summary:** ADR-0002 drafted, accepted by the owner as option A (the sibling's stack, a one-shot poller fired by the OS scheduler, Postgres), and carried into the overlay, the root `CLAUDE.md`, `docs/03` and `docs/08`.
**State:** Open — the scaffold PR, cut by `impl-director` along the new map, is the next step.

## What was done

Branch `claude/stack-adr`, from `main` at `07710fd`, in its own worktree; PR #1. Briefed by the
coordinating session; no code, no scaffold, no issue.

- **The draft.** `docs/adr/0002-the-stack.md` weighed three stacks — (A) the sibling project's
  as is, (B) Python only with pages rendered on the server and SQLite, (C) TypeScript end to
  end — then what fires the poller (APScheduler in the API, a long-running worker, or an OS
  scheduled task firing a one-shot command) and Postgres against SQLite. It recommended A with
  the OS-scheduled one-shot poller and Postgres, and drafted the file-ownership map.
- **The acceptance.** The owner chose option A on 2026-09-23. The same PR then:
  - marks ADR-0002 Accepted — "over B, C and A-with-SQLite" — and moves its row in
    `docs/adr/README.md`;
  - moves Q-B to Answered in `docs/08-open-questions.md`, deleting its open section; nothing
    else in `docs/08` changed, since other lanes are editing Q-C to Q-F;
  - fills `.claude/agents.local.md`: the banner, the ownership map with the sibling's two
    partition rules, the contract and the build order, the layers (pointing at `docs/03` and at
    `api/src/constellate/CLAUDE.md` and `scripts/check_layering.py`, both named as arriving with
    the scaffold), and the toolchain, marked "once the scaffold exists". The domain-invariants
    paragraph now names ADR-0002's structural constraints, which it said did not exist;
  - writes `docs/03-architecture.md`: the shape, the three seams, the layer order with
    `sources/` and the entry points, and what is not decided here;
  - edits the root `CLAUDE.md`: the M0 banner (it said "no stack"), the `impl-director` bullet,
    and four standing constraints citing ADR-0002, in place of the sentence saying none
    existed. The owner approved these two instruction-file edits in the session before they
    were made;
  - adds a dated revision line to ADR-0001's "The implementation agents cannot run yet".

## How it was verified

- `python scripts/check_docs.py` is green, and the pre-commit hook passed on every commit.
- Every line outside a table and a handoff header is at most 100 characters, counted by
  character.
- The draft's claims about the sibling project were read from its files at the time of writing.
  Nothing there, and nothing in the main checkout, was written to.
- **Not verified**: the Task Scheduler setting names in ADR-0002 (`StartWhenAvailable`,
  `WakeToRun`) are from memory, and the ADR says so. Whoever writes the task checks them.

## What remains open

- **The scaffold PR, the next step.** Cut by `impl-director` and built by the specialists, not
  by this PR: the `api/` and `web/` skeletons laid out per the map; `scripts/check_layering.py`
  ported to package `constellate`; the `api`, `web` and `infra` gate areas in
  `scripts/gates.py` and their workflows; the per-directory `CLAUDE.md` files, starting with
  `api/src/constellate/CLAUDE.md`, which the overlay and `docs/03` already point at.
- **The data-source documents may still move details.** ADR-0002's Consequences name three:
  whether YouTube needs an extension (which makes `extension/` and its gate area real), whether
  Spotify can be polled and how often, and how a polled play and an exported play are
  recognised as one. None of them reopens the stack.
- **Q-E** decides where it runs, and with it what keeps Postgres and the scheduled task up.
  ADR-0002 makes a database server that starts with the machine a requirement of that answer.

## Needs a decision

Nothing further here: the stack was decided by the owner on 2026-09-23.

## What carried it

The overlay's three *not yet* sections — file ownership, the contract, the layering — at the
moment of framing the draft's Context: they turned "which stack" into three constraints every
option could be scored against. At acceptance, the same sections became the checklist of what
to fill.
