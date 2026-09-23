# Domain model: events, items, creators, sources
**Summary:** Wrote `docs/02-domain-model.md`, Q-C's answer, and ADR-0003, its ingestion seam, accepted by the owner with no cross-service item merging; the review pass is folded, and one amendment to the ADR awaits the owner.
**State:** Open — the owner confirms ADR-0003's 2026-09-23 amendment, and #1 merges first; then #4 rebases and goes ready, and the consolidation PR follows.

## What was done

- `docs/02-domain-model.md`, the brief's eight sections, summarised in its own "The model in
  brief". It was written against the inputs on open PRs: the Spotify research (#3, finally at
  `ec00a85`, which adds Policy §III read whole and the Last.fm path), the YouTube research (#2,
  `9543a9f`) and the stack ADR (#1, `e8677c7`).
- `docs/adr/0003-the-ingestion-seam.md`, **Accepted**. The owner's acceptance, over a
  last-writer-wins upsert, and the choice against cross-service merging were relayed by the
  coordinator session on 2026-09-23. A dated amendment follows the acceptance. It lets
  observations be deleted where a source's terms require it, pairs matches in order, and widens
  the name-and-time fallback for Last.fm. The first of those is the owner's to confirm.
- `docs/07-roadmap.md`: M0's domain-model line is marked done.
- The standard pre-review pass: four reports in `docs/reviews/domain-model/`. Everything
  real was folded, and the PR body's Review pass section lists what was acted on and dismissed.

## How it was verified

- `python scripts/check_docs.py` passes. No prose line is wider than 100 columns. The record
  gate passed in the pre-commit and pre-push hooks. CI's `Record` workflow did not start:
  GitHub reports that the account's payments failed or its spending limit is reached.
- Every citation of a data-source finding was checked against its document; the Spotify terms
  and the Last.fm path against §6 at `ec00a85`, quote by quote.
- Each reviewer finding was checked against the text before it was folded. The failure cases in
  the tech review (a repeated track, an ISRC row already deleted, an export before a late poll)
  were traced through the rules as written.
- Not verified: the model has met no real data. The matching windows, the Last.fm window, the
  scrobble's `to_end` basis and the shared Google key stay inferences until the owner's data
  arrives.

## What remains open

- **The owner confirms or rejects ADR-0003's amendment**, above all the deletion of Spotify's
  live observations on re-sourcing and on a disconnect.
- **How Spotify captures live** (model §8): the Web API, the export plus Last.fm with no Spotify
  app, or the export alone. It is the owner's choice under Q-D, and the model carries all three.
- **#4 merges after #1.** #1 still says the stack ADR is Proposed; its acceptance has to be
  recorded there first, because ADR-0003 cites option A as accepted. Rebase then, keeping both
  rows of the ADR index.
- **The consolidation PR**, after #1 and #4 merge:
  - Q-C's answered entry in `docs/08`;
  - the two standing constraints in the root `CLAUDE.md`: the log holds no catalogue data, and
    items are never merged across services;
  - the overlay's "not yet written" line for the domain model and its "None decided" line on
    product constraints (`.claude/agents.local.md`);
  - Q-E's inherited requirements: database backups kept at most five days with the plain-format
    export as the long-term copy (model §4), and encryption at rest if Data Portability is used.
- **M1's first migration** should delete the model's §7 sketch and have §1 point at the schema,
  so the two never drift.
- The rest of the model's §8: `ip_addr`, the time zone, null-item events, collection tables, a
  work layer. None blocks the schema.

## What carried it

The data-source documents' paragraphs addressed to Q-C did most of the work. The 30-day rule
turned the duration's provenance into a basis stored on the event, and the seam then absorbed
Spotify's terms and Last.fm without a new table, because an event re-resolves from whatever
observations remain. The review pass carried the rest. A repeated track traced through the
matching rule, and an acceptance commit diffed against the text the owner had accepted, found
what a re-read would not.
