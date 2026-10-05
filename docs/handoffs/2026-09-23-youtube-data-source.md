# YouTube data source research
**Summary:** Wrote `docs/01-data-sources-youtube.md`: how YouTube and YouTube Music watch history is backfilled, captured ongoing and given durations, with a recommendation.
**State:** Open — the owner reads the document and requests the Takeout; the Data Portability API spike and Q-D's answer in `docs/08` remain.

## What was done

- Researched the YouTube half of Q-D on the coordinator's brief and wrote
  `docs/01-data-sources-youtube.md` on `claude/youtube-data-source`. It covers the history
  setting and auto-delete, the Takeout record, ongoing capture, enrichment with
  `videos.list`, what "how long" can mean, how two records of one watch are matched, and a
  recommendation.
- The finding that most changes Q-D's starting leaning: Google's Data Portability API exports
  the same `myactivity.youtube` records daily and incrementally, under a 30- or 180-day
  consent, for accounts in the EU, Switzerland and the UK. If a personal, unverified app can
  hold that grant, ongoing capture of *what and when* needs no browser extension; the
  extension is then needed only for measured seconds on desktop.
- Two further findings that shape the model: auto-delete defaults to 36 months for accounts
  or histories started after 24 June 2020, so the oldest history may be disappearing monthly;
  and the Data API's developer policies cap storage of API data at 30 days unless refreshed,
  so video length and category are a cache, not log columns.
- No edits to `docs/07`, `docs/08` or the overlay, and no issues filed, per the brief.

## How it was verified

- Every load-bearing claim carries a source (34, all read 2026-09-23) and is marked
  verified (read on the page), reported (third party) or inferred. Pages were read through a
  fetch tool that returns excerpts, which the document says.
- One claim was read out of code rather than prose: `ytmusic_wrapped`'s parser, fetched raw,
  selects `header == "YouTube Music"` and slices ids at character 32.
- `python scripts/check_docs.py` passes on the branch; the pre-commit hook ran it.

## What remains open

- **The Data Portability API spike** (`docs/01-data-sources-youtube.md` §6): whether an
  unverified personal app keeps a 180-day grant past the 7-day testing-token limit. It decides
  between daily capture and two-monthly Takeout.
- **The owner's steps today**: check YouTube History and auto-delete; request a JSON Takeout of
  YouTube and YouTube Music.
- **Unverified points**, listed in the document's §7: Shorts in the history, the Music URL
  host, when `time` is logged, the 50-id limit, the auto-delete choices, and Web Scrobbler on
  non-music videos.
- **Q-D's answer in `docs/08`**, once both source documents exist and the owner has read them;
  the duration *kind* (measured, length, estimate, unknown) as an input to Q-C; the
  extension's reframing as an input to Q-F.

## What carried it

- The brief was self-contained and named the questions; it made the document's outline.
- Reading Google's own pages over third-party summaries; where only a third party said
  something, the document says so rather than rounding it up to fact.
- Searching for a sanctioned recurring route beyond the brief's list is what surfaced the
  Data Portability API, which the brief's leanings did not name.
