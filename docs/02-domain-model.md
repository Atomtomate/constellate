# 02 — Domain model

> **A sketch to argue with, not a specification.** This answers Q-C in
> [08](08-open-questions.md) for the owner to accept or correct. It builds on three documents on
> open pull requests when it was written — `01-data-sources-spotify.md`,
> `01-data-sources-youtube.md` and the stack ADR (`0002-the-stack.md`, whose option A the owner
> has accepted) — and cites their findings by document, section and source number, so a claim
> can be traced to the page that made it. Two parts are decided: the ingestion seam, as
> [ADR-0003](adr/0003-the-ingestion-seam.md), and no merging of items across services, both
> chosen by the owner on 2026-09-23.

*Last updated: 2026-09-23*

## The model in brief

A play or a watch is an **event**. Every source that saw it contributes an **observation** of it,
kept as the source sent it, and the event's columns are resolved from its observations by
precedence: the export's measured milliseconds beat the poller's estimate, whichever arrived
first. An event references an **item** — a track, an episode, a video — which each source knows
by an **item ref**: a URI, a video id. An item is by one or more **creators**. What a catalogue
API says about an item — its length, its category, its ISRC — is a **cache** with a fetch date,
never a column of the log, so YouTube's 30-day rule is honoured by deleting rows no event
depends on. Spotify's rule against keeping its API data indefinitely is honoured the same way,
and by keeping the Web API's plays only until the owner's own export replaces them.

Q-C's four open points, answered:

- **Does an event reference an item or carry a copy of its fields?** It references the item. The
  copy as the source named it at the time — the title Takeout recorded that evening — is in the
  observation's raw record, so nothing is lost by not copying it onto the event.
- **Is a creator an item in its own right?** No. Nothing plays a creator, and an "item" that
  meant two things would put a kind test in every total. The atlas points at either (§5).
- **Are a theme and a constellation one thing at two sizes?** The same shape, not the same
  meaning (§5).
- **How is an item that exists on two sources one item?** Within one service, by an identifier
  the service gives; across services, it is not (§3).

## 1. The nouns and their fields

### What is a column, and what is JSON

A **column** is what a total, a filter, a join or a constraint reads, and it means the same for
every source. Everything else a source says is kept as the record it sent — `raw`, verbatim JSON
on the observation. Two reasons. A parser fix is then a re-derivation from stored records, not a
new export request, and Spotify's takes up to a month (`01-data-sources-spotify.md` §1, S3).
And promoting a field later is cheap: add a column, fill it from `raw` — a migration of one
table, no re-import. The fields most likely to be promoted are YouTube's `header` (YouTube Music
or YouTube, if listening and watching are totalled apart) and Spotify's `incognito_mode`.

What stays in `raw` only: Spotify's `reason_start`, `reason_end`, `shuffle`, `skipped`,
`offline`, `incognito_mode`, `platform`, `conn_country`, `ip_addr`, the API's `context` (the
playlist or album a play came from); Takeout's `header`, `subtitles`, `activityControls`; the
extension's playback rate.

### Event

One play or one watch. The row every total and the timeline read.

| Field | Kind | Holds |
|-------|------|-------|
| `item_id` | column | The item played. Null only when no observation names one (below). |
| `started_at` | column | UTC, from the observation that saw the start most directly. |
| `duration_ms` | column | Time actually played. Set only when an observation measured it. |
| `duration_basis` | column | What the observations say about the duration: see below. |

**The duration's provenance.** The brief's three kinds — measured, the item's length, unknown —
are what a *total* reports. The event stores what its *observations* said instead, because
whether an item's length is known changes as the cache fills and empties, and the log must not
change with it (§4). The item's length also splits in two, because the sources give two
different reasons to use it:

| Basis | The observations say | A total reads |
|-------|----------------------|---------------|
| `measured` | how long it played | `duration_ms` |
| `to_end` | it played to its end | the cached length, as an estimate |
| `start_only` | only that it started | the cached length, as an upper bound |

Which source gives which basis is the source table's "Gives" column (below).
`to_end` rests on a report, not on Spotify's word. Last.fm's Spotify connection reads Spotify's
`recently-played` (S29), which reportedly lists only plays that reached, or nearly reached, their
end (`01-data-sources-spotify.md` §2, S24). With no cached length, a `to_end` or `start_only`
event reads as unknown. So a total is three
numbers and a count: measured time, estimated time, upper-bounded time, and events with no
number. The YouTube document's estimate `min(length, time until the next watch)`
(`01-data-sources-youtube.md` §5) is one way to read `start_only` events. It is computed when
read, because a backfill can insert an event between two others.

**The event carries no source.** An event may have three observations from three sources; which
one is "its" source has no single answer. The observations carry theirs, and a total per service
reads the item's service.

**An event with no item.** A removed or private video appears in Takeout with a generic title and
no usable URL or channel (`01-data-sources-youtube.md` §2, S9). The watch happened, at a known
time, so it is an event, with a null item. The timeline shows it, per-item totals cannot, and a
total says how many such events it left out.

### Observation

One source's record of one event: the draft an adapter produced (§2), stored. Immutable once
written, and deleted only with its ingest run or where its source's terms require it (§4). It is
the ground truth the event's columns are resolved from, so changing a precedence or the way a
start is derived is a recompute over stored observations.

Fields: its event; its source and ingest run; `record_key`, unique, the upstream record's
identity (§2); the item ref the source named, if any; the source's own `started_at`,
`duration_ms` and `duration_basis`; and `raw`.

### Item

A track, a podcast episode, an audiobook chapter, a video; later a web page. Fields: `service`,
`kind`, `title`, and `detail`, a JSON column of labels no total reads (an album name, a show
name).

The **title** comes from the owner's own records: the export's track name, or Takeout's title with
the localised "Watched" stripped (`01-data-sources-youtube.md` §2). It never comes from a
catalogue lookup, because a catalogue's data expires (§4). The one stand-in: a Spotify track the
Web API or Last.fm reported before any export named it carries that title until the export's
replaces it.

The **length** is not a field of the item. It is a cached fact with a fetch date (§4).

**Album.** Q-C lists the album among the items. M1 needs it only as a label on a track, and the
export gives only its name, with no identifier (`01-data-sources-spotify.md` §1), so it goes in
`detail`. When the atlas wants to favourite an album, the album becomes an item kind with a
track-to-album link. That adds a table and leaves the event table alone.

### Item ref

An identity by which a source names an item: a namespace and a value, unique together.
Namespaces to start with: `spotify:track`, `spotify:episode`, `spotify:chapter`, `youtube:video`,
and `lastfm:track` if Last.fm is a source (§3).
An item has one ref or more. Merging two items re-points one's refs to the other (§3).

### Creator

An artist, a channel, a podcast's show; later an author or a site. Fields: `service`, `kind`,
`name`. Its **creator refs** work like item refs: `youtube:channel`, and `spotify:artist-name`,
the identity of last resort (§3). Spotify's artist URIs come only from the Web API, so they are
catalogue facts in the cache (§4), not refs. An **item–creator** link holds the
role (artist, album artist, channel, show) and the position, because a track has several artists
and their order is part of the credit.

A YouTube video's channel id and name come from the owner's Takeout record, the tail of
`subtitles[0].url` (`01-data-sources-youtube.md` §2), so channels need no API.

### Source

One row per path into the store. The owner chose Spotify's paths on 2026-09-23 (§4):

- the export is the record;
- Last.fm's scrobbles are the live tail, and the backbone that must work with no Spotify app;
- the Web API's playback poller is optional, on top, for measured listening time.

The tracker reads no `recently-played` of its own, because Last.fm's connection already reads it
(S29). The poller's app also makes the catalogue lookups an ISRC comparison needs (§3).

| Source | Service | Gives | Cursor |
|--------|---------|-------|--------|
| `spotify-export` | Spotify | observations, `measured` | none: files |
| `lastfm-scrobbles` | Spotify | observations, `to_end`, names but no URI | newest scrobble time |
| `spotify-poller` | Spotify | observations, `measured` ± Δ; catalogue facts | the open play |
| `youtube-takeout` | YouTube | observations, `start_only` | none: files |
| `google-portability` | YouTube | observations, `start_only` | end of the last export window |
| `youtube-extension` | YouTube | observations, `measured` | none: it pushes |
| `youtube-data-api` | YouTube | catalogue facts only | none |

The cursor is JSON because its shape differs per source and only that source's adapter reads it.

### Ingest run

One row per run of an adapter: a file import, a poll, an extension batch. It records when the run
started and finished, how it ended, the file's hash for an import, and what it counted (new,
duplicate, matched). Three things come from it: the last successful poll per source, which the
stack ADR requires to be stored and shown; an import that went wrong is undone by deleting its
observations and re-resolving their events; and a file offered twice is recognised by its hash
before it is parsed.

## 2. The ingestion seam

The decision this section details — one event per play, resolved by precedence from immutable
observations — is [ADR-0003](adr/0003-the-ingestion-seam.md), accepted by the owner on
2026-09-23. Its rules live there: the precedence, how matches pair, the cursor's transaction and
when an observation may be deleted. What follows is their detail, not a second statement.

### The draft event

Every adapter produces the same draft. The adapter knows HTTP or a file format and never SQL
(the stack ADR's appendix). The draft carries everything the ingestion service needs, so the
service never has to go back to the source.

| Field | Holds |
|-------|-------|
| `source` | Which adapter produced it. |
| `record_key` | The upstream record's identity, in that record's namespace (below). |
| `item_ref` | Namespace and value, or none when the record names no item. |
| `item_hint` | Kind, title, album, creator refs and names, as the record gives them. |
| `started_at` | UTC. Observed, or derived: the export's is `ts − ms_played`. |
| `duration_ms` | The time measured, or none. |
| `duration_basis` | `measured`, `to_end` or `start_only`. |
| `raw` | The record as sent, less the catalogue facts below. |
| `catalogue` | Length, ISRC, per-track artists, when the response carried them. |

### What the service does with one

In one transaction per draft, or per batch of them:

1. **Drop it** if its `record_key` is already stored: the same record, delivered again.
2. **Resolve the item**: find the ref, or create the ref and its item from `item_hint`; the same
   for the creators.
3. **Find the event it also sees** (below), or create one.
4. **Store the observation**, and re-resolve the event's columns from all its observations.
5. **Write `catalogue` to the cache**, never to the log (§4).

### Two kinds of duplicate

**The same record, delivered twice**, has the same `record_key`, and step 1 drops it. The key is
the upstream record's, not the path's. Takeout and the Data Portability API are two paths to one
Google store (`01-data-sources-youtube.md` §1, inferred there), so both produce
`google-watch:<video id>@<time>` for the same watch — provided the two give the same `time` to
the millisecond, which the first Portability export beside a Takeout will show. A re-requested
Spotify export repeats every earlier play as `spotify-export:<uri>@<ts>`. Last.fm's overlapping
reads repeat `lastfm:<artist>|<title>@<start>`. Last.fm occasionally scrobbles one play twice
(Spotify §3, S29): if the two copies carry the same start, the key drops the second. If they do
not, the export's one-to-one pairing leaves the extra one unmatched, and the ingest run counts
it like any other miss (§4).

**The same play, seen by two streams**, arrives as two different records with two keys. Step 3
matches them to one event:

| Pair | Match on | Within (to tune on real data) |
|------|----------|-------------------------------|
| export and Last.fm | title, artist and time | scrobble start within 1 min of `ts − ms_played` |
| export and poller | the track URI | the poller's end within 2Δ + 1 min of `ts` |
| Last.fm and poller | title, artist and time | scrobble start within Δ + 1 min of the poller's |
| Takeout or Portability, and extension | the video id | minutes |

A scrobble's timestamp is "the time the track started playing" (Spotify §3, S30), so it is
compared with a start. How pairs are chosen is ADR-0003's: one-to-one and in order, with Takeout
and Portability counting as one stream. The pairing is in order, not nearest first. When a track
plays twice back to back, one stream's end of the first play sits on the other stream's start of
the second, and nearest first pairs the wrong two. Where two records share no ref — Spotify
relinked the track (Spotify §4, S20), or the record is a Last.fm scrobble, which names no URI
(Spotify §6) — the match falls back to title, artist and time. The export–poller and YouTube
windows are the data-source documents' own (Spotify §4, YouTube §5). The two Last.fm windows are
this model's. All of them are inferences, to be tuned against the owner's first weeks.

### The source cursor

A source cursor is the position up to which a source's records are stored, so the next run asks
only for what is newer: the newest scrobble time, passed as `user.getRecentTracks`'s `from`, or
the Data Portability API's `start_time` (Spotify §3, S31; YouTube §3.2). It lives on the source
row and commits with the observations it covers (ADR-0003). A run stores its drafts oldest
first, so a crash leaves the cursor at the last one stored, and the next run asks for everything
after it. Stored newest first, a crash after the first draft would move the cursor past the
older plays of the same poll, and they would never be asked for again.

File imports have no cursor, because a file is complete and step 1 absorbs the overlap. The
extension pushes, so it has none either. The playback poller's cursor is its open play — item,
start, milliseconds so far, last sample. A crash loses the open play. If it was completed,
Last.fm still has it; if not, the next export does.

The Spotify sign-in date, which starts a six-month clock (Spotify §2, S13), is source state
beside the cursor. The tokens themselves are secrets and belong in none of these tables.

## 3. Identity across sources

**One item per source identity, merged only on an identifier the service gives, never across
services.** The owner chose no cross-service merging on 2026-09-23, with
[ADR-0003](adr/0003-the-ingestion-seam.md)'s acceptance.

- **The same ref is the same item, always.** A Spotify track, episode or chapter URI; a YouTube
  video id.
- **Two Spotify track URIs with the same ISRC are one item.** Relinking, reissues and regional
  editions give one recording several URIs (Spotify §1, §4). The export has no ISRC (S5, S34).
  The API's track object carries it in `external_ids`, restored in March 2026 (S21). It comes
  free with every play the poller sees; for export-only tracks it costs one `GET /tracks/{id}`
  each, which the poller's app makes. Without the poller there are no ISRCs, and no merges:
  relinked URIs stay two items, which splits a song's totals and loses no play. Until an ISRC
  arrives, the two URIs are two items. When it arrives, the second ref is
  re-pointed, its events are re-resolved, and the empty item is deleted. The merge is the
  tracker's own conclusion and stays. The ISRC is catalogue data and lives in the cache (§4),
  which may already have deleted the row an earlier URI's ISRC was in. So when a URI's ISRC
  arrives, the ISRCs of the items that share its title and album artist in the owner's records
  are fetched again and compared. That is usually none or one request, and it is the only way a
  relinked URI that turns up months later still finds its item. Whether a merge prompted by API
  data outlives a Spotify disconnect is one of the readings Spotify §6 leaves open; if it does
  not, the disconnect splits the ISRC merges too.
- **A Last.fm scrobble names a track by title and artist only**, so its ref is a name ref,
  `lastfm:track`. That ref points at the item an export already named with the same title and
  album artist, when exactly one did, and otherwise at a stand-in item. When the export arrives,
  precedence gives the event the export's item, and a stand-in left with nothing is deleted. A
  name ref never re-points a URI ref, so no two Spotify items are ever merged on a name.
- **A merge can be split.** Every observation keeps the ref it named, so a wrong merge is undone
  by re-pointing that ref and re-resolving its events. What does not split mechanically is an
  atlas row on the merged item (§8).

**Kept as two:**

- **The same song on Spotify and on YouTube Music.** No identifier joins them: none of the fields
  the YouTube document lists for `videos.list` is an ISRC (§4 there). A match on title and artist
  would be wrong often enough to corrupt the totals it merges. Kept apart, "how long on Spotify,
  how long on YouTube" stays answerable. The atlas can group them as a *work* later (§6).
- **A music video and its "Artist - Topic" upload** (YouTube §2, S13): two video ids, two items.
- **A remaster and its original**, when Spotify gives them different ISRCs, as it usually does.
- **A Spotify artist and the same artist's YouTube channel**: two creators, for the same reasons.

**The exception: creators known only by name.** The export names a track's creator only by the
album artist's name (Spotify §1, S34), and artist URIs are cache (§1). So the durable Spotify
creator is that name, a ref of last resort, `spotify:artist-name`, and it is what totals by
artist read. A featured artist is known only while the cache holds the track.
Two artists who share a name are one creator; the owner can correct that by hand, because an
item–creator link the owner sets is the owner's own record. A podcast's show is handled the same
way.

## 4. The enrichment cache, and what each service's terms allow

The line has three sides:

- **The owner's own records of their own activity are the log**, kept for the log's life: the
  Spotify export, Takeout, the Data Portability archive, and what the extension observes.
- **What a catalogue said about an item is the cache**: the YouTube Data API's `videos.list`,
  Spotify's `GET /tracks/{id}`, and the track objects inside Spotify's player responses.
- **The owner's Spotify plays as a live source reported them** — Last.fm's scrobbles and the
  Web API poller's observations — are in the log only until the export re-sources them (below).

The cache has one row per item ref, because a catalogue answers per identifier and two refs
merged into one item may differ in length. A row holds: its source, `fetched_at`, a status
(found, not found), `length_ms` as a column because totals read it, and a JSON payload for the
rest — category, ISRC, per-track artists, publish date.

| | YouTube Data API | Spotify Web API |
|-|------------------|-----------------|
| The rule | 30 days, then delete or refresh | not indefinitely; kept current; no period |
| Rows kept | every video the log names | only while an event or an ISRC check needs one |
| Refreshed | daily, rows over 25 days, 50 ids a call | by each live play; else one call per track |
| Deleted | at 30 days unless refreshed | once not needed; at 30 days unless refreshed |
| As a set | — | within 5 days of a disconnect, with its plays |

### YouTube: thirty days

YouTube's developer policies allow API data to be stored "not longer than 30 calendar days",
after which it is deleted or refreshed (YouTube §4, S27, verified 2026-09-23). It is honoured
three ways, and by the backups below:

- **Refresh**: a daily job re-fetches every row older than 25 days, 50 ids a call. That is 1,000
  units a month per 50,000 videos, a tenth of one day's quota (YouTube §4).
- **Delete**: a row not refreshed by day 30 — the video is gone, or the API was down for days —
  is deleted, not left stale.
- **Read**: a read treats any row older than 30 days as absent, so a stuck job cannot put
  expired data on a page.

Title, channel name and channel id are not in the cache: they come from the owner's own Takeout
record, which the YouTube document infers may be kept permanently (§4 there, inferred).

**Inherited from Data Portability.** Its policy requires encryption at rest and use limited to
features the user sees (YouTube §3.2, S23). If it becomes the capture path, the first is a
requirement on the host Q-E chooses.

### Spotify: not indefinitely, kept current, deletable as a set

Spotify's Developer Terms (version 10, effective 15 May 2025) were read for the Spotify document's
§6 (S38, S39; a reading, not legal advice). "Spotify Content" covers the catalogue facts and the
listening events the poller captures alike, and the events are also "Spotify Personal Data"
(S38 §II, Appendix A §1). Three clauses shape the model:

- "Do not store Spotify Content indefinitely", and use "reasonable efforts to ensure that any
  data you display to users is the most up to date data available [...] and to delete older
  data" (S38 §IV). **No period is given**, unlike YouTube's 30 days.
- When the user disconnects, the app deletes that user's Spotify Personal Data "within five (5)
  days" (S38 §V; Appendix A §5(c)), and it must offer "a working and easily accessible mechanism
  to disconnect" (S38 §V). On termination it deletes all Spotify Content "obtained through use
  of the Spotify Platform" (S38 §IX).
- The export does not come through the Platform — the APIs, SDKs and widgets — but from the
  privacy page, as the owner's right of access and portability (GDPR Article 20, S41). So its
  fields may be durable columns of the log. This is an inference, because the definition of
  Spotify Content ends "or by Spotify", which read literally covers the export (Spotify §6).

Read whole, the Developer Policy's §III goes further. On its text, both its analysis clause
("derived listenership metrics") and its integration clause ("integrated with streams or content
from another service") plausibly reach this tracker's totals and its timeline beside YouTube
(Spotify §6; S39 §III, S44). The research therefore names a path that avoids Spotify's developer
terms entirely: no Spotify app, the export for the record, and Last.fm for the live tail.

**The owner's choice, 2026-09-23: both.** The export is the record. Last.fm is the live tail and
the backbone, and it must work with no Spotify app at all. The Web API's playback poller is an
optional source on top, for measured listening time, and the owner accepts the policy risk for
it. The log must not depend on the poller: without it, the export and Last.fm still give every
play, with the durations arriving when the export does. Both live sources are re-sourced to the
export.

What the model does with that:

- **Catalogue facts** are cache, as for YouTube, but kept only while something needs them: the
  length of a `to_end` event the export has not yet re-sourced, or an ISRC comparison (§3). They
  exist only while the poller runs. The poller returns a full track object, and the adapter
  splits it: the URI and the play's times go into the observation, the track's length, ISRC and
  artists into the cache. Every play the poller sees therefore refreshes its track's row at no
  extra request. Without the poller, a scrobble's `to_end` event has no length and reads as
  unknown until the export measures it. A row still needed after 25 days is re-fetched, at one
  request per track (Spotify §2, S19) and within a quota one tool exhausted at about 600 a day
  (S28). A row no longer needed is deleted, and any row is deleted at 30 days unless refreshed.
  Thirty days is the model's reading of "kept current", not Spotify's number.
- **Live plays are re-sourced to the export.** An event that holds an export observation holds
  no Web API observation and no scrobble. When the export arrives, the ones already there are
  deleted; one that arrives after the export is not stored. The event's duration, start and item
  then rest on the owner's own record (Spotify §6). The cost is the poller's more exact start and
  its playlist context. A live observation that an export covering its date does not match is
  kept and counted in the ingest run, because a miss is likelier a matching error than a play
  Spotify forgot. Until the next export arrives, the weeks since the last one rest on live data.
- **Deletable as a set.** Every row a Spotify Web API source supplied is deleted in one
  transaction: its cache rows, its observations, and the events and items left with nothing else.
  That statement is the disconnect mechanism the terms require, and the answer to termination.
  An item an atlas row holds is not left with nothing. It stays, with a placeholder title in
  place of the API's, until an export names it, because the atlas row is the owner's own record.

### Last.fm: the live tail without a Spotify app

The owner connects Spotify to Last.fm, so Last.fm is the Spotify developer, and the tracker reads
the owner's scrobbles under Last.fm's API terms (Spotify §6, S43). Those terms
allow storage and non-commercial use. They cap Last.fm data held at 100 MB, require a credit and
a link to Last.fm, and require deletion on termination. The tail the model holds is weeks of
scrobbles, far below the cap, and it is re-sourced like the Web API's plays. A scrobble has a
start time and names but no URI and no duration. Its basis is `to_end`, inferred from Last.fm's
use of the Web API (Spotify §6), and the owner's first weeks can check that.

### Backups

A database backup holds whatever the log held when it was cut: cache rows past 30 days, and live
plays the export has since replaced. So database backups are kept at most five days, which is
inside both YouTube's 30 days and Spotify's five after a disconnect. What is kept longer is the
plain-format export of the log (00's success criteria). It holds the owner's own records and the
events they resolve, and it leaves out the cache and every live observation by construction.

### What the log never depends on

No event's existence, start, measured duration, item or creator depends on a cache row, or on
the Web API poller. Emptying the cache costs precision: `to_end` and `start_only` events lose
their lengths and read as unknown, and categories disappear. Stopping the poller costs live
measured time and ISRC merges. No play is lost either way. A Spotify disconnect, or leaving
Last.fm, is the one exception: the plays since the last export go with the live data, and return
when the next export arrives.

## 5. Room for the atlas

Every atlas table references the log, and no table of the log references the atlas. M2 adds
tables and alters none. Where an atlas row can point at an item or a creator, it carries two
nullable references and a check that exactly one is set. That keeps the database's referential
integrity, which a generic "target type and id" pair would give up.

**Favourite.** A row per favourited item or creator, with the date it was marked. It is a row, not
a column on the item, so the log's table never learns about the atlas. The vision's "a favourite
is a flag on an item the log already knows" still holds: the row exists or it does not.

**Rating.** One current value per item, dated. Whether past ratings are kept is M2's question.

**Note.** Free text on an item or a creator, dated, several per target. The place for "why this
one" when it is not yet part of a constellation.

**Theme.** A named label applied to many items and creators as they are met: "long-form video
essays", "Berlin techno". It is open-ended, and the atlas browses by it.

**Constellation.** A named, closed set of items and creators, with its reason written down and
often a period: "these three did that thing around then". It is found by theme, by time and by
member. Its members are as often creators as items, because "who were those creators again?"
asks about creators.

**Recommendation list.** Named and ordered, a note per entry, built from the collection, and
shareable read-only by an unguessable link whose token lives on the list.

**Theme and constellation, one thing or two (Q-C).** They share a shape — a named set of items and
creators — but not a meaning: a theme is a label applied as things are met, a constellation a set
assembled for a reason. A recommendation list is the same shape again, ordered. One `collection`
table with a kind and one membership table could hold all three; three tables would each say what
they are. The leaning is one shape, decided at M2 with the screens in view. Neither choice touches
the log.

## 6. Sanity check: a third source, and a fourth

**Websites.** The roadmap's M2 captures "a site or a page with creator and themes": the owner adds
it by hand, and it is an item with no events. A browsing history, from an extension, would add
events. Either way the new things are an item kind, `page`; a ref namespace, `url`; a creator
kind, `site` or `author`; and a source row. The event fits as it is. The start is the visit, and
the duration is either measured (time the tab had focus) or `start_only` (a history entry). A
page has no length, so `start_only` reads as unknown, which is the truth. Two costs land
elsewhere. URL identity is hard — query strings, fragments, redirects, tracking parameters — and
it is the item ref's problem, not the event's. Every page load would be an event, so browsing
might outnumber everything else tenfold. That is still well inside the stack ADR's scale, where a
decade of listening and watching is about half a million events.

**Another music service.** Its export or API becomes new source rows and new ref namespaces. Its
items are tracks with their own `service`, and its creators are artists with their own. Whatever
its records say about duration fits one of the three bases. The one bend: if it gives ISRCs, the
ISRC rule of §3 would suggest merging its tracks with Spotify's, and `item.service` refuses. If
the owner wants a song to total as one across services, that is a *work* above items: a new table
and a reference from the item, a migration of the item table. Merging the items themselves would
move `service` from the item to its refs, and that is the expensive change, because atlas rows
would have to follow (§8).

**Podcasts and audiobooks** are already a test the model passes: the Spotify export holds them
(Spotify §1, S1). They are episode and chapter items, with the show as a creator.

**Last.fm** is the smaller test of a source with names and no identifiers (§3). It costs a name
ref, a match on title, artist and time instead of on a ref, and a stand-in item until an export
names the track. The event table does not notice.

**The answer: yes, the event table survives both without a migration.** Its columns are an item,
a start, a duration and a basis, and none of them names a service or a format. What a new source
costs lands on the item: a kind, a ref namespace, and identity rules. Those rules — URLs for the
web, cross-service works for music — are where the next source will argue, and neither argument
reaches the event.

## 7. The core tables, sketched

```sql
-- A SKETCH to argue with, not a migration. Postgres; names and types are placeholders.

create table source (
  id           smallint primary key,
  key          text not null unique,        -- 'spotify-export', 'youtube-takeout', ...
  service      text not null,               -- 'spotify', 'youtube'
  cursor       jsonb                        -- shape per source; only its adapter reads it
);

create table ingest_run (
  id           bigint generated always as identity primary key,
  source_id    smallint not null references source,
  started_at   timestamptz not null,
  finished_at  timestamptz,
  outcome      text,                        -- 'ok', 'failed'; null while running
  file_sha256  text,                        -- file imports only
  counts       jsonb,                       -- new, duplicate, matched
  error        text
);

create table item (
  id           bigint generated always as identity primary key,
  service      text not null,
  kind         text not null check (kind in ('track', 'episode', 'chapter', 'video')),
  title        text not null,               -- from the owner's records, never a catalogue
  detail       jsonb not null default '{}'  -- album or show name: labels no total reads
);

create table item_ref (
  id           bigint generated always as identity primary key,
  item_id      bigint not null references item,
  namespace    text not null,               -- 'spotify:track', 'youtube:video', ...
  value        text not null,
  unique (namespace, value)
);

create table creator (
  id           bigint generated always as identity primary key,
  service      text not null,
  kind         text not null check (kind in ('artist', 'channel', 'show')),
  name         text not null
);

create table creator_ref (
  creator_id   bigint not null references creator,
  namespace    text not null,               -- 'spotify:artist-name', 'youtube:channel'
  value        text not null,
  primary key (namespace, value)
);

create table item_creator (
  item_id      bigint not null references item,
  creator_id   bigint not null references creator,
  role         text not null,               -- 'artist', 'album-artist', 'channel', 'show'
  position     smallint not null default 0,
  primary key (item_id, creator_id, role)
);

create table event (
  id             bigint generated always as identity primary key,
  item_id        bigint references item,    -- null: no observation names an item
  started_at     timestamptz not null,
  duration_ms    integer,                   -- set only when measured
  duration_basis text not null check (duration_basis in ('measured', 'to_end', 'start_only')),
  check ((duration_basis = 'measured') = (duration_ms is not null))
);
create index on event (started_at);
create index on event (item_id, started_at);

create table observation (
  id             bigint generated always as identity primary key,
  event_id       bigint not null references event,
  source_id      smallint not null references source,
  ingest_run_id  bigint not null references ingest_run,
  record_key     text not null unique,      -- the upstream record's identity
  item_ref_id    bigint references item_ref,
  started_at     timestamptz not null,
  duration_ms    integer,
  duration_basis text not null,
  raw            jsonb not null             -- the record as sent, less catalogue facts
);
create index on observation (event_id);

-- Catalogue facts, never read as log (section 4).
create table catalogue_cache (
  item_ref_id  bigint primary key references item_ref,
  source_id    smallint not null references source,
  fetched_at   timestamptz not null,        -- read as absent once 30 days old
  status       text not null,               -- 'found', 'not-found'
  length_ms    integer,
  payload      jsonb                        -- category, ISRC, per-track artists, ...
);
```

## 8. What stays open, and what is expensive to reverse

**Expensive to reverse**, most expensive first:

1. **One event per play, resolved from observations that are kept**: ADR-0003, accepted by the
   owner on 2026-09-23. Its Consequences say what reversing it would cost, and its Alternatives
   say why the other designs lost.
2. **An item is one source identity, merged within a service on ISRC only, never across
   services.** The owner chose no cross-service merging on 2026-09-23. It is cheap to change
   today, because refs make merges reversible. Once atlas rows exist it is expensive: a
   favourite, a rating or a constellation membership on a merged item has no mechanical owner
   when the item splits, and a cross-service merge would reshape every per-service total.

**In between.** The `record_key` scheme: a wrong key silently duplicates or drops records, and
re-keying is a recompute from `raw`. The log–cache line: moving a fact from the log to the cache
later is a purge of the log, so the model errs toward the cache, the cheap side.

**Cheap.** The basis vocabulary, which is recomputed from observations; promoting a `raw` field
to a column; a new source; a new item kind.

**Decided by the owner, 2026-09-23:** ADR-0003 and its amendment; no merging of items across
services; and Spotify's paths (§4). The export is the record, Last.fm is the live tail and the
backbone with no Spotify app, and the Web API poller is optional, on top, for measured time.

**Open:**

- **Spotify's terms**: the readings §4 leaves open, which Spotify has published nothing on. The
  owner accepts that risk for the poller alone.
- **The matching windows**: inferences from the data-source documents, to be tuned on the
  owner's first weeks of data (§2).
- **The owner's choices, which the model holds but does not make.** Whether to import
  private-session plays, podcasts, audiobooks and Spotify's video plays. Whether totals split
  YouTube Music listening from YouTube watching, which promotes `header`.
- **Whether to strip `ip_addr` and `conn_country`** from the export's records on import. The site
  never shows `raw`, but the store keeps it for years.
- **Local time.** Totals by local day need a time zone. One configured zone is simplest; a zone
  per event would follow travel, and `conn_country` in `raw` is enough to add it later.
- **An event with no item**, or a placeholder item per unidentifiable record (§1).
- **Theme, constellation and list**: one table or three (§5).
- **A work above items**, if the owner later wants one song totalled across services (§6). It
  would group items, and so would not contradict the owner's choice against merging them.
- **Spotify's account-data package** (past year, names only) is not an input. Names are not
  identifiers (Spotify §1), and the extended history covers the same year with URIs.
- **An owner column** stays with docs/08's "Smaller, for later". Nothing here depends on it.
