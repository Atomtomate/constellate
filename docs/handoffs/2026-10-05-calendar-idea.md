# Idea filed: a calendar of concerts and releases, and the ideas capture surface
**Summary:** Created `docs/ideas/` — rules, template, index — and filed the owner's calendar idea at `shaped`: how it fits the model (one new noun, the occasion), sixteen feeds verified with URL and date, open questions, and a roadmap proposal.
**State:** Open — the owner reads the idea, answers its first three open questions and says where it sits in the roadmap; the root `CLAUDE.md`'s table gains a `docs/ideas/` row in the consolidation PR.

## What was done

- `docs/ideas/CLAUDE.md`, `_template.md` and `README.md`, modelled on the sibling project's and
  adapted: Constellate's stack for a stub (ADR-0002); the domain model named in backticks while
  PR #4 is in flight; research in the data-source documents' style; the roadmap proposed, never
  edited; and why this index is a hand-kept table while the handoff and friction indexes are
  derived.
- `docs/CLAUDE.md`: an `ideas/` row in "What lives where", and the word *idea* in the paragraph
  that tells the record's kinds apart.
- `docs/ideas/concert-and-release-calendar.md` at `status: shaped`. The owner's words first.
  Three kinds of entry and an iCalendar feed as the output. The fit with
  `docs/02-domain-model.md`: a concert is by a creator the log knows, a release is of an item the
  log does not yet have (kinds `game` and `film`), and a future-dated occasion is not an event —
  so one new table in the atlas's two-reference pattern, feed columns a cache and the owner's
  marks the record, each feed a source adapter under the daily poller. Sixteen feeds and six
  bookmark sources in tables, each claim cited to one of 58 sources read on 2026-10-05 and marked
  verified, reported or inferred. Nine open questions, the dependencies, a SQL and a Python
  sketch, a size, and three roadmap options with a leaning.
- No edits to `docs/00`, `07`, `08`, the overlay or the root `CLAUDE.md`; no code; no issues.

## How it was verified

- Three research agents read the feeds' pages in parallel, one per column — concerts; games and
  bookmarks; films and the calendar format. The author re-read the pages the leaning turns on:
  Songkick's closure, Bandsintown's terms, Ticketmaster's quota and terms, TMDB's terms and
  release types, Steam's Web API terms, RAWG's plans, JamBase's plans and terms, and the Twitch
  agreement's 24-hour cache clause, read in the browser because the fetch tool got only its
  header. Two live calls to Steam's store endpoint, which carries no personal data, confirmed
  the response shape. Every re-read claim held.
- `python scripts/check_docs.py` and `python -m unittest discover scripts/tests` pass on the
  branch; the pre-commit hook ran both.
- Every prose line is at most 100 columns; table rows and bare URLs are not wrapped, as in the
  data-source documents.

## What remains open

- The root `CLAUDE.md`'s "Where things are" table has no `docs/ideas/` row. The coordinator's
  consolidation PR owns that file.
- `docs/ideas/CLAUDE.md` and the idea name `docs/02-domain-model.md` and `ADR-0003` in backticks;
  once PR #4 merges they can become links.
- The idea's *Not verified* list, chiefly: Ticketmaster's rate limit (5 or 2 a second), JamBase's
  German coverage, which of IGDB's FAQ and the Twitch agreement governs storage, Google
  Calendar's refresh interval, and whether Eventim's affiliate programme admits a private site.
- If the idea is adopted, its feed tables outgrow an idea file and move to
  `docs/investigations/` or a `01`-style data-source document, as `docs/ideas/CLAUDE.md` says.

## Needs a decision

- Where the idea sits: a bullet in M2, its own milestone between M2 and M3 (the leaning), or M4.
  The roadmap changes only when the owner chooses.
- The idea's first three open questions, which decide its shape: where "within reach" is, which
  bands, and which stores and films.
- Whether scraping Eventim's public pages is acceptable: Germany's largest ticket seller has no
  API, and `docs/00` excludes scraping only a service's *private* pages.

## What carried it

The domain model's own line between cache and record (`docs/02` §4). Every feed's retention
clause — six months, thirty days, twenty-four hours, "reasonable periods" — landed on a
distinction the model had already drawn for YouTube, so the terms shaped one sentence of design
rather than a section each. The moment was reading TMDB's terms, §1.C.
