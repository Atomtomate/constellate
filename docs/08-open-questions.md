# 08 — Open Questions

> **Exploratory plan.** Answered questions move to the bottom rather than being deleted.

*Last updated: 2026-11-04*

## Still open

### Q-E — Where does it run?

**The store's half is answered** *(2026-10-19)*. The owner, asked "Q-E's store half, due before the
first migration ends the free switch to SQLite: where does Postgres run for the owner's own data?
(The public URL and the rig's proxy can stay open.)", chose "The sibling PC, as a service
(Recommended)": "The same machine the boardgame tracker's Postgres already runs on, Postgres
installed as a Windows service rather than Docker so it survives reboots unattended; the scheduled
poller runs there too." No ADR: ADR-0002 already requires "a service that starts with the machine,
wherever Q-E puts it", so the store stays Postgres and its SQLite fallback falls away.

**Still open: the public URL and the rig's proxy.** The sibling project serves from a PC the owner
controls; the same rig could serve this.

**What the chosen host must still show**, for what the decisions so far require of it:

- **Database backups kept at most five days**, with the plain-format export of the log as the
  long-term copy, because a backup holds cache rows and live plays past what the services'
  terms allow (`02-domain-model.md` §4).
- **Encryption at rest**, if the Data Portability API carries YouTube's daily capture: its
  policy requires it (`02-domain-model.md` §4; `01-data-sources-youtube.md` §3.2).
- **A scheduler that fires the poller every few minutes, all day**, as a bounded sampling run
  (the owner, 2026-09-23; ADR-0002's Consequences), registered to run whether or not the owner
  is signed in, with the daily jobs beside it. If the Spotify poller runs, the owner signs in
  to Spotify every six months (`01-data-sources-spotify.md` §2).
- **From M3, the calendar's feed reachable from the internet**, because Proton Calendar and
  Google Calendar fetch a subscribed calendar from their own servers (the calendar idea's
  "How it fits the model", inferred there).

### Q-F — What is "a system of apps"?

A phone app for capturing; a browser extension for capturing the current page or video; a
share-sheet target; a desktop app. Each is a different cost, and none is designed until the
website has proved the model (M5). The extension's role has narrowed: if the Data Portability
API's spike passes, it captures what was watched and when without one, which leaves the
extension the route to seconds watched on desktop (`01-data-sources-youtube.md` §6).

**Deferred here, 2026-11-04: how a client that is not a browser presents a credential.** ADR-0004
gives the browser an HttpOnly session cookie and leaves this undecided ("Not decided here"). PR
#27's direction review leaned to deciding it with the extension, and the M1 plan's re-cut
(`reviews/m1-plan/impl-director-check-3.md`) deferred it so: the director's call, not the owner's.
The one constraint Lane 3 carries meanwhile is that a session is found by its token, and the
cookie is only the browser's way of carrying it, so a token borne in a header later is additive
and needs no migration.

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
already proven. The map is in `.claude/agents.local.md`; where the store runs is Q-E's.

**Q-C — What is the domain model?** → **One event per play, resolved from kept observations;
one item per source identity** *(2026-09-23)* → ADR-0003. The model is
[`02-domain-model.md`](02-domain-model.md). Every source's record of a play is an immutable
observation, and the play is one event whose item, start and duration are resolved from its
observations by precedence. An event references its item rather than copying it; a creator is
not an item; a theme and a constellation share a shape, not a meaning. Items are kept per
source identity, merged within a service only on an identifier it gives (a Spotify ISRC) and
never across services, the owner's choice of 2026-09-23. What the model leaves open is its §8.

**Q-D — How does the history get out of Spotify and YouTube?** → **The two research documents'
paths, Spotify's as the owner chose them** *(2026-09-23; Premium confirmed 2026-10-05)*. The
documents are [`01-data-sources-spotify.md`](01-data-sources-spotify.md) and
[`01-data-sources-youtube.md`](01-data-sources-youtube.md). **Spotify**, as the owner chose: the
extended streaming-history export is the record; Last.fm's scrobbles of Spotify are the live tail
and the backbone, which work with no Spotify app; the Web API playback poller is optional on top,
for measured listened time, its policy risk accepted. The log never depends on the poller.
**YouTube**, the research's recommendation, which no owner decision has changed: Takeout is the
backfill, the Data Portability API the daily capture (scheduled Takeout if its spike fails),
`videos.list` gives lengths as a cache refreshed within 30 days, and a browser extension comes
later, only for seconds watched on desktop — sooner if the spike fails, since scheduled Takeout runs
up to two months late (Q-F). "How long" is time actually played where a source measures it, and each
event's basis says when it is not (`02-domain-model.md` §1). No ADR: each path is a source adapter
under ADR-0003's seam.

**Does the log need an owner column from day one?** → **Yes** *(2026-11-03)*. The owner chose "Add
it now", against the director's leaning; [`02-domain-model.md`](02-domain-model.md) §8 quotes the
ask and what it costs, and its §8 states which tables carry it, what it holds and what uniqueness
does with it, settled by the director within the owner's words (2026-11-04). No ADR: none rules
the column out, and `00-vision-and-scope.md` defers multiple users, not the column.
