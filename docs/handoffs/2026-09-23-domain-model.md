# Domain model: events, items, creators, sources
**Summary:** Drafted `docs/02-domain-model.md`, Q-C's proposed answer, and ADR-0003 (Proposed), its ingestion seam: one event per play resolved from kept observations, items per source identity, catalogue data as an expiring cache.
**State:** Open — the owner accepts or corrects ADR-0003 and the model; Q-C's answered entry in `docs/08` and the standing constraints follow acceptance, and are the coordinator's.

## What was done

- `docs/02-domain-model.md`, the brief's eight sections. It was written against the three inputs
  on open PRs, as they stood at their tips: the Spotify research (#3, `cfbdb78`), the YouTube
  research (#2, `9543a9f`) and the stack ADR (#1, `e8677c7`, option A accepted by the owner).
  The model in one line each:
  - **Event and observation.** An event is one play. Each source's record of it is an
    observation, stored with its raw JSON and never changed. The event's columns are resolved
    from its observations by precedence, so the export's `ms_played` replaces the poller's
    estimate whichever arrives first.
  - **Duration basis.** The event stores `measured`, `to_end` or `start_only`, not "the item's
    length". Length is YouTube API data under the 30-day rule, so it may never be copied onto a
    log row; a total joins it from the cache when read.
  - **Identity.** An item is one source identity (`item_ref`). Items are merged within a service
    only on ISRC, and never across services. Creators known only by the export's album-artist
    name are the exception.
  - **Cache.** Keyed by item ref, in its own schema so long-lived backups leave it out. It is
    refreshed at 25 days, deleted at 30, and read as absent after 30.
  - **Sanity check.** Websites and a fourth music service fit without migrating the event table.
    The cost lands on item identity.
- `docs/adr/0003-the-ingestion-seam.md`, Proposed, listed in the ADR index. It states the seam
  on its own so that the owner can decide it from one document: observations stored verbatim and
  never changed; the event resolved by precedence; `record_key` dropping re-delivered records;
  the cursor committed with its observations. It records three rejected alternatives. Item
  identity stays out of it, as one paragraph under Consequences, because the seam works under
  any grouping of refs into items. The model's §2 and §8 point at the ADR.
- Nothing else changed. `docs/08` is left for the coordinator, and there is no code and no
  overlay edit.

## How it was verified

- `python scripts/check_docs.py` passes. No line of the document is wider than 100 columns.
- Every citation of a data-source finding was checked against that document at the tip named
  above. Three claims were tightened on that pass: that the Data API gives no ISRC (true only by
  the absence of the field in the YouTube doc's list), that Takeout and Portability share one key
  (it rests on an inference there), and the `to_end` basis (it rests on a report, S24).
- Not verified: the model has met no real data. The matching windows, the precedence order and
  the shared Google key are all inferences until the owner's exports arrive.

## What remains open

- **Spotify's developer terms on storing Web API data** were not read by the Spotify research.
  The model treats Spotify's catalogue facts as cache so that the answer can only loosen it.
  Reading them is a small research task before M1's enrichment.
- **Q-C's answered entry in `docs/08`**, to be written by the coordinator when the owner accepts.
- **Standing constraints for the root `CLAUDE.md`**, once accepted. The log keeps no catalogue
  data, and an item's length is never copied onto an event (the YouTube policy, dated). An item
  is one source identity, never merged across services.
- The eight open points in the document's §8 (terms, windows, the owner's import choices,
  `ip_addr`, the time zone, null-item events, collection tables, a work layer). None blocks the
  schema except the first two, and those are tuned in M1 rather than decided now.

## Needs a decision

- **Accept ADR-0003, the ingestion seam, or correct it.** The leaning is to accept. It is the
  most expensive choice in the model to reverse. It gets an ADR of its own for three reasons:
  - the root `CLAUDE.md` names "an import seam" among the things written down before they are
    built on;
  - the stack ADR delegated only the draft's *shape* to Q-C, not how duplicates resolve;
  - its rejected alternatives (a row per record with duplicate flags; an upsert where the last
    writer wins) are exactly what a future implementer would propose again.
- **Accept or correct the rest of the model.** The second choice that is expensive to reverse is
  item identity: one item per source identity, merged only on ISRC, never across services. It
  needs no ADR if the owner agrees; it becomes a standing constraint and part of Q-C's answer. If
  the owner wants one song merged across services, that is an ADR of its own.
- **ADR numbering.** `0002` is the stack ADR on #1. Whichever of #1 and this PR merges second
  takes a one-line conflict in the ADR index.

## What carried it

The two data-source documents' paragraphs addressed to Q-C did most of the work: YouTube §5's
"carry its duration together with the kind of duration", YouTube §4's cache-versus-column point,
and Spotify §4's "the export wins". Putting the brief's "provenance: the item's length" beside
the 30-day rule is what turned the provenance into a basis stored on the event, with the length
read from the cache, rather than a length copied onto the event.
