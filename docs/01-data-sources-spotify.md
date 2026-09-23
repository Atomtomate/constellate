# 01 — Data sources: Spotify

> **Research, not a decision.** This document answers Q-D for Spotify in
> [08](08-open-questions.md) and gives Q-C the fields it needs. It decides nothing: the
> recommendation at the end is for the owner to accept or correct. Every load-bearing claim
> names its source by a number (S1, S2, …) from the list at the end, which gives the URL, the
> date it was read, and whether the claim was **verified** on the page, **reported** by a third
> party, or **inferred** here.

*Last updated: 2026-09-23*

**Request the extended streaming history today.** Spotify's privacy page quotes up to 30 days
to prepare it (S3, reported); people have received it in four hours and in more than a month
(S4, S6). Nothing else in this document can backfill years of listening, and it can run while
M0 is still being planned. The steps are in [What the owner does](#what-the-owner-does).

## The answer in brief

Spotify holds two things worth having, and neither is enough by itself.

- **The extended streaming history export** covers the account's whole lifetime. Each play
  carries the time it *ended*, the milliseconds actually played, the track or episode URI, and
  the reason it started and stopped (S1, verified). It is the ground truth for "how long", and
  the only backfill. It arrives as JSON files, after a delay the owner cannot control.
- **The Web API** is the only way to capture plays as they happen. It gives two views, and
  neither is complete. `recently-played` lists the last 50 plays, but without listened time.
  Developers report that it leaves out partial plays (S7, verified; S24, reported). Polling
  `currently-playing` gives listened time to within the polling interval. In the development
  mode an individual is limited to, it draws on a quota Spotify does not publish (S15, S22,
  verified).

The combination that loses least: import the export once, poll both endpoints from the day the
tracker runs, and re-request the export every few months so its measured `ms_played` replaces
the poller's estimates. Last.fm and ListenBrainz run on the same Web API endpoints (S29, S27)
and add no information, only someone else's uptime.

Three findings change the plan as `07-roadmap.md` and Q-D now state it:

1. **The API alone cannot say "how long".** `recently-played` has no listened-time field, and
   reportedly shows only plays that reached, or nearly reached, the end of the track (S24).
   Actual listened time comes from polling playback state or from the export.
2. **An individual's API access is development mode for good, and it is metered.** Since
   February 2026 development mode requires the app owner to hold Premium (S18, S20). Since May
   2025 only organisations with 250,000 monthly users may apply for more (S15). The quota is
   per developer account, and its size and reset period are unpublished (S22). One developer
   hit it by polling playback every 3 seconds (S23). Another was blocked for 23 hours after about
   600 metadata requests in a day (S28). The polling interval is a budget to measure, not a
   free choice.
3. **The owner must sign in again every six months, and enriching the export costs one
   request per track.** Since 2026-07-20 refresh tokens expire six months after
   authorisation, and refreshing does not extend them (S13, verified). Separately, the export
   has no track length, no per-track artist list and no ISRC (S5, S34). Filling them in now
   takes one `GET /tracks/{id}` per distinct track, because development mode lost the batch
   endpoints in February 2026 (S19, S20). Twenty thousand distinct tracks is about five weeks
   of quota at the rate S28 observed.

## 1. Backfill: what Spotify already holds

### The three download packages

The privacy page's "Download your data" tool offers three packages, requested separately or
together, each delivered as JSON (S1, verified):

| Package | Listening history it holds | Identifiers |
|---------|----------------------------|-------------|
| Account data | Past year: end time, creator, title, `msPlayed` | Names only |
| Extended streaming history | Lifetime, one object per play | Track, episode, audiobook URIs |
| Technical log information | None: commands, errors, log strings | — |

The extended history is the backfill; the technical log is not needed. The account-data
history names a play only by artist and title (S1, verified). Its field names
in third-party parsers are `endTime`, `artistName`, `trackName` and `msPlayed`; Spotify's page
names only `msPlayed`. Names are not identifiers, so this package can be neither matched
reliably to the API nor used as the backfill. It is worth requesting only because it arrives
sooner: "usually within a few days" (S3, reported).

### What the extended history contains

The files are named `Streaming_History_Audio_<years>_<n>.json`, with a separate
`Streaming_History_Video_…` file for video plays (S3, reported; the video file name is seen in
several third-party parsers). Each file is a JSON array of about 12 MB at most (S4, reported),
and a PDF "Read Me First" describes the fields (S1, verified). One object per play, with these
fields, from a 2026 sample (S5, reported) that matches Spotify's own list (S1, verified):

| Field | Meaning (S1 unless noted) |
|-------|---------------------------|
| `ts` | When the stream **ended**, UTC, to the second |
| `ms_played` | Milliseconds actually played |
| `platform` | Device or OS, e.g. "Android OS", "Google Chromecast" |
| `conn_country`, `ip_addr` | Country and IP address of the stream |
| `master_metadata_track_name` | Track title |
| `master_metadata_album_artist_name` | The **album** artist, not the track's artists (S34) |
| `master_metadata_album_album_name` | Album title |
| `spotify_track_uri` | `spotify:track:…` — null for episodes and audiobooks |
| `episode_name`, `episode_show_name`, `spotify_episode_uri` | Podcast episode, show, URI |
| `audiobook_title`, `audiobook_uri` | Audiobook and its URI (S5; not on S1) |
| `audiobook_chapter_title`, `audiobook_chapter_uri` | Chapter and its URI (S5) |
| `reason_start`, `reason_end` | Why it started and stopped: `trackdone`, `fwdbtn`, … |
| `shuffle` | Shuffle on or off |
| `skipped` | Whether the user skipped to the next track — **unreliable**, below |
| `offline`, `offline_timestamp` | Played offline, and when offline mode was used |
| `incognito_mode` | Played in a private session |

Spotify's list also names the username and the user agent (S1). Neither appears in the 2024
and 2026 samples read for this document (S4, S5), so they were probably dropped (inferred).

**Podcasts and audiobooks are in it:** the episode and audiobook fields exist for them, and the
page describes the history as "songs, videos, and podcasts" (S1, verified). **Private-session
plays are in it too**, marked by `incognito_mode` (S1, verified). Those are the plays the app's own
Recently Played list omits (S37, reported). Whether the tracker keeps them is the owner's call.
**Offline plays are in it**, marked `offline` (S1, verified).

**What `ms_played` means:** "For how many milliseconds the track was played" (S1, verified). It
is time listened, not track length. A play's start time is therefore `ts − ms_played`
(inferred). The export does not state it.

**Quality problems others have measured**, over one account's decade of data (S4, reported;
S28 repeats them from a second account):

- `skipped` is `false` for every play between 2015-04-13 and 2022-10-16, so it is unreliable
  for those years. `reason_end` and `ms_played` are the usable signals for a skip; S28 uses
  `ms_played < 30000`.
- About 2.6% of streams overlap the next one, so `ts − ms_played` is an estimate.
- `offline_timestamp` switched from seconds to milliseconds at some point, and disagrees with
  `offline` in over 23% of streams.
- The same recording appears under several track URIs (remasters, reissues, regional
  editions).

### Requesting it, and how long it takes

The request is made signed in at `https://www.spotify.com/account/privacy/`, the Account
Privacy page (S2, verified). Under "Download your data", tick "Extended streaming history" and
request it. Spotify then sends a **confirmation email that must be clicked** before preparation
starts (S3, reported; S6, a user report answered by a Spotify moderator on 2024-04-17). A
second email brings the download link, which works only while signed in to the same account
(S3, reported).

The privacy page quotes 30 days (S3, S4, reported). This could not be verified here because the
page requires signing in. Reported arrivals range from four hours (S4, December 2024) to more
than 30 days (S6, April 2024). In that thread the moderator's advice for a request that never
arrived was to check the spam folder and then resubmit (S6, verified). Nothing found says how
long the download link stays valid, or whether repeated requests are rate-limited.

## 2. Ongoing capture: the Web API

### Access in 2026: development mode, and only that

A Spotify app is registered in the Developer Dashboard and starts in **development mode**
(S15, verified). As of this reading:

- **The app owner must hold Premium**, and the app stops working if it lapses. This applies to
  new apps since 2026-02-11 and to existing ones since 2026-03-09 (S18, S20, verified).
- **Five authorised users per app**, each allowlisted by email, since the same dates (S15, S18,
  verified).
- **25 Client IDs per developer account**, up from one, since July 2026 (S22, verified).
- **The quota is per developer account**, shared by all its apps, since July 2026. Its buckets
  and limits are unpublished (S15, S22, verified).
- **Extended quota mode** has accepted only organisations since 2025-05-15, and requires
  250,000 monthly active users. Review takes up to six weeks (S15, verified).

Extended quota mode is out of reach for a personal tracker, so the tracker runs in development
mode indefinitely (inferred). The owner's account is both the app owner and the one user. **If
the owner does not have Premium, the API path is closed**, and capture falls back to periodic
exports alone.

**Endpoint removals that touch this project.** The November 2024 removals (Recommendations,
Audio Features, Audio Analysis, Related Artists and others) touch nothing the tracker needs
(S17, verified). The February 2026 development-mode changes removed the batch fetches
(`GET /tracks?ids=`, `/albums`, `/artists`, `/episodes` and others), `GET /users/{id}`, the
browse endpoints and artist top tracks. They also dropped `popularity`, `available_markets` and
`linked_from` from track objects (S19, S20, verified). `external_ids`, which carries a track's
ISRC, was removed and then restored in March 2026 (S21, verified). **Every Player endpoint the
tracker needs is on the list of endpoints still available**: `recently-played`,
`currently-playing` and playback state. So are single-item `GET /tracks/{id}`,
`GET /episodes/{id}` and `GET /me` (S19, verified).

### Authorisation

- **Flow.** Authorization Code with PKCE is "the recommended authorization flow" when a client
  secret cannot be kept safe (S11, verified). A server-side poller that holds a secret can
  equally use the plain Authorization Code flow. Either way the owner signs in once in a
  browser.
- **Scopes.** `user-read-recently-played` for `recently-played` (S7, S10);
  `user-read-currently-playing` for `currently-playing`, or `user-read-playback-state` for
  playback state (S8, S9, S10; all verified). Nothing needs write access.
- **Redirect URI.** HTTPS, or a loopback IP literal: `http://127.0.0.1:PORT/…`. **`localhost`
  is not allowed** (S14, verified).
- **Token lifetimes.** Access tokens last one hour (S12, verified). **Refresh tokens last six
  months from the owner's authorisation, and refreshing does not extend that**. When one expires
  the token endpoint answers `400` with `invalid_grant`, and the only remedy is to sign in again.
  This applies to new apps since 2026-06-18 and to existing ones since 2026-07-20 (S12, S13,
  verified). Tokens carry no issue date, so the tracker must record when the owner signed in
  and warn ahead of the deadline (S13, verified).

### `GET /me/player/recently-played`

What the reference says (S7, verified): `limit` 1 to 50, default 20. `after` or `before` is a
Unix-millisecond cursor, and the two are mutually exclusive. Each item carries the full track
object, `played_at` (ISO 8601) and the `context` it was played from (playlist, album, …).
"Currently doesn't support podcast episodes."

What the reference does not say, as developers report it:

- **Fifty plays is the whole window, not a page size.** A `before` cursor past the most recent
  50 returns nothing (S25, reported 2021; S24, 2023). Last.fm says the same: "the Spotify API
  only allows us to access the last 50 tracks" (S29, verified).
- **Partial plays are missing.** Reports from 2020 to 2025, including one from stats.fm on
  behalf of its users, say that only plays reaching or nearly reaching the end of the track
  appear, however long the play before the skip (S24, reported). The 30-second threshold some
  describe does not hold in their tests.
- **No listened time.** The item carries the track's `duration_ms`, which is its length, and
  nothing about how long it was played (S7, verified by absence).
- **`played_at` is ambiguous.** It is undocumented whether it marks the start or the end of the
  play, and one report shows both on different days, both from offline plays (S26, reported in
  Spotify's issue tracker, archived in 2020 with no answer).
- **It can lag.** ListenBrainz's maintainers note that it "does not show updated listens for
  hours" at times while `currently-playing` does (S27, verified in their docs).
- **Offline plays appear after the device syncs**, within the same 50-play window (inferred
  from S29's "offline scrobbling is limited to the last 50 tracks played" and from S26).
- **Private-session plays are not added** to the app's Recently Played list (S37, reported);
  that the API behaves the same is inferred.

### `GET /me/player/currently-playing` and `GET /me/player`

Both return the same object (S8, S9, verified). It holds `item` (the track, or the episode if
`additional_types=episode` is passed) and `progress_ms`, the position in the item. It also holds
`is_playing`, `currently_playing_type`, `context`, and `timestamp`, the "Unix Millisecond
Timestamp when playback state was last changed (play, pause, skip, scrub, new song, etc.)".
Playback state adds the active `device`, whose fields include `is_private_session`. When nothing
is playing, playback state answers `204` (S9, verified).

**Podcasts are visible here**, with `additional_types=episode`, although `recently-played`
never lists them (S8, verified). **Offline plays are not visible**: they happen where the API
cannot see them (inferred).

Measuring listened time from it (inferred, to be tested in M1): sample every Δ seconds and keep
one open play per item. While `is_playing` is true, the play's listened time grows by the
elapsed time between samples. A change of item closes the open play. Its start is known to
within Δ, or exactly from `timestamp` if that field behaves as documented. Its listened time
is off by at most Δ at the end. A play shorter than Δ can fall between two samples and be missed.
If it ran to its end, `recently-played` still lists it, with only its length as duration.

### Rate limits and quota

These are two different limits (S15, S16, S22, verified):

- **The rate limit** is counted over a rolling 30-second window, is higher in extended quota
  mode, and answers `429` with `Retry-After` in seconds. Its value is not published.
- **The development-mode quota** groups endpoints into buckets that share a limit. "The
  specific groupings and limits are subject to change", and they are not published. Exceeding
  it answers `429` with `"reason": "QUOTA_EXCEEDED"`. Since July 2026 it is counted per
  developer account, so a second app does not add budget.

Data points, none from Spotify:

- A family event app polling playback state every **3 seconds** hit "the new limits". Its
  developer fell back to 30-second polling when idle (S23, 2026-08-15, reported).
- A tool resolving export tracks one `GET /tracks/{id}` at a time was blocked with
  `Retry-After: 82661` (23 hours) after about 500 requests. The next day it was blocked again at
  599, with requests paced half a second apart (S28, 2026-08-04, reported). Whether Player
  endpoints share that bucket is unknown.
- A community post asking Spotify for the quota's size and reset period has no answer (S23).

### The polling interval, derived

**`recently-played` as the backstop.** It holds the last 50 completed plays, so polling must
come around before 50 plays go by. For 90-second tracks, a short case, that is 75 minutes
(inferred). Polling **every 30 minutes** with `after` set to the newest `played_at` already
stored keeps a margin of 2.5, costs 48 requests a day, and also absorbs the reported lag.
Overlap is harmless when stored plays are de-duplicated on track URI and `played_at`.

**Playback state for listened time.** The cost is (hours playing × 3,600 / Δ_playing) plus
(hours idle × 3,600 / Δ_idle):

| Δ while playing | Δ while idle | Requests a day, 4 h listening | Error per play |
|-----------------|--------------|-------------------------------|----------------|
| 10 s | 60 s | 1,440 + 1,200 = 2,640 | ≤ 10 s |
| 30 s | 180 s | 480 + 400 = 880 | ≤ 30 s |
| 60 s | 300 s | 240 + 240 = 480 | ≤ 60 s |

Adding `recently-played`'s 48, the middle row is under a thousand requests a day. Whether that
fits the quota is the one number this research could not find. S23's 3-second poller (about
1,200 requests an hour while playing) failed, and S28's ~600 a day was on a different
endpoint. **The recommendation is to start at 30 s playing and 3 min idle, log every `429` and
its `reason`, and tighten only once a few weeks show headroom** (inferred). Under that design,
running out of quota loses precision, not plays: `recently-played` still lists completed plays,
and the next export restores every `ms_played`.

## 3. Alternatives for ongoing capture

Both services named in the brief are built on the same two endpoints, so they inherit every
limit above rather than escaping it.

**Last.fm's Spotify connection** is linked once in Last.fm's settings, and scrobbles from
every device, Spotify Connect speakers included. Last.fm states that "this new feature uses the
Spotify api" (S29, verified), and lists the consequences:

- Offline plays are limited to the last 50, because that is all the API returns.
- A track is scrobbled only when the next one starts.
- A play is occasionally scrobbled twice (all S29, verified).

A scrobble's timestamp is "the time the track started playing". Its only duration is "the
length of the track", and even that is optional (S30, verified). Reading the log back with
`user.getRecentTracks` takes an API key and returns 200 scrobbles a page, filterable by
`from` and `to`, with no duration (S31, verified). It is free to connect; no pricing page was
checked. Whether the profile is public by default was not verified.

**ListenBrainz's Spotify connection** stores listens from `recently-played` and shows "playing
now" from `currently-playing` (S27, verified). So it inherits the 50-play window, the
missing partial plays and the lag. A listen has `listened_at` in Unix seconds and an optional
`duration_ms`, "the duration of the track" (S35, verified). Since 2025-08-30 it also imports the
extended-history zip (S34). It is **public by design**: "User listen data and text is made
public under the Creative Commons Zero (CC0) license". A private listen store is listed among
its "anti-goals" (S33, verified).

**What they are good for:** uptime. Last.fm's connection polls Spotify around the clock on
Last.fm's servers, under Spotify's quota for Last.fm, not the owner's. It could therefore fill a
window when the owner's poller was down, at start-time resolution and with no listened time
(inferred). **What they are not:** a source of anything the tracker cannot read itself, or of
listened time. ListenBrainz's public-by-design model is at odds with a private log (S33;
`00-vision-and-scope.md`'s "infrastructure the owner controls").

**Prior art.** `your_spotify` (Yooooomi/your_spotify, active in July 2026) is a self-hosted
tracker. It polls the Web API, "will only retrieve data for the past 24 hours once registered",
and imports both the account-data and the extended-history packages. It detects duplicates but
warns that "some may still be inserted" (S36, verified). It is the same design recommended
here, minus playback-state polling. It is worth reading before M1 designs the import, not
adopting (inferred).

## 4. What "how long" means, and matching the paths

| Path | "How long" | Start time | Identifier |
|------|------------|------------|------------|
| Extended history | `ms_played`, measured | `ts − ms_played`; `ts` is the end | URI |
| Account data | `msPlayed`, measured | `endTime − msPlayed` | Names only |
| Playback-state poller | Summed while playing, ± Δ | ± Δ, or `timestamp` | URI |
| `recently-played` | Track length, completed plays only | `played_at`, start or end | URI |
| Last.fm, ListenBrainz | None, or track length | Scrobble time, the start | Names |

Every start time here except the poller's is derived, not given (inferred).

So "how long" has one meaning for the tracker, milliseconds listened, and each event should
record where its number came from. A duration taken from track length is an estimate that a
later export corrects, not a fact (inferred; how an event records its provenance is Q-C's to
decide).

**Matching an export play to an API play** (inferred, to be tested on the owner's data):

- **Same URI, near in time.** Take the export's `spotify_track_uri` and `ts`. Match the poller's
  play whose URI is equal and whose end falls within 2Δ plus a minute of `ts`. For
  `recently-played` plays, whose `played_at` may be either end, allow the track's length plus a
  minute. Match one-to-one, nearest first, so a track played twice in a row stays two plays.
- **URI drift.** Spotify can substitute a different URI for the same recording ("track
  relinking"). Development mode no longer returns `linked_from`, which named the original (S20,
  verified), so the API's URI and the export's can differ for one play (inferred). Fall back to
  track title, album artist and time; or compare ISRCs from `external_ids`, at one
  `GET /tracks/{id}` per distinct track (S21).
- **The export wins.** Where both have a play, the export's `ms_played` replaces the poller's
  estimate. The poller's `context` (the playlist or album it was played from) has no equivalent
  in the export and is worth keeping (inferred).

For Q-C: the export gives the album artist, not the track's artists, and no track length or
ISRC (S5, S34). Anything that needs those, such as "every track featuring X", requires either
the metadata calls costed above or a cache filled over weeks. The item model should work with
the export's own fields and treat the rest as enrichment that arrives later (inferred).

## 5. Recommendation

**Backfill from the extended history; capture with our own poller of both endpoints; reconcile
by re-requesting the extended history every few months.** Last.fm is optional insurance for
poller downtime. ListenBrainz is not recommended, because it publishes listens.

Each part covers the others' losses:

| Loss | Covered by |
|------|------------|
| Years before the tracker ran | The first extended-history export |
| Listened time, live | Playback-state polling, 30 s / 3 min |
| Short plays; plays during a `429` or downtime | `recently-played` every 30 min, if completed |
| Offline, private-session, unseen partial plays | The next extended-history export |
| Poller down for more than 50 plays | The next export; or Last.fm, if connected |

Loss that remains: until the next export, a partial play the poller did not see is gone, and a
completed one carries its track length rather than its listened time. With an export every
three months that is at most three months of estimates, all corrected (inferred).

### What the owner does

1. **Today:** sign in at `https://www.spotify.com/account/privacy/`, request **Extended
   streaming history**, and also **Account data**, which arrives sooner. Click the confirmation
   email for each request, and check spam if it does not come. When the download email arrives,
   download the zip while signed in and keep it unmodified.
2. **Say whether the account has Premium.** Development mode requires it of the app owner (S18,
   S20). Without it, ongoing capture is exports alone.
3. **When M1 starts:** register one app in the Spotify Developer Dashboard with a
   `http://127.0.0.1:<port>/callback` redirect URI, sign in once, and keep the Client ID with
   the tracker's configuration.
4. **Every six months:** sign in again when the tracker says the refresh token is due (S13). A
   calendar reminder at five months is the fallback.
5. **Every three months or so:** request the extended history again, and hand the zip to the
   tracker's import.
6. **Optional:** connect Spotify to Last.fm in its application settings, as insurance for
   poller downtime.

## What could not be verified

- **The quota's size, buckets and reset period** for development mode. Spotify does not publish
  them (S15), and the two data points (S23, S28) are third-party and on different endpoints. M1
  measures this before it fixes the interval.
- **The privacy page's own wording** on preparation time, and how long a download link lasts:
  the page requires signing in. The 30 days is from third parties (S3, S4).
- **Whether `played_at` marks the start or the end** of a play (S26, unanswered), and whether
  `currently-playing`'s `timestamp` changes as documented. Both are measurable in M1.
- **The exclusion of partial plays** from `recently-played`: consistent community reports
  (S24), no statement from Spotify.
- **Whether `currently-playing` returns plays in a private session**: the device object has an
  `is_private_session` field (S9), but no page says what the endpoint does then.
- **Whether the export's username and user-agent fields** were dropped, or are absent only from
  the samples read (S1 against S4, S5).
- **Last.fm's default profile privacy and its scrobble rule for the Spotify connection.** The
  general scrobbling rule (over 30 s, half the track or 4 minutes, S32) is for clients that
  scrobble themselves.

## Sources

All read on 2026-09-23. **V**: verified on the page. **R**: reported by a third party, not
Spotify. Inferences are marked where they occur in the text, not here.

- **S1** (V) Spotify Support, "Understanding your data"
  https://support.spotify.com/us/article/understanding-my-data/
- **S2** (V) Spotify Support, "Data rights and privacy settings"
  https://support.spotify.com/us/article/data-rights-and-privacy-settings/
- **S3** (R) Digital Takeout Day, "Download your Spotify data" (updated 2026-08-23)
  https://takeoutday.org/guides/download-spotify-data
- **S4** (R) Ortham, "My Spotify extended streaming history data" (2024-12-21)
  https://blog.ortham.net/posts/2024-12-21-spotify-streaming-history-part-1/
- **S5** (R) Elastic Labs, sample extended-history record
  https://github.com/elastic/elastic-labs/blob/main/supporting-blog-content/spotify-to-elasticsearch/to_read/example.json
- **S6** (V / R) Spotify Community, "Why isn't my extended streaming history data ready yet?"
  (moderator, 2024-04-17)
  https://community.spotify.com/t5/Other-Podcasts-Partners-etc/Why-isn-t-my-extended-streaming-history-data-ready-yet/td-p/6009253
- **S7** (V) Web API reference, Get Recently Played Tracks
  https://developer.spotify.com/documentation/web-api/reference/get-recently-played
- **S8** (V) Web API reference, Get Currently Playing Track
  https://developer.spotify.com/documentation/web-api/reference/get-the-users-currently-playing-track
- **S9** (V) Web API reference, Get Playback State
  https://developer.spotify.com/documentation/web-api/reference/get-information-about-the-users-current-playback
- **S10** (V) Web API, Scopes
  https://developer.spotify.com/documentation/web-api/concepts/scopes
- **S11** (V) Web API, Authorization Code with PKCE
  https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow
- **S12** (V) Web API, Refreshing tokens
  https://developer.spotify.com/documentation/web-api/tutorials/refreshing-tokens
- **S13** (V) Spotify for Developers blog, "Introducing refresh token expiration" (2026-06-18)
  https://developer.spotify.com/blog/2026-06-18-refresh-token-expiration
- **S14** (V) Web API, Redirect URIs
  https://developer.spotify.com/documentation/web-api/concepts/redirect_uri
- **S15** (V) Web API, Quota modes
  https://developer.spotify.com/documentation/web-api/concepts/quota-modes
- **S16** (V) Web API, Rate limits
  https://developer.spotify.com/documentation/web-api/concepts/rate-limits
- **S17** (V) Blog, "Introducing some changes to our Web API" (2024-11-27)
  https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api
- **S18** (V) Blog, "Update on Developer Access and Platform Security" (2026-02-06, updated
  2026-03-09)
  https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security
- **S19** (V) Web API changelog, February 2026
  https://developer.spotify.com/documentation/web-api/references/changes/february-2026
- **S20** (V) February 2026 migration guide
  https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide
- **S21** (V) Web API changelog, March 2026
  https://developer.spotify.com/documentation/web-api/references/changes/march-2026
- **S22** (V) Web API changelog, July 2026 and blog, "Web API quota updates for Development Mode"
  (2026-07-23)
  https://developer.spotify.com/documentation/web-api/references/changes/july-2026
  https://developer.spotify.com/blog/2026-07-23-web-api-quota-updates
- **S23** (R) Spotify Community, "Web API quota updates for Development Mode" (staff post
  2026-07-23; replies to 2026-09)
  https://community.spotify.com/t5/Spotify-for-Developers/Web-API-quota-updates-for-Development-Mode/td-p/7508852
- **S24** (R) Spotify Community, "Bug with an API Recently Played Tracks" (2020-11 to 2025-01)
  https://community.spotify.com/t5/Spotify-for-Developers/Bug-with-an-API-Recently-Played-Tracks/td-p/5065969
- **S25** (R) Spotify Community, "Current User's Recently Played Tracks before param not working"
  (2021)
  https://community.spotify.com/t5/Spotify-for-Developers/quot-Current-User-s-Recently-Played-Tracks-quot-before-param-not/td-p/5133179
- **S26** (R) spotify/web-api issue 1083, inconsistent `played_at`
  https://github.com/spotify/web-api/issues/1083
- **S27** (V) ListenBrainz, maintainers' "Debugging Spotify Reader"
  https://github.com/metabrainz/listenbrainz-server/blob/master/docs/maintainers/spotify-reader.rst
- **S28** (R) anticuchito/spot-albums, `FINDINGS.md` ("verified against the live API on 2026-08-04")
  https://github.com/anticuchito/spot-albums/blob/main/FINDINGS.md
- **S29** (V) Last.fm Support, "Spotify Scrobbling"
  https://support.last.fm/t/spotify-scrobbling/189
- **S30** (V) Last.fm API, `track.scrobble`
  https://www.last.fm/api/show/track.scrobble
- **S31** (V) Last.fm API, `user.getRecentTracks`
  https://www.last.fm/api/show/user.getRecentTracks
- **S32** (V) Last.fm API, Scrobbling
  https://www.last.fm/api/scrobbling
- **S33** (V) ListenBrainz, About
  https://listenbrainz.org/about/
- **S34** (V) MetaBrainz blog, "GSoC 2025: Importing Listening History Files in ListenBrainz"
  (2025-08-30)
  https://blog.metabrainz.org/2025/08/30/gsoc-2025-importing-listening-history-files-in-listenbrainz/
- **S35** (V) ListenBrainz docs, JSON
  https://listenbrainz.readthedocs.io/en/latest/users/json.html
- **S36** (V) Yooooomi/your_spotify, README
  https://github.com/Yooooomi/your_spotify
- **S37** (R) Theodore Echo, "Spotify Recently Played Not Showing All Songs?" (2026-06, updated
  2026-08)
  https://www.theodorehq.com/echo/blog/posts/spotify-recently-played-missing-songs
