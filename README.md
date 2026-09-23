# Constellate

> **Status: M0.** Nothing is built. This repository holds the plan, the decisions and the
> agent setup; the first line of product code waits on the data-source research, the
> domain model and the stack ([08](docs/08-open-questions.md)).

A log of what the owner listens to on Spotify and watches on YouTube — when, and for how
long — and, on top of it, an atlas of favourite videos, music and websites and of the
thematic constellations between their creators. It exists to answer two questions with a
link instead of from memory: *what would you recommend?* and *who were those creators
again?*

**Created:** 2026-09-23

## Read in this order

| # | Document | What it answers |
|---|----------|-----------------|
| 00 | [Vision & Scope](docs/00-vision-and-scope.md) | The brief, what we build, what we do not |
| 07 | [Roadmap](docs/07-roadmap.md) | Milestones and what blocks what |
| 08 | [Open Questions](docs/08-open-questions.md) | What is still undecided |

[docs/adr/](docs/adr/) holds the decisions. [docs/investigations/](docs/investigations/)
holds parked research.

## How work happens here

A shared fleet of Claude Code agents, mounted at `.claude/agents/` and told about this
project by `.claude/agents.local.md`
([ADR-0001](docs/adr/0001-adopt-the-shared-agent-fleet.md)). Every PR gets a four-reviewer
pass; every task ends with a handoff; the closing step keeps the record and the two GitHub
boards in step, and `scripts/` says when they are not. The rules are in
[`CLAUDE.md`](CLAUDE.md).

After cloning:

```
git submodule update --init .claude/agents
git config core.hooksPath .githooks
git config extensions.worktreeConfig true
```
