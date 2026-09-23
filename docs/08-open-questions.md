# 08 — Open Questions

> **Exploratory plan.** Answered questions move to the bottom rather than being deleted.

*Last updated: 2026-09-23*

## Still open

### Q-B — Which stack?

Undecided, and nothing is built until it is. What the tracker needs is a scheduled job that
talks to two APIs, a store that holds years of events, and a website that reads them back.
Known from the sibling project: the owner is fastest in Python and already has a FastAPI +
Postgres + React/Vite stack that the fleet's implementation agents know how to cut across.
Reusing it is the cheap leaning; the brief's "system of apps" may argue for something else
(Q-F). Decided by ADR, and that ADR also writes the file-ownership map in
`.claude/agents.local.md`.

### Q-C — What is the domain model?

The nouns the brief implies, the tracker's first: an **event** (one play or one watch — an
item, a start time, a duration, the source it came from), an **item** (a track, an album, a
video, later a website), its **source** (Spotify, YouTube, later the web), a **creator**
(artist, channel, later author or site). The atlas adds a **theme**, a **constellation**
(a group of items or creators with its reason) and a **recommendation list**. Open:
whether an event references an item or carries its own copy of the item's fields at the
time; whether a creator is an item in its own right; whether a theme and a constellation
are one thing at two sizes; how an item that exists on two sources is one item. Answered
in `02-domain-model.md` when it is written, and not before the two data-source documents
(`01-data-sources-spotify.md`, `01-data-sources-youtube.md`) say what fields the sources
actually give.

### Q-D — How does the history get out of Spotify and YouTube?

For each source, two paths are needed: a **backfill** of what the service already holds,
and **ongoing capture** from the day the tracker runs. Leanings to verify, not facts:

- **Spotify.** The Web API's recently-played endpoint returns a short tail of plays with
  their start times but not how long each was listened to, so it must be polled often to
  miss nothing; the account's privacy page offers an extended streaming-history export
  that holds every play for the life of the account with milliseconds listened, but arrives
  by email days or weeks after it is requested.
- **YouTube.** The Data API has no watch-history endpoint at all. Google Takeout gives the
  watch history as a file with titles, URLs and timestamps but no durations, so a duration
  is either the video's length from the Data API or a guess. Live capture with a real
  duration needs something running where the watching happens — a browser extension or
  userscript — which is also the only route to "how long" rather than "how long the video
  is".

What "how long" means — milliseconds actually listened, or the length of the track or
video — is decided per source by what it can give, and stated in that source's document:
`01-data-sources-spotify.md` and `01-data-sources-youtube.md`, one per source so the two
can be researched at once. The research writes them; the leanings above are what it
starts from, and every claim in them is dated and points at the page that says so.

### Q-E — Where does it run?

The tracker's poller has to run somewhere all day. The sibling project serves from a PC
the owner controls; the same rig could serve this. Open until M1 needs it.

### Q-F — What is "a system of apps"?

A phone app for capturing; a browser extension for capturing the current page or video —
which Q-D may need for YouTube anyway; a share-sheet target; a desktop app. Each is a
different cost, and none is designed until the website has proved the model (M4).

### Smaller, for later

- **Should the generic record scripts move into the fleet repository?** `scripts/` is a
  copy of the sibling project's with its product checks left out, and two copies drift.
  The fleet's own rule is that project-measuring tooling stays with the project; these
  measure the record rather than the product, which argues for the move.
- **Does the log need an owner column from day one?** One user today; the column is
  cheap, the retrofit is a migration.

---

## Answered

**Q-A — Is the name Constellate?** → **Yes** *(2026-09-23)*. Confirmed by the owner the
day the repository was created; the alternatives offered were Fundgrube, Mixtape,
Wunderkammer and Cairn. No ADR: a name decides nothing an ADR would.
