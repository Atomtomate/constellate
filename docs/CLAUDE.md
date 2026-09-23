# `docs/` — the written record

The plan is written down rather than carried in someone's head, and the reasoning with it.
That only stays true if the record is maintained. Read the root `CLAUDE.md` first.

## What lives where

| Path | Holds | Written when |
|------|-------|--------------|
| `00`, `07`, `08` (and `02`, `03` once they exist) | Scope, roadmap, open questions; later the domain model and the architecture | The plan changes |
| `adr/` | Decisions, with the reasoning that produced them | A decision is made |
| `investigations/` | External constraints, researched then **parked** | Reality is discovered |
| `handoffs/` | One record per finished task: done, verified, still open, what carried it — a `**Summary:**`/`**State:**` header under the title, indexed by `scripts/record_index.py` | A task closes |
| `friction/` | One note per time the process failed an agent: a wrong definition, a tool that fought back, an exclusion that dropped something real — an `**Agent:**`/`**Summary:**`/`**Retro:**` header under the title, indexed by `scripts/record_index.py` | An agent finishes with one to leave |
| `reviews/` | A branch's pass: one file per reviewer, an earlier wave's kept beside it as `<agent>-first-wave.md`, and the implementation agents' plans, which `reviews.is_reviewer_report` tells apart | A review pass runs, or a lane is planned |
| `digests/` | One file per `manager` run: the record since the last one, compressed and judged — a `**Covers:**`/`**Supersedes:**` header under the title, at most `record.DIGEST_CAP` lines | The manager runs, every few sessions and before a retro |

The distinction that matters: an **investigation** is something the world imposes, an
**ADR** is something we decided, a **handoff** is what one task left behind, a **friction
note** is what the process cost the agent that ran it, a **digest** is the record read whole
and judged, and the **roadmap** is what we committed to build.

## ADRs

- One decision per file, numbered, never deleted.
- Status is `Accepted`, `Proposed`, `Superseded` or `Parked`. Keep `adr/README.md` in step;
  `scripts/check_docs.py` fails when the two disagree.
- When an open question closes, it becomes an ADR only if the answer decides something no
  existing ADR already permits; otherwise it becomes a dated entry under "Answered" in
  `docs/08-open-questions.md`, naming which ADR already permits the answer ("No ADR: …").
  Either way the section that argued it is deleted: where an ADR follows, prose survives
  only where it argues something the ADR does not.
- Superseding beats editing. When a decision genuinely changes, add a dated revision note
  to the Consequences saying what changed and *why it was safe to change*.
- The Alternatives section is not padding. A future reader needs to know what was
  considered and rejected, or they will propose it again.

## Keeping it honest

**A change that makes a doc wrong is not finished until the doc is fixed.** This is the
single most common failure in a project like this: a decision made well, argued in a code
comment, and never written where the next person will look.

Two specific traps, both seen in the sibling project:

- **Citing an ADR that does not contain the decision.** Worse than citing none, because it
  looks reviewed. If the ADR does not say it, add it to the ADR.
- **A milestone redefined in conversation.** If what is being built stops matching
  `07-roadmap.md`, the roadmap is wrong and must be rewritten — including what replaced any
  sequencing rule that was dropped.

`pr-direction-review` checks for both, but catching it there means it already reached a PR.

## Style

Prose, not bullet soup. Say why, not only what. Where a claim is load-bearing — a policy, a
limit, an API's behaviour — quote the source and date it, because these things change and
the next reader needs to know how stale the claim is.

Nothing in `investigations/` may influence a design decision until it is deliberately
unparked.
