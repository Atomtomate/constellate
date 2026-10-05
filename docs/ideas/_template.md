---
status: raw
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# <Idea name>

> One or two sentences. What it is, in the owner's framing.

## Progress

- [x] Captured
- [ ] Problem stated — what is actually wrong today
- [ ] Ambiguity resolved — we agree what this means
- [ ] Approach sketched
- [ ] Checked against the [domain model](../02-domain-model.md)
- [ ] Stub or sketch written
- [ ] Sized
- [ ] Decision: adopt / park / drop

## The idea

What the owner said, verbatim and dated, and what it would do. Their framing first.

## Why it might be worth it

The problem it solves. If this section is hard to write, that is information.

## Open questions

Ambiguities, recorded rather than guessed at. The most important section while `raw`.

## Depends on

Milestones, data that does not exist yet, other ideas, parked investigations.

## Fit with the domain model

Either "fits, costs one table the log never references" or a specific list of what would have
to change. Leave empty until the idea is `shaped`.

## Where the data would come from

Only where the idea needs the outside world. A table of candidate feeds or files: what each
gives, how it is reached, what it costs, the terms that bite — every claim with the URL and
the date read, marked verified, reported or inferred — and a list of what was not verified.
When this section outgrows the file, it is an investigation (see `CLAUDE.md`).

## Sketch

Optional. Signatures and types, `raise NotImplementedError` bodies, or a table in SQL, clearly
marked as a sketch. See `CLAUDE.md` for the rules.

## Size

An evening / a weekend / a month / unknown. Do not fill in at `raw`.

## Where it would sit in the roadmap

A proposal with its alternatives, as a question for the owner. Never an edit to `07`. Leave
empty until the idea is `shaped`.
