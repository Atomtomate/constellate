# 08 — Open Questions

> **Exploratory plan.** Answered questions move to the bottom rather than being deleted.

*Last updated: 2026-10-06*

## Still open

### Q-E — Where does it run?

The tracker's poller has to run somewhere all day. The sibling project serves from a PC
the owner controls; the same rig could serve this. Open until M1 needs it. Whatever host is
chosen has to give what the decisions so far require of it:

- **A database server that starts with the machine**, because the poller fires unattended.
  Where that cannot be promised, the store is SQLite instead, a switch that costs nothing
  before the first migration (ADR-0002, Consequences).
- **Database backups kept at most five days**, with the plain-format export of the log as the
  long-term copy, because a backup holds cache rows and live plays past what the services'
  terms allow (ADR-0003's amendment; `02-domain-model.md` §4).
- **Encryption at rest**, if the Data Portability API carries YouTube's daily capture: its
  policy requires it (`02-domain-model.md` §4; `01-data-sources-youtube.md` §3.2).
- **A scheduler that fires the poller every few minutes, all day**, as a bounded sampling run
  (the owner, 2026-09-23; ADR-0002), registered to run whether or not the owner is signed in,
  with the daily jobs beside it. If the Spotify poller runs, the owner signs in to Spotify
  every six months (`01-data-sources-spotify.md` §2).

### Q-F — What is "a system of apps"?

A phone app for capturing; a browser extension for capturing the current page or video; a
share-sheet target; a desktop app. Each is a different cost, and none is designed until the
website has proved the model (M5). The extension's role has narrowed: if the Data Portability
API's spike passes, it captures what was watched and when without one, which leaves the
extension the route to seconds watched on desktop (`01-data-sources-youtube.md` §6).

### Q-G — What does the calendar add to the model?

The calendar (M3) brings what the log has never held: a future-dated **occasion**, a concert
or a release. It is not a log event — it has not happened, nobody measured it, and its date
moves — and it references a creator (a concert) or an item (a release). Whether it is one noun
or two, and what the ICS feed reads, is decided with `02-domain-model.md`'s revision when M3
starts. The argument so far is the idea file's "How it fits the model" and "Open questions"
([`ideas/concert-and-release-calendar.md`](ideas/concert-and-release-calendar.md)).

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

**Q-B — Which stack?** → **The sibling's stack** *(2026-09-23)* → ADR-0002. The board-game
tracker's FastAPI, SQLAlchemy, Alembic and Postgres, with a committed OpenAPI contract and a
React + Vite + TypeScript client; the poller a one-shot command fired by the OS scheduler.
Chosen by the owner over a Python-only stack with pages rendered on the server, TypeScript end
to end, and the same stack on SQLite, chiefly because the fleet's file-ownership map for it is
already proven. The map is in `.claude/agents.local.md`; where the store runs is still Q-E's.

**Q-C — What is the domain model?** → **One event per play, resolved from kept observations;
one item per source identity** *(2026-09-23)* → ADR-0003. The model is
[`02-domain-model.md`](02-domain-model.md). Every source's record of a play is an immutable
observation, and the play is one event whose item, start and duration are resolved from its
observations by precedence. An event references its item rather than copying it; a creator is
not an item; a theme and a constellation share a shape, not a meaning. Items are kept per
source identity, merged within a service only on an identifier it gives (a Spotify ISRC) and
never across services, the owner's choice of 2026-09-23. What the model leaves open is its §8.

**Q-D — How does the history get out of Spotify and YouTube?** → **The two research
documents' paths, Spotify's as the owner chose them** *(2026-09-23; Premium confirmed
2026-10-05)*. The documents are
[`01-data-sources-spotify.md`](01-data-sources-spotify.md) and
[`01-data-sources-youtube.md`](01-data-sources-youtube.md). **Spotify**: the extended
streaming-history export is the record; Last.fm's scrobbles of Spotify are the live tail and
the backbone, which work with no Spotify app; the Web API playback poller is optional on top,
for measured listened time, its policy risk accepted. The log never depends on the poller.
**YouTube**: Takeout is the backfill, the Data Portability API the daily capture (scheduled
Takeout if its spike fails), `videos.list` gives lengths as a cache refreshed within 30 days,
and a browser extension comes later, only for seconds watched on desktop. "How long" is time
actually played where a source measures it, and each event's basis says when it is not
(`02-domain-model.md` §1). No ADR: each path is a source adapter under ADR-0003's seam.
