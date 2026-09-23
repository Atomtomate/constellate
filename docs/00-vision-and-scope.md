# 00 — Vision & Scope

> **Exploratory plan.** Everything here is a sketch to argue with, not a specification.
> Settled choices live in [ADRs](adr/); everything else is provisional, and all of it was
> written on the day the repository was created, from two short messages of brief.

*Last updated: 2026-09-23*

## The brief, in the owner's words

> I want to build a system of apps and a website that tracks my favorite YouTube videos,
> music and websites. I routinely get asked for recommendations or look for past groups of
> creators or artists that are thematically linked. This is the very broad scope.

And, the same day, the first priority:

> First things: I need tracker for spotify, youtube. what I watch/listen to how long and
> when.

Everything below is derived from those two paragraphs, and the owner corrects it.

## Long-term vision (the thing we are steering toward, not building now)

Two layers, the second standing on the first:

1. **The log.** A durable, automatic record of what the owner listens to on Spotify and
   watches on YouTube — which track or video, by whom, when, and for how long — kept for
   years, on infrastructure the owner controls, and never dependent on either service
   keeping it for them.
2. **The atlas.** On top of the log, the things the owner rates — videos, music,
   websites — and the **links between them**: a theme, a scene, an era, a "these three all
   did that thing around then". It exists to answer two questions fast:
   - **"What would you recommend?"** — for a person, a mood or a topic: a list that can be
     handed over, not retyped from memory.
   - **"Who were those creators again?"** — the group of channels, artists or sites that
     were thematically linked, found by the theme or the time rather than by a name.

Reachable from a website and from whatever "a system of apps" turns out to mean (Q-F in
[08](08-open-questions.md)).

## What "v1" means

**The tracker** — the owner's stated first priority. A private website where the Spotify
listening history and the YouTube watch history arrive on their own, with timestamps and
durations, and can be read back as a timeline and as totals: per day, week or month; per
artist, channel, track or video.

The atlas — favourites, themes, constellations, recommendation lists — comes after, and is
designed so that a log entry and a favourite are the same *item* seen twice.

## In scope for the first release (proposed)

- One user: the owner. No accounts beyond that.
- **Spotify**: every play, with track, artist, album, when it started and how long it was
  listened to — backfilled from what Spotify already holds, then kept current.
- **YouTube**: every video watched, with title, channel, when and how long — backfilled
  from what Google already holds, then kept current.
- A timeline of both, and totals by period and by creator.
- Capture is automatic where a service allows it and an import where it does not; how
  each is done is Q-D's answer and the subject of `01-data-sources-spotify.md` and
  `01-data-sources-youtube.md`.

## Explicitly out of scope for the first release (proposed)

Listed so they can be cut without debate later, and so nobody quietly builds them:

| Deferred | Why it is safe to defer |
|----------|-------------------------|
| Favourites, ratings, themes, constellations, recommendation lists | The atlas layer; M2 and M3. The log's item model has to leave room for them, and that is the whole cost today. |
| Websites and browsing history | Named in the brief, but not in the first priority. An item that is a website is one more source once the model exists. |
| Playback of anything | The item links out; the source plays it. |
| Automatic recommendations | The owner is the recommender; the tool remembers. A model can be laid over a well-tagged log later and constrains nothing now. |
| Multiple users, social features, a public site | Nothing in a private single-user log prevents them later; an owner column from day one is the whole cost, and whether to pay it is in [08](08-open-questions.md). |
| Native mobile apps | The website first; what the apps are is Q-F. |
| Scraping a service's private pages | Imports use each service's export or API, or a file the owner already has. |

## Non-goals, permanently

- Not a media player, and not a download tool.
- Not a public database or a competitor to any existing service.
- Not a social network: sharing, when it comes, is a read-only list handed to a person.

## Success criteria for v1 (proposed)

- A day's listening and watching is in the log by the next morning with the owner having
  typed nothing.
- "How long did I listen to X last month?" and "what did I watch on that evening?" are
  answered by the site, correctly, in one screen.
- The whole log can be exported, in a plain format, at any time.
- Adding the atlas later requires no rewrite of the log: a favourite is a flag on an item
  the log already knows.
