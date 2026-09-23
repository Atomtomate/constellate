# 07 — Roadmap

> **Exploratory plan.** Ordering is the useful part; nothing here has an estimate yet.

*Last updated: 2026-09-23*

Ordered by dependency, not by date. Written on the day the repository was created and
reordered the same day, when the owner named the tracker as the first priority. The GitHub
milestones mirror the headings here, and `scripts/check_board.py` says when they do not.

---

## M0 — Foundations

The repository, the agent fleet and the written plan — no product code.

- Repository on GitHub, the agent fleet mounted as a submodule, the overlay, the hooks and
  the record scripts — **done** *(2026-09-23, the first commit)*.
- The name — **done** *(Constellate, confirmed by the owner 2026-09-23)*.
- The scope in [00](00-vision-and-scope.md) corrected by the owner.
- The data sources researched (Q-D): how Spotify's and YouTube's history is obtained,
  backfilled and kept current, with what fields and what limits, as
  `01-data-sources-spotify.md` and `01-data-sources-youtube.md`.
- The domain model sketched — an event, an item, a creator, and the room the atlas needs
  later (Q-C) — as `02-domain-model.md` — **done** *(2026-09-23, with ADR-0003, the
  ingestion seam)*.
- The stack decided (Q-B), as an ADR, and with it the file-ownership map in
  `.claude/agents.local.md` that the implementation agents need before any of them can run —
  **done** *(2026-09-23, ADR-0002)*.

**Done when:** the questions above have answers written down, and an implementation agent
can be briefed against an ownership map.

---

## M1 — The tracker

The owner's first priority: what was listened to and watched, when, and for how long.

- Spotify listening history into the store: backfill from what Spotify already holds, then
  ongoing capture, each play with track, artist, album, start time and duration.
- YouTube watch history into the store the same way: video, channel, start time, duration.
- A timeline of both, and totals by day, week and month, and by artist, channel, track and
  video.
- Private, single user; the owner signs in.

**Done when:** a week of real listening and watching is in the log with nothing typed, and
the totals match what the owner remembers.

---

## M2 — The collection

The atlas begins: the things the owner rates, on top of the log.

- Mark an item a favourite, rate it, note it, give it themes; the item is the same one the
  log already knows.
- Websites as a source: capture a site or a page with creator and themes.
- Browse and search by theme, creator, source, time and rating.

**Done when:** the owner's existing favourites are in, and a new one goes in from a phone in
under thirty seconds.

---

## M3 — Constellations and recommendations

The two questions the atlas exists for.

- Constellations: a named group of items or creators with its reason written down; found
  by theme, by time, by member.
- Recommendation lists: named, ordered, built from the collection, shareable read-only by
  link.

**Done when:** the next "what do you recommend?" is answered with a link.

---

## M4 — The apps

What "a system of apps" means is Q-F; this milestone is a placeholder for its answer.
Nothing here is designed until M1 has proved the model.

---

## Sequencing rules

1. **The log before the atlas.** A favourite is a flag on an item the log knows; building
   the atlas first would build the item model twice.
2. **Sources are adapters.** Every source produces the same event and the same item; the
   first source decides nothing the second cannot use.
3. **Backfill before live capture.** The export the owner can request today holds years;
   the poller holds what happens from the day it runs. The first shows whether the model
   holds before the second is built.
4. **Ship M1 before starting M2.** A half-finished log plus a half-finished collection is
   how a project like this dies.
