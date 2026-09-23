# Domain model: events, items, creators, sources
**Summary:** Wrote `docs/02-domain-model.md`, Q-C's answer, and ADR-0003, its ingestion seam, accepted by the owner: one event per play resolved from kept observations, items per source identity with no cross-service merging, catalogue data as a cache, Spotify's API plays kept until the export replaces them.
**State:** Open — Q-C's answered entry in `docs/08` and the two standing constraints in the root `CLAUDE.md` wait for the consolidation PR after #1 and #4 merge; #4 rebases onto `main` once #1 has merged.

## What was done

- `docs/02-domain-model.md`, the brief's eight sections. It was written against the three inputs
  on open PRs: the Spotify research (#3, `cfbdb78`, and its terms section §6 at `3623499`), the
  YouTube research (#2, `9543a9f`) and the stack ADR (#1, `e8677c7`, option A accepted by the
  owner). The model in one line each:
  - **Event and observation.** An event is one play. Each source's record of it is an
    observation, stored verbatim and never changed. The event's columns are resolved by
    precedence, so the export's `ms_played` wins in any arrival order.
  - **Duration basis.** The event stores `measured`, `to_end` or `start_only`, never a length.
    Length is catalogue data, read from the cache when a total needs it.
  - **Identity.** One item per source identity, merged within a service on ISRC only. The owner
    chose no cross-service merging.
  - **Cache and terms.** YouTube: refreshed at 25 days, deleted at 30. Spotify: rows kept only
    while needed, refreshed by live plays. The Web API's plays are re-sourced to the export once
    it covers them, and everything from Spotify's API is deletable as a set within five days of
    a disconnect.
  - **Sanity check.** Websites and a fourth music service leave the event table alone.
- `docs/adr/0003-the-ingestion-seam.md`, now **Accepted**. The owner's acceptance was relayed by
  the coordinator session on 2026-09-23, over a last-writer-wins upsert. It carries one dated
  amendment made in this PR: Spotify's terms add a second reason to delete observations.
  Item identity stays out of it, as a Consequences paragraph recording the owner's choice.
- Nothing in `docs/08`, the overlay or the root `CLAUDE.md`; the consolidation PR owns those.

## How it was verified

- `python scripts/check_docs.py` passes. No prose line in the three files is wider than 100
  columns.
- Every citation of a data-source finding was checked against its document at the tip named
  above. The Spotify terms were checked against §6 quote by quote.
- Not verified: the model has met no real data. The matching windows, the precedence order and
  the shared Google key stay inferences until the owner's exports arrive.

## What remains open

- **Consolidation PR** (the coordinator's), after #1 and #4 merge. It writes Q-C's answered entry
  in `docs/08` and adds two standing constraints: the log holds no catalogue data, and items are
  never merged across services.
- **Rebase** of #4 onto `main` once #1 merges. The ADR index then takes a one-line conflict;
  keep both rows.
- **Spotify's terms as Spotify would read them** (model §8): "indefinitely" for API plays no
  export has yet replaced, own totals as "analysis", a timeline beside YouTube as
  "integration", and whether the export is covered at all.
- The rest of the model's §8: the matching windows, the owner's import choices, `ip_addr`, the
  time zone, null-item events, collection tables, a work layer. None blocks the schema.

## What carried it

The data-source documents' paragraphs addressed to Q-C did most of the work: YouTube §5's
"carry its duration together with the kind of duration", YouTube §4's point on cache against
column, Spotify §4's "the export wins", and then Spotify §6's "re-sourced to the export". The
30-day rule is what turned the duration's provenance into a basis stored on the event, rather
than a length copied onto it. The same seam then absorbed Spotify's terms without a new table,
because an event re-resolves from whatever observations remain.
