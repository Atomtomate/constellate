---
status: shaped
created: 2026-10-05
updated: 2026-10-05
---

# A calendar of concerts and releases

> Upcoming concerts of the owner's bands, within reach of where they live, and the release dates
> of the games and films they have bookmarked — as a calendar the phone subscribes to. Typed by
> hand first; later filled by scrapers from the atlas's favourites and the owner's bookmarks, so
> that nothing is typed.

## Progress

- [x] Captured
- [x] Problem stated — what is actually wrong today
- [ ] Ambiguity resolved — waits on the owner's answers under Open questions
- [x] Approach sketched
- [x] Checked against the domain model (`docs/02-domain-model.md`, in flight as PR #4)
- [x] Stub or sketch written — the occasion table, under Sketch
- [x] Sized — roughly, under Size
- [ ] Decision: adopt / park / drop — and where it sits, under Where it would sit in the roadmap

## The idea

The owner's words, 2026-10-05, relayed by the coordinating session:

> A calendar for the concerts I want to go to and releases (for games and movies, we later need
> to build a scraper that fills this with my favorite bands and bookmarked game releases). We
> should plan that out as well.

Three kinds of entry, one calendar:

- **A concert** by one of the owner's bands, with its date, venue and city and a ticket link —
  within reach of where the owner lives, which is a radius the owner sets.
- **A game release**: the day a game the owner has wishlisted or bookmarked comes out, with its
  store page.
- **A film release**: the day a bookmarked film opens in German cinemas, or arrives on a digital
  store, with the film's page. Whether TV premieres belong is a question below.

The calendar is read where calendars are read: the phone's calendar app subscribes to a feed the
site serves, and the entries carry reminders. A page on the site lists the same entries and is
where the owner marks one *going* or *not interested*, or types one that no feed knows.

The owner's word is "scraper". What the research below finds is that every usable source is an
API with a key, which [`00`](../00-vision-and-scope.md)'s rule against scraping a service's
private pages leaves alone. The one source with no API at all is Germany's dominant ticket
seller, and whether its public pages may be scraped is a question for the owner (below).

**The order the owner implies** — the calendar first, filled by hand; the scrapers later, once
the atlas knows the favourites and the bookmarks are in — holds up: the table and the feed are a
weekend, and they need nothing the log does not already have.

## Why it might be worth it

Three things the owner does today by hand, each with a failure mode the calendar removes:

- Finding out that a band is playing nearby — usually too late, or not at all, because the news
  travels through the band's channels and not through the owner's.
- Remembering when a wishlisted game or a bookmarked film comes out. A store wishlist mails on
  release day for that store alone; nothing mails for "the film I read about in March".
- Keeping those dates where the owner actually looks, which is the phone's calendar, not a store
  page or a ticketing site.

It is also the first feature that reads the atlas *forward*. The log says what the owner listened
to; the atlas says what they rate; the calendar says what, of those, is about to happen. It costs
no change to the log, and it gives M2's favourites something to do on the day they exist.

## How it fits the model

Checked against `docs/02-domain-model.md` and `ADR-0003`, both in flight as PR #4 when this was
written. The short answer: **it fits, and it costs one new noun that nothing in the log
references.**

**A concert is by a creator the log already knows.** Totals by artist read the `creator` row
with the ref `spotify:artist-name`, which comes from the owner's own export and needs no Spotify
app (`docs/02` §3; [`01 Spotify`](../01-data-sources-spotify.md) §6). So "my favourite bands" is
a question the store already answers two ways: the creators with the most listened time over a
period (M1), and the creators the owner marks as favourites (M2). The calendar adds nothing to
the creator; it adds a *ref*. Every concert feed names an artist by its own id, and matching a
name to one is ambiguous ("Genesis"), so the mapping the owner confirms once is stored as a
creator ref in a new namespace — `ticketmaster:attraction`, `musicbrainz:artist` — exactly as
`youtube:channel` is today. The MusicBrainz id earns a namespace of its own: three of the feeds
below accept or return it, so it is the hub that lets one confirmed mapping serve several feeds.

**A release is of something the owner has bookmarked, which the log does not know.** No event
ever plays a game or a film, so neither is an item kind the log has. M2 already plans items with
no events — a web page the owner captures is "an item with no events" (`docs/02` §6) — and a
bookmarked game or film is the same thing: an item the owner wants, before it exists. The
leaning is two item kinds, `game` and `film`, with refs `steam:app`, `igdb:game` and
`tmdb:movie`, created by the bookmark import. The alternative, a bare title on the calendar
entry, costs nothing today and loses the day the owner wants to rate the game they waited for.
A new item kind is the cheap change `docs/02` §8 names: the `item.kind` check constraint grows.

**A future-dated occasion is not a log event.** An event is a play that happened, observed by a
source, with a start and a duration, and its observations are immutable (`ADR-0003`). A concert
announcement is none of those: it lies in the future, nobody measured its duration, its date
moves, it gets cancelled, and two feeds announce the same concert with two dates. Storing it as
an event with a future `started_at` would put announcements into every total and make the log's
immutability rule false. So the new noun is an **occasion**: something announced to happen on a
date, whose subject is a creator (a concert) or an item (a release), or neither (typed by hand).
It carries the two nullable references and the "at most one is set" check that `docs/02` §5
gives every atlas row. No log table references it, so the atlas rule — M2 adds tables and alters
none of the log's — holds.

**What is the feed's and what is the owner's.** Every feed below limits how long its data may be
kept: six months (TMDB), twenty-four hours (Twitch, for IGDB), "reasonable periods"
(Ticketmaster), thirty days (JamBase). The log already draws this line for YouTube's thirty days
(`docs/02` §4): what a catalogue said is a cache with a fetch date, what the owner did is the
record. Here the feed's columns on an occasion — date, venue, status, URL — are refreshed on
every fetch and read as absent when stale, while the owner's mark on it (*going*, *not
interested*, a note) and a hand-typed occasion are the owner's own record and never expire. A
daily refresh satisfies every cache rule in the table at once, because every rule is a day or
longer. What the calendar remembers after a date has passed is a question below.

**The scrapers are source adapters.** Each feed is one adapter in `sources/`, HTTP in and draft
occasions out, never SQL ([`03`](../03-architecture.md)), reached through an interface
`services/` declares and run by the same `python -m constellate.poll` entry point once a day.
One service persists occasions, idempotent on the feed's own record id — the ingestion seam's
shape, not its tables, because an occasion has no observations to resolve: the latest fetch wins
and earlier values are not kept. The adapters need the host to be up once a day, which Q-E
already requires of the poller.

**The output is a file, not an app.** An iCalendar feed — one `VEVENT` per occasion, a `VALARM`
inside it for the reminder [S56, verified] — served at an unguessable URL whose token lives on
the owner's row, the mechanism `docs/02` §5 already gives recommendation lists. Google Calendar
subscribes to a URL from its web interface only, not from its phone apps [S57, verified]; the
subscription then reaches the phone through the account (inferred). iOS subscribes in the
Calendar app itself [S58, verified]. The output side is one endpoint and a text format; it
touches none of Q-F's apps, and an app later would read the same occasions through the contract.

## Where the data would come from

### How the claims are marked

Every load-bearing claim cites a source from the list at the end, as [S*n*], with one of three
marks, as the data-source documents do:

- **verified**: read on that page on 2026-10-05 — by the three research agents this pass ran,
  one per column of the table, or by the author, who re-read the pages the leaning turns on:
  Songkick's closure, Bandsintown's terms, Ticketmaster's quota and terms, TMDB's terms and
  release types, Steam's terms and store endpoint, RAWG's plans, the Twitch agreement's caching
  clause, JamBase's plans and terms.
- **reported**: a third-party page says so — a forum post, a community wiki, a mirror of a
  service's own machine-readable list.
- **inferred**: reasoning, stated as such.

What could not be settled is under *Not verified*, below the tables.

### Concert feeds

| Feed | Gives | Access today | Cost and limits | Terms that bite | Verdict |
|------|-------|--------------|-----------------|-----------------|---------|
| **Ticketmaster Discovery API v2** | Events by attraction id, keyword, country, city, geo-point and radius, date range; venue name, city, country, coordinates; sale dates; ticket URL [S8, verified] | Open signup; Discovery keys work instantly [S9, verified] | Free; 5,000 calls a day; 5 requests a second on the docs page, 2 on the FAQ [S9, S10, verified] | Event content kept only "for reasonable periods in order to provide the service"; Ticketmaster may limit apps whose calls are not driven by direct user actions; a privacy policy must disclose data use; no revenue from the API [S11, verified, 2023-06-27] | **Start here.** Germany is market 210 and `DE` a supported country code [S12, verified in the docs repository's data files]; the coverage is Ticketmaster's inventory, not Eventim's. |
| **Bandsintown Artist Events API** | Events by artist name, past and upcoming; venue with city, region, country, coordinates; lineup; offers [S1, verified] | A key is self-serve in the artist dashboard and tied to one artist; non-artists apply by email to a partnerships team; students refused [S2, S3, verified] | Free for artists; no numeric limit published; noisy keys throttled [S4, verified] | For use "solely by artists, or people working in connection with or on behalf of artists"; no commercial use; session caching only, after notifying them; Bandsintown branding and its ticket links as primary [S2, verified, 2019-02-25] | **Closed to a fan's app** without written approval (inferred from S2, S3). Technically the best fit: artist name in, events out. |
| **Songkick API** | Upcoming events per artist id or MusicBrainz id; venue, city, metro area, country; status [S5, verified] | **Closed**: "unable to process new applications for API keys"; hobbyist and student requests not approved; partners pay a licence fee [S5, S6, verified] | None available | Non-commercial; logo and link per resource; cache at most 24 hours; no mixing with other concert data [S7, verified, 2022-01-26] | **Closed.** The alternative to Bandsintown if it reopens. |
| **JamBase Data API v3** | Events by artist, geo-radius, country, date; venue address and coordinates; ticket offers; MusicBrainz and other external ids; a delta-sync parameter [S16, verified] | Self-serve; a $0 Developer plan [S17, verified] | 1,000 calls a month, 3,600 an hour; six months ahead and no past events; $0.05 a call over quota [S17, verified] | Non-commercial, hobby sites explicitly allowed; an attribution mark linking to JamBase; every event links to its ticket URL unmodified; storing or caching "beyond 30 days" needs written permission [S18, verified, v1.2.0 effective 2026-08-26] | **A fallback to test.** German coverage is stated nowhere, and the schema's state field exists for the US, Canada and Australia only (inferred). |
| **Setlist.fm API** | Setlists per artist (MusicBrainz id) with event date, venue, city, country [S13, verified] | Register, then apply for a key [S13, verified] | Free for non-commercial use [S13, verified]; 1,440 requests a day on a standard key [S15, reported] | Attribution with the per-response URL; no retained copies beyond short caching [S14, verified, 2019-10-14] | **Past concerts only** (inferred: the guidelines admit only concerts that happened). Not for this calendar; relevant only if "concerts I went to" ever becomes a log entry. |
| **MusicBrainz events** | Event entity: type, begin and end date, cancelled flag, linked artists and place; browse by artist [S19, verified] | No key; a User-Agent naming the app [S20, verified] | Free; one request a second [S20, verified] | None: event data is CC0 [S21, verified] | **A cross-check, not a listing.** Nothing read says how complete future events are in an editor-maintained catalogue (inferred). Its artist id is the hub id above. |
| **Eventim** | — | **No public API found**: an affiliate programme with links and banners for `eventim.de` [S22, verified]; Eventim US has an API feed that returns US events alone [S23, verified] | — | Affiliate rules, not read | **The gap.** Germany's largest ticket seller is reachable by link, not by feed (inferred from the searches and two unreachable partner pages). |
| **Spotify Web API** | No concert data: the artist endpoints are albums, top tracks and related artists [S24, verified] | — | — | — | **Nothing to get.** Spotify's concert listings are an in-app feature (inferred). |

### Release feeds — games

| Feed | Gives | Access today | Cost and limits | Terms that bite | Verdict |
|------|-------|--------------|-----------------|-----------------|---------|
| **Steam wishlist** (`IWishlistService/GetWishlist`) | The owner's wishlist as app ids with a priority and the date added; no names, no dates [S25, reported; a live call confirmed the shape] | No key and no login, for a wishlist whose profile shares "Game details" publicly [S25, reported; S28, verified] | Free; the Web API terms allow 100,000 calls a day [S26, verified, July 2010] | Steam Data for end users' personal use; a privacy policy naming where data is stored; an account that has spent under $5 gets no Web API [S26, S27, verified]. The older `wishlistdata` endpoint is gone since late 2024 [S29, reported] | **The bookmark source for games.** A private profile returns an empty object, indistinguishable from an empty wishlist (observed, undocumented). |
| **Steam store `appdetails`** | Per app, `release_date: {coming_soon, date}`, the date free text — "8 Oct, 2026", a quarter, a year, or empty [S30, reported; live calls confirmed the shape] | Open; no key (live call) | Free; about 200 requests per five minutes [S30, reported] | No published terms for the storefront endpoint, which Valve does not document (inferred from the docs search) | **The date for every wishlisted game**, parsed as a window when coarse. Developers choose day, month, quarter, year or "coming soon" and may move the date until two weeks before release [S31, verified]. |
| **IGDB** (`/v4/release_dates`) | Per game, platform and region: the date, a human string, the precision down to quarter, year or TBD, a status, `updated_at` [S32, verified] | Open signup: a Twitch developer application with client credentials [S32, verified] | Free; 4 requests a second, 8 in flight [S32, verified] | The docs say free for non-commercial use under the Twitch Developer Services Agreement, and their FAQ welcomes storing and caching; that agreement limits stored copies to a 24-hour cache unless Twitch authorises more, requires "a clear path to the source", and forbids monetising Twitch Data [S32, S33, verified; the agreement dated 2023] | **The best date semantics**, behind an unsettled terms question (whether S32's FAQ or S33 governs). A daily refresh satisfies the stricter reading. |
| **RAWG** | Games with `released` and a `tba` flag; filter by a release-date range [S34, verified] | Open signup; the key on every request [S34, verified] | Free up to 20,000 requests a month; Business $149 a month [S34, verified] | Non-commercial on the free plan (the terms beneath also admit hobby projects); "Required backlinks to RAWG"; no redistribution [S34, verified] | **The simpler fallback to IGDB.** One date and a flag: a quarter-only announcement cannot be told from an exact day (inferred). |

### Release feeds — films

| Feed | Gives | Access today | Cost and limits | Terms that bite | Verdict |
|------|-------|--------------|-----------------|-----------------|---------|
| **TMDB** | Per film, release dates by country (`iso_3166_1`) and type — 1 premiere, 2 limited theatrical, 3 theatrical, 4 digital, 5 physical, 6 TV; upcoming films for `region=DE` by release type, the docs' own worked example; per series, the next episode to air [S42, S44, S45, S46, verified] | An account, then a key from its settings page after accepting the terms; whether issue is instant is not stated [S41, verified] | Free for non-commercial use; a soft limit around 40 requests a second [S43, verified] | No commercial use; nothing from the API cached "for longer than 6 months"; a fixed attribution notice and the logo; terminable at any time [S47, verified, 2023-10-20] | **The film feed.** Germany's cinema dates are `DE` rows of type 3 [S42, verified; delivery through the API inferred from the website's own release pages]. |
| **OMDb** | One `Released` date per title, with no country [S48, verified] | A key by email [S48, verified] | 1,000 requests a day free; Patreon tiers from €1 [S48, verified] | Personal use only; CC BY-NC [S49, verified] | **Not a release-calendar source**: a single, US-centric date (inferred). |
| **Letterboxd** | Release data is first-party only; an account export is a zip of CSV files, the watchlist among them [S50, S52, verified; the file's name reported] | **Closed**: by request, and not "for private or personal projects" [S51, verified] | — | — | **A bookmark source by hand**: the exported watchlist, not the API. |
| **JustWatch** | Streaming offers and arrival dates — for partners [S54, verified] | **Partner contract only**; the terms forbid "data mining, robots, scraping" [S53, S54, verified] | Not published | Scraping forbidden | **Closed.** There is no open source for the day a film reaches a streaming service. |
| **German sources** | FFA lists its funded films with their cinema start as HTML, no feed [S55, verified] | — | — | — | **None with an API found**; TMDB's `DE` rows are the practical source (inferred). |

### Where "bookmarked" comes from

| Source | Gives | How it is read | Verdict |
|--------|-------|----------------|---------|
| The Steam wishlist | App ids with the date added | The endpoint above, daily | **Yes** — the canonical list for games. |
| Chrome's bookmarks | A JSON file named `Bookmarks` in the profile directory, folders and URL nodes with name, URL and the date added [S35, S36, verified] | A copy of the file, parsed; a store URL yields the app or film id | **Yes**, as M2's websites source: a bookmark is a `page` item, and a store page becomes a `game` or `film` item. |
| Firefox's bookmarks | `places.sqlite` in the profile; `moz_bookmarks` rows of type 1 point at `moz_places` rows with URL and title [S37, S38, verified] | A copy of the database, read with SQLite — the live file is locked | **Yes**, the same way. |
| A Letterboxd watchlist | A CSV in the account export [S52, verified; the name reported] | Uploaded by hand when the owner exports | **Yes, by hand.** |
| GOG and Epic wishlists | GOG: an undocumented endpoint the website uses, with the owner's own token [S39, reported]; Epic: no API and no export of a user's wishlist [S40, verified] | — | **No.** Nothing licenses the GOG route; Epic has none. |
| A list the owner keeps | Whatever the owner types | The atlas's favourites and notes (M2), or the calendar's own form | **Yes** — the fallback for everything, and the first version. |

### The leaning

- **Concerts: Ticketmaster Discovery**, by attraction id once the owner has confirmed each band's
  attraction, and by geo-point and radius for "within reach". It is the one open, instant, free
  feed that names Germany. Its terms want the data refreshed rather than kept, and its calls
  "driven by direct user actions": a daily job for a hundred bands is a few hundred calls against
  a quota of five thousand, and the phrase is a right Ticketmaster reserves, not a prohibition —
  but the owner should know it is there. Test **JamBase** for German coverage before counting on
  it as a second source. **MusicBrainz** supplies the hub id and a cross-check for free.
  **Bandsintown** and **Songkick** stay closed until one of them says otherwise. **Eventim** is
  the coverage gap no feed closes.
- **Games: Steam's two endpoints** cover the wishlist and the date with no key at all. **IGDB**
  adds date precision and status once the terms question is settled, and a daily refresh
  satisfies the strict reading of them anyway. **RAWG** is the fallback if IGDB's terms are read
  as closed.
- **Films: TMDB**, `DE` rows of type 3 for cinema and type 4 for digital, with the owner's
  bookmarks or Letterboxd export as the list. Streaming arrival dates have no open source.
- **Output: an iCalendar feed** with alarms, subscribed to from Google Calendar's web interface
  or from iOS directly.

### Not verified

- Ticketmaster: 5 or 2 requests a second (the docs and the FAQ disagree); whether past events are
  retrievable; what share of German concerts it lists next to Eventim.
- JamBase: German coverage; which plan includes ticket links, addresses and coordinates.
- Setlist.fm: rate limits rest on a forum post; "past only" is not stated in so many words.
- Eventim: whether its affiliate programme admits a private non-commercial site; whether a product
  feed exists for `eventim.de`; four partner pages were unreachable.
- Steam: whether the Web API terms govern the storefront endpoint; how `appdetails` spells a
  month-, quarter- or year-level date (only exact days were observed live); what a private
  wishlist returns; one account's wishlist count and its item list disagreed by two.
- IGDB: which of its FAQ and the Twitch agreement governs storage; the release-status names,
  which sit behind authentication.
- TMDB: whether a key is issued instantly; that `DE` entries arrive through the API as the website
  shows them; the default filters of `/movie/upcoming`.
- Letterboxd: the watchlist file's name and columns, seen on third-party pages only.
- Calendars: Google's refresh interval for a subscribed calendar, which its help page does not
  state; whether Google and iOS honour `VALARM` in a subscribed feed.
- Where the owner lives, and how far they will travel: not in the record.

## Open questions

Recorded, not resolved. The first three decide the shape; the rest decide details.

1. **Where is "within reach"?** The record holds no location. A home point and a radius in
   kilometres is the simplest answer; a list of cities another; "anywhere, but mark the far ones"
   a third.
2. **Which bands?** The creators with the most listened time over the last year (automatic, M1);
   the creators the owner favourites (M2); a hand list; or the first until the second exists.
3. **Which stores and which films?** Steam alone, or GOG and consoles too, which no feed covers;
   cinema dates, digital dates, or both; TV season premieres through TMDB's series data, or not.
4. **Is scraping Eventim's public pages acceptable?** [`00`](../00-vision-and-scope.md) excludes
   scraping a service's *private* pages; these would be public listings, under terms this pass did
   not read. Without it, German concerts are Ticketmaster's inventory alone.
5. **What does the calendar remember?** After a date passes: drop the feed's data (the terms'
   cheap reading), keep the owner's marks alone, or keep the occasion as "went" — which edges
   toward a log entry and is deliberately not proposed here.
6. **Are the feeds' terms acceptable?** Ticketmaster's privacy-policy clause and its "direct user
   actions" phrase; TMDB's attribution notice on the page that shows its data; IGDB's unsettled
   storage rule.
7. **How does the owner confirm a band's feed identity?** A one-time review of candidates per
   creator, or automatic on an exact name match with a review of the rest.
8. **Reminders**: how long before a concert's on-sale date, before the concert, before a release.
9. **An occasion typed by hand that a feed later also announces**: merge on title and date, or
   keep both.

## Depends on

- **M1**: the creators and their listened time; the API and sign-in, since the feed's token hangs
  off the owner; the poller entry point the adapters run under; and the host Q-E chooses being
  up once a day.
- **M2**: favourites as the explicit band list; websites as a source, which is where a bookmark
  file becomes items.
- **The owner's location**, which nothing in the record states.
- **Accounts the owner creates**: Ticketmaster, TMDB, a Twitch developer application for IGDB,
  RAWG if used; a Steam profile whose game details are public, or an exported wishlist.
- **`docs/02-domain-model.md` merging** (PR #4): the item kinds and ref namespaces above extend
  what it defines.

## Sketch

A sketch to argue with, in the shape `docs/02` §7 uses; Postgres, names provisional.

```sql
-- A SKETCH. One table the log never references, in the atlas's two-reference pattern.
create table occasion (
  id            bigint generated always as identity primary key,
  kind          text not null check (kind in ('concert', 'release')),
  creator_id    bigint references creator,        -- a concert's band
  item_id       bigint references item,           -- a release's game or film
  title         text not null,                    -- as the feed or the owner names it
  starts_on     date not null,                    -- the announced day, or the window's start
  precision     text not null check (precision in ('day', 'month', 'quarter', 'year', 'tba')),
  starts_at     timestamptz,                      -- a concert's start, when the feed gives one
  venue         text, city text, country text,    -- concerts; null for a release
  url           text,                             -- tickets, or the store page
  status        text not null check (status in ('announced', 'postponed', 'cancelled')),
  source_id     smallint references source,       -- null: typed by hand
  record_key    text unique,                      -- the feed's own id; the refresh is idempotent
  fetched_at    timestamptz,                      -- feed columns read as absent when stale
  raw           jsonb,
  check (num_nonnulls(creator_id, item_id) <= 1)
);

create table occasion_mark (                      -- the owner's own record; never expires
  occasion_id   bigint primary key references occasion,
  mark          text not null check (mark in ('going', 'interested', 'not_interested')),
  note          text,
  marked_at     timestamptz not null
);
```

What a feed adapter looks like, in the layering [`03`](../03-architecture.md) fixes:

```python
# A SKETCH. sources/ knows HTTP and never SQL; services/ declares the interface it satisfies.
class ConcertFeed(Protocol):
    """Upcoming concerts for the creators the owner has mapped to this feed's ids."""

    def upcoming(self, refs: Sequence[CreatorRef], within: GeoRadius) -> list[DraftOccasion]:
        """One draft per announced concert; the same record twice carries the same key."""
        raise NotImplementedError
```

## Size

Rough, and the first number is the one that matters:

- **The calendar typed by hand, plus the iCalendar feed**: a weekend. One table, one migration,
  two endpoints and a form, and the feed writer. It needs nothing but M1's API.
- **Ticketmaster**: a weekend — the adapter is an evening; a review screen for confirming a
  hundred bands' attractions is the rest.
- **TMDB, the Steam pair, IGDB**: an evening each; IGDB's Twitch sign-in a little more.
- **The bookmark import**: a weekend, and it is M2's websites source, so most of it is owed
  anyway.
- **Unknown**: how well band names match attractions, and how much of a German concert calendar
  Ticketmaster alone shows. Both are found out in the first week of running it.

A month of evenings for all of it; a weekend for the first useful version.

## Where it would sit in the roadmap

A proposal and a question for the owner; [`07`](../07-roadmap.md) is unchanged by this file.

- **A. A bullet in M2, the collection.** The occasion is atlas material, the favourites and the
  bookmarks it reads are M2's, and the hand-typed version needs nothing M2 does not already build.
  Against it: M2's "done when" is about favourites, and a milestone with two centres is what the
  roadmap's fourth rule warns of.
- **B. Its own milestone between M2 and M3**: "the calendar", with constellations and
  recommendations moving to M4 and the apps to M5. It brings a new noun, three feeds with their
  own terms and the first forward-looking feature, and it is small enough to finish. Against it:
  one more milestone before the two questions the atlas exists for.
- **C. In M4, the apps.** The output is phone-facing. Against it: the output is a file any
  calendar reads, and no app is needed.

**The leaning is B**, with the hand-typed table and the feed allowed into M2 if the owner wants
concerts on the phone before the atlas exists — they need only M1's creators. Whichever is
chosen, nothing here moves before M1 ships; the roadmap's fourth rule stands.

## Sources

All read on 2026-10-05.

- **S1**: Bandsintown PublicAPI 3.0.0 specification: artist and event endpoints and fields.
  https://api.swaggerhub.com/apis/Bandsintown/PublicAPI/3.0.0
- **S2**: Bandsintown Data Applications Terms (last updated 2019-02-25): artists only, no
  commercial use, session caching, branding.
  https://corp.bandsintown.com/data-applications-terms
- **S3**: Non-artists apply by email; students not accepted.
  http://help.artists.bandsintown.com/en/articles/3372745-can-i-have-access-to-the-api-and-an-api-key-if-i-m-not-an-artist
- **S4**: Optimising API usage: throttling of noisy keys, caching of misses.
  https://help.artists.bandsintown.com/en/articles/13142424-optimizing-api-usage
- **S5**: Songkick developer page: hobbyist requests not approved; licence fee.
  https://www.songkick.com/developer
- **S6**: Songkick key requests: "unable to process new applications for API keys".
  https://www.songkick.com/api_key_requests/new
- **S7**: Songkick API Terms of Use (2022-01-26).
  https://www.songkick.com/developer/api-terms-of-use
- **S8**: Ticketmaster Discovery API v2 reference: parameters and event fields.
  https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/
- **S9**: Ticketmaster getting started: instant keys; 5,000 a day; 5 a second.
  https://developer.ticketmaster.com/products-and-docs/apis/getting-started/
- **S10**: Ticketmaster FAQ: 5,000 a day; 2 a second.
  https://developer.ticketmaster.com/support/faq/
- **S11**: Ticketmaster API Terms of Use (2023-06-27): caching, user-driven calls, privacy policy.
  https://developer.ticketmaster.com/support/terms-of-use/
- **S12**: Ticketmaster's docs repository: `_data/orgs/discovery-api/v2/countryCode.json` (DE) and
  the markets include (210 Germany).
  https://github.com/ticketmaster-api/ticketmaster-api.github.io
- **S13**: Setlist.fm API docs: non-commercial, key via settings, headers, artist setlists.
  https://api.setlist.fm/docs/1.0/index.html
- **S14**: Setlist.fm terms (2019-10-14): attribution, no retained copies.
  https://www.setlist.fm/help/terms
- **S15**: Setlist.fm forum: 1,440 requests a day on a standard key (admin post, 2026-05-15).
  https://www.setlist.fm/forum/setlistfm/setlistfm-api/rate-limit-exceeded-bd67dc2
- **S16**: JamBase Data API getting started and reference (v3.1.0).
  https://data.jambase.com/api/docs/getting-started
- **S17**: JamBase pricing: Developer $0, 1,000 a month, 3,600 an hour, six months ahead.
  https://data.jambase.com/pricing
- **S18**: JamBase Terms of Service v1.2.0 (effective 2026-08-26): hobby use, 30-day cap,
  attribution.
  https://data.jambase.com/legal/terms-of-service
- **S19**: MusicBrainz Event entity.
  https://musicbrainz.org/doc/Event
- **S20**: MusicBrainz API rate limiting: one call a second; User-Agent.
  https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting
- **S21**: MusicBrainz data licence: core data CC0.
  https://musicbrainz.org/doc/About/Data_License
- **S22**: Eventim's AWIN merchant profile: links and banners.
  https://ui.awin.com/merchant-profile/11388
- **S23**: Eventim US Affiliates Network: an API feed of Eventim US events only.
  https://clients.eventim.us/hc/en-us/articles/18890091910939-Affiliates-Network
- **S24**: Spotify Web API reference index: no concert endpoints.
  https://developer.spotify.com/documentation/web-api
- **S25**: `IWishlistService` on an unofficial mirror of Steam's own interface list.
  https://steamapi.xpaw.me/IWishlistService
- **S26**: Steam Web API Terms of Use (July 2010): 100,000 calls a day; personal use; a privacy
  policy.
  https://steamcommunity.com/dev/apiterms
- **S27**: Steam limited accounts: no Web API under $5 spent.
  https://help.steampowered.com/en/faqs/view/71D3-35C2-AD96-AA3A
- **S28**: Steam profile privacy: wishlists under "Game details".
  https://steamcommunity.com/games/593110/announcements/detail/1667896941884942467
- **S29**: The `wishlistdata` endpoint replaced by `GetWishlist` in late 2024 (forum report).
  https://steamcommunity.com/groups/bartervg/discussions/0/4629233379372457987/
- **S30**: Community documentation of the storefront `appdetails` endpoint and its rate limit.
  https://github.com/Revadike/InternalSteamWebAPI/wiki/Get-App-Details
- **S31**: Steamworks: release-date display options and when a date may move.
  https://partner.steamgames.com/doc/store/release_dates
- **S32**: IGDB API docs: Twitch credentials, 4 a second, `release_dates`, FAQ on caching.
  https://api-docs.igdb.com/
- **S33**: Twitch Developer Services Agreement (last modified 2023): 24-hour cache, attribution.
  https://legal.twitch.com/legal/developer-agreement/
- **S34**: RAWG API docs: plans, limits, backlinks, no redistribution.
  https://rawg.io/apidocs
- **S35**: Chromium bookmark codec: the `Bookmarks` JSON keys.
  https://chromium.googlesource.com/chromium/src/+/HEAD/components/bookmarks/browser/bookmark_codec.cc
- **S36**: Chromium user data directory per platform.
  https://chromium.googlesource.com/chromium/src/+/HEAD/docs/user_data_dir.md
- **S37**: Firefox profile folder and `places.sqlite`.
  https://support.mozilla.org/en-US/kb/profiles-where-firefox-stores-user-data
- **S38**: Firefox places schema: `moz_bookmarks`, `moz_places`.
  https://raw.githubusercontent.com/mozilla-firefox/firefox/main/toolkit/components/places/nsPlacesTables.h
- **S39**: Unofficial GOG API documentation: the wishlist endpoint.
  https://gogapidocs.readthedocs.io/en/latest/
- **S40**: Epic Games Store wishlist notifications: developers see aggregates only.
  https://dev.epicgames.com/docs/epic-games-store/sales-and-marketing/marketing/automated-wishlist-notifications
- **S41**: TMDB getting started: the key from account settings.
  https://developer.themoviedb.org/docs/getting-started
- **S42**: TMDB region support: the `region=DE` discover example.
  https://developer.themoviedb.org/docs/region-support
- **S43**: TMDB rate limiting: about 40 requests a second.
  https://developer.themoviedb.org/docs/rate-limiting
- **S44**: TMDB movie release dates: `iso_3166_1`, types 1–6.
  https://developer.themoviedb.org/reference/movie-release-dates
- **S45**: TMDB discover movie: `region`, `with_release_type`, date filters.
  https://developer.themoviedb.org/reference/discover-movie
- **S46**: TMDB TV series details: `next_episode_to_air`.
  https://developer.themoviedb.org/reference/tv-series-details
- **S47**: TMDB API Terms of Use (2023-10-20): non-commercial, 6-month cache, attribution.
  https://www.themoviedb.org/api-terms-of-use
- **S48**: OMDb API: fields, free tier, Patreon.
  https://www.omdbapi.com/
- **S49**: OMDb legal: personal use, CC BY-NC.
  https://www.omdbapi.com/legal.htm
- **S50**: Letterboxd API docs: releases first-party only.
  https://api-docs.letterboxd.com/
- **S51**: Letterboxd API access: not for private or personal projects.
  https://letterboxd.com/api-beta/
- **S52**: Letterboxd FAQ: the account export.
  https://letterboxd.com/about/faq/
- **S53**: JustWatch Terms of Use: no scraping.
  https://support.justwatch.com/article/just-watchs-terms-of-use
- **S54**: JustWatch partner API: content and upcoming dates, by contract.
  https://apis.justwatch.com/docs/
- **S55**: FFA "Filmstarts": funded films' cinema starts as HTML.
  https://www.ffa.de/filmstarts.html
- **S56**: RFC 5545, iCalendar (September 2009): VEVENT §3.6.1, VALARM §3.6.6.
  https://datatracker.ietf.org/doc/html/rfc5545
- **S57**: Google Calendar: subscribe by URL on a computer; not in the phone apps.
  https://support.google.com/calendar/answer/37100
- **S58**: Apple: subscribe to a calendar on iPhone.
  https://support.apple.com/en-us/102301
