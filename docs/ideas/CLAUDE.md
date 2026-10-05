# Working in `docs/ideas/`

Instructions for Claude when handling anything in this directory. The root `CLAUDE.md` and
[`docs/CLAUDE.md`](../CLAUDE.md) apply; this file adds only what is specific to ideas.

## What this directory is

A **capture surface**. The owner throws an idea here; it gets filed, and then developed over
time — possibly over months, possibly never.

The priority when an idea arrives is that it is **recorded faithfully and fast**, not that it
is designed. A raw idea sitting in a file is a success. A raw idea turned into three pages of
speculative architecture is a failure — the plan calls itself exploratory for the same reason
([`00`](../00-vision-and-scope.md)'s banner), and everything the outside world imposes is
parked until it is deliberately unparked ([`investigations/`](../investigations/README.md)).

## Filing a new idea

When the owner gives you an idea:

1. **One file per idea**, named as a slug: `concert-and-release-calendar.md`. No numeric
   prefixes — ideas get dropped and reordered too often for numbering to help.
2. Copy [`_template.md`](_template.md) and fill in what you actually know.
3. **Start at `status: raw`.** Do not skip ahead because the idea seems clear.
4. Write down what the owner said, verbatim and dated, before adding your own words. The
   record cites the owner's decisions by date; an idea's origin is cited the same way.
5. **Ambiguity gets recorded, not resolved.** If an idea could mean four things, list the four
   under Open questions and ask. Do not pick one and design it.
6. Add a row to [`README.md`](README.md).
7. Say what you filed, in one or two lines. Do not summarise the whole file back.

## Developing an idea

Only when the owner asks, or when the idea is directly relevant to work in progress.

Move it one status at a time and update the progress checklist as you go. It is fine — normal,
even — for an idea to sit at `raw` for months.

When you do develop one:

- **Check it against the domain model**: `docs/02-domain-model.md` and the ingestion seam it
  rests on, `ADR-0003` — both in flight as PR #4 when this file was written (2026-10-05), so
  named here rather than linked. Either the idea fits, or the file names exactly what would
  have to change. This is the single most valuable thing you can add to an idea, because it
  converts "nice thought" into "one table the log never references" or "a migration of the
  event table".
- **Name what it depends on.** Most ideas are gated on something — a milestone in
  [`07`](../07-roadmap.md), data that does not exist yet, another idea, a question in
  [`08`](../08-open-questions.md), a parked investigation.
- **Where it needs the outside world, research it the way the data-source documents do**: a
  table of candidates, each claim with the URL and the date it was read, marked verified,
  reported or inferred, and a list of what was not verified. An idea may hold that research
  while it fits in a section; when it outgrows one it is an investigation and moves to
  [`investigations/`](../investigations/README.md), parked.
- **Size it honestly.** An evening, a weekend, or a month. If you cannot tell, say so.
- **Propose its place in the roadmap; never take it.** Where an idea sits in
  [`07`](../07-roadmap.md) is the owner's decision. The idea states the options and a leaning,
  and the roadmap changes only when they choose, in a PR that says so.
- Link, never duplicate. Point at ADRs, the roadmap and investigations rather than restating
  them — in backticks while the file is not on your branch, because `scripts/check_docs.py`
  resolves every link in `docs/` and fails on one that does not.

## Stub implementations

Optional, and useful once an idea reaches `shaped`. Rules:

- Match the decided stack ([ADR-0002](../adr/0002-the-stack.md)): Python 3.13, FastAPI,
  SQLAlchemy 2 and Alembic on Postgres in `api/`, package `constellate`; React + Vite +
  TypeScript in `web/`. A sketch respects the layers [`03`](../03-architecture.md) states: a
  source adapter knows HTTP or a file format and never SQL.
- Types, signatures and docstrings. Bodies are `raise NotImplementedError` or a comment. The
  point is to make the shape concrete, not to write the feature.
- **Always inside a fenced block, in the Markdown file. Never a `.py` file, never wired into
  the app.** A sketched table is SQL in a fenced block the same way, marked as a sketch, as
  `docs/02-domain-model.md` does it.
- Prefix any non-obvious block with a line saying it is a sketch.

If a stub starts wanting to be real code, that is the signal the idea is ready to graduate —
not a reason to keep writing it here.

## Status vocabulary

| Status | Means |
|--------|-------|
| `raw` | Captured. Possibly one sentence. No analysis yet. |
| `shaped` | The problem and a rough approach are clear. Ambiguity resolved. |
| `speced` | Detailed enough that someone could build it. Fits the model, or names the change. |
| `adopted` | Promoted to the [roadmap](../07-roadmap.md). The file stays as the origin story. |
| `parked` | Good idea, blocked or not now. Says what would unblock it. |
| `dropped` | Decided against. **Keep the file**, with the reason. Stops it being re-proposed. |

## How an idea leaves this directory

It does not — files stay. What changes is status, plus where the work is tracked:

```
idea ──► needs external research? ──► investigations/ ──┐
     └──► adopted ──► a roadmap milestone ──────────────┤
                  └──► a structural choice ──► an ADR ──┘
```

An adopted idea keeps its file with `status: adopted` and a pointer to wherever the work now
lives. The idea file records *why the thing exists*; the roadmap records *what is being
built*. Do not migrate content out of here.

## The distinction that matters

[`docs/CLAUDE.md`](../CLAUDE.md) draws the line between an investigation, an ADR, a handoff
and the roadmap. An idea sits before all of them: *something we might want*, whose origin is
that someone had a thought. If a new file is "what does Ticketmaster's API allow", it is an
investigation, not an idea; "we should have a concert calendar" is an idea, and the API
question is one line under its Open questions until someone goes to find out.

## The index

[`README.md`](README.md) holds a table, one row per idea. The handoff and friction indexes are
derived from headers instead, because every closing branch edited their tables at once
(`docs/handoffs/README.md`). Ideas arrive a few a month, one conversation at a time, so this
table is kept by hand; if it ever conflicts the way those did, the header-and-script pattern
is the fix, not a rule against having an index.

## Do not

- Design an idea further than the owner asked for.
- Estimate an idea at `raw`.
- Create implementation files anywhere in this repository.
- Silently reinterpret an ambiguous idea into whichever version is easiest to write about.
- Let this file drift. When a convention changes, change it here in the same commit, and say
  so, so the owner knows the convention moved.
