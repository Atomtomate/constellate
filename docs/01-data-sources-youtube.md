# 01 — Data sources: YouTube and YouTube Music

> **Research, not a decision.** This answers the YouTube half of Q-D in
> [`08`](08-open-questions.md) and is input to Q-C (the domain model) and Q-F (the apps). It
> recommends; the owner decides. The Spotify half is `01-data-sources-spotify.md`.

*Last updated: 2026-09-23*

## The answer in brief

Google keeps one record per video started, on every signed-in device, with the video, the
channel and a timestamp, and **never how long it was watched**. That record comes out three
ways: **Google Takeout** (the backfill, on request, minutes to days), **Takeout's scheduled
export** (every two months, a safety net), and, for accounts in the EU, Switzerland and the
UK, **Google's Data Portability API**, which may export it daily with the owner's consent.
The YouTube Data API has had no watch-history endpoint since 2016. It can still add each
video's length and channel after the fact, for a small share of the daily quota. The seconds
actually watched exist only where the watching happens, so they need a browser extension.
That covers desktop viewing only.

| Path | Gives | Misses | Build cost | Terms |
|------|-------|--------|------------|-------|
| Takeout, once | Every retained watch, all devices, years back | Duration; anything deleted or auto-deleted | A JSON parser | Google's own export |
| Takeout, scheduled | The same, every 2 months for a year | Freshness: up to 2 months late | Same parser; a manual download | Google's own export |
| Data Portability API | The same records, at most daily, incremental | Duration; unverified for a personal app (§3.2) | OAuth, a daily job, the same parser | Sanctioned; consent lapses after 180 days |
| Data API `videos.list` | Length, channel id, category per video | Removed and private videos | A batch job, an API key | Allowed; stored values expire after 30 days (§4) |
| Browser extension | Seconds actually played, start time | Phone, TV, other browsers | A small extension; upkeep when YouTube changes | Reading the owner's own playback; see §3.4 |

The recommendation (§6): request the Takeout today, spike the Data Portability API for an
hour, enrich with `videos.list`, and treat the extension as an optional add-on for measured
durations rather than a prerequisite of M1.

## How the claims are marked

Each load-bearing claim cites a source from the list at the end, as **[S*n*]**, with one of
three marks:

- **verified**: read on that page on 2026-09-23. Pages were read through a fetch tool that
  returns excerpts. A quotation here is what that excerpt showed.
- **reported**: a third-party page (a tool's README, a blog), not Google, says so.
- **inferred**: my reasoning, or read out of another project's code. It is stated as
  inference and should be checked against the owner's own export.

Anything neither verified nor reported is listed in §7 as unverified.

## 1. What Google records at all

Everything below depends on the account's **YouTube History** setting. With history turned
off, "any videos that you watch while history is turned off won't show up in your history"
**[S1, verified]**. The setting is under My Activity → YouTube History → Manage history →
Controls, and it can include or exclude watched videos and searches separately **[S1,
verified]**. If watched videos are excluded, no path in this document except the extension
sees anything.

**Auto-delete** is the second gate. The choices are 3, 18 or 36 months, or none **[S2,
reported: the search snippet of Google's help page; the fetched excerpt did not show the
list]**. Since 24 June 2020 the default is 36 months "if you create a new account or turn on
your YouTube History for the first time"; existing settings were not changed **[S3,
verified]**. With auto-delete on, the oldest month of history disappears every month. The
backfill cannot recover what has already gone, and every month's delay costs one more month.
**This is the one thing to check today.**

The history is the account's, not the browser's. Phone and TV viewing while signed in lands in
the same record **[inferred]**. The help page covers TV and console history controls
separately, so a TV can be set up differently **[S1, verified]**.

**My Activity** (`myactivity.google.com`) is a viewer over the same records, not a separate
source. It has no API, and scraping it is out of scope (`docs/00`, "Scraping a service's
private pages"). The Takeout file tags each record with `activityControls: ["YouTube watch
history"]` **[S9, reported]**, and the Data Portability API calls the same data
`myactivity.youtube` **[S12, verified]**. Both point to one store behind all three views
**[inferred]**.

## 2. Backfill: Google Takeout

At `takeout.google.com`, select **YouTube and YouTube Music**. The watch history arrives as
`Takeout/YouTube and YouTube Music/history/watch-history.json`, or `.html`. History comes as HTML or
JSON, the rest of the YouTube data as CSV **[S10, reported]**. **Choose
JSON.** The HTML form is one page of localised date strings. The JSON gives an ISO 8601 UTC
timestamp per record **[S9, reported example: `"2026-07-24T12:34:56.000Z"`]**.

### The record

Google publishes the schema of activity records in `google/takeout` **[S8, verified]**. The
YouTube file is a flat JSON array, one object per event **[S9, reported]**:

| Field | Holds | Source |
|-------|-------|--------|
| `header` | The product: `"YouTube"` or `"YouTube Music"` | S8 verified (field); S9, S13 reported, S14 inferred (values) |
| `title` | `"Watched <video title>"`; the verb is in the account's language | S8 verified; S15 reported (language) |
| `titleUrl` | The video's URL; the video id is its `v=` parameter | S8 verified |
| `subtitles[]` | `name` = channel title, `url` = `https://www.youtube.com/channel/UC…` | S9, S11 reported |
| `time` | "Time and date the user did the activity", ISO 8601 UTC | S8 verified; S9 reported (format) |
| `products` | `["YouTube"]` | S8 verified |
| `details[]` | Present when the event came from an ad: `"From Google Ads"` | S8 verified |
| `activityControls` | `["YouTube watch history"]` | S9 reported |
| `description` | Optional free text; its use for YouTube is not documented | S8 verified (field exists) |

**There is no duration field.** Google's schema lists none **[S8, verified]**. The Data
Portability schema for the same records lists none **[S12, verified]**. Third-party pages say
the same **[S9, reported]**, one in so many words: "The data export does not show how long you
watched a video for" **[S10, reported]**. A watch lasting "only a few seconds still counts"
**[S10, reported]**.

The channel id is already in the file: it is the tail of `subtitles[0].url`. The backfill needs
the Data API only for the video's length and category, not for the channel **[inferred from
S9, S11]**.

### What is in it, and how to tell it apart

- **YouTube Music vs YouTube.** Music plays are in the same file and carry `header: "YouTube
  Music"` **[S9, S13, reported]**. One statistics tool keeps exactly the records with that
  header whose title starts with `Watched` **[S14, inferred from its code]**. The URLs
  conflict: one page says music entries use `music.youtube.com` **[S9, reported]**. That tool
  instead cuts the video id at character 32, the length of `https://www.youtube.com/watch?v=`,
  which implies `www` URLs **[S14, inferred]**. **Tell them apart by `header`, never by URL.**
  Songs proper come from `"<Artist> - Topic"` channels **[S13, reported]**. A music video
  played in YouTube Music is a Music event whose channel is not a Topic channel.
- **Ads** carry `details: [{"name": "From Google Ads"}]` **[S8, verified: the schema's YouTube
  example]**. They are dropped on import.
- **Shorts.** **Not verified.** No page I read says whether Shorts appear or how they are
  marked. If they are present, they are probably ordinary `watch?v=` records, told apart only
  by length after enrichment **[inferred]**. The owner's own export settles it.
- **Removed and private videos** appear with a generic title and no usable URL or channel
  **[S9, reported]**. They cannot be enriched, so their duration stays unknown.
- **Rewatches.** Each play appears to be its own record. Scrobbling tools count repeat plays
  of a song by counting its records **[S14, inferred from its code]**.
- **The title's verb is localised.** The same tool tells users to switch the account to
  English or edit its string matching **[S15, reported]**. A parser strips a known list of
  prefixes, or takes the title from the Data API.

### How far back, how long, how often

- **How far back**: to the start of the account's retained history. That excludes whatever was
  deleted by hand and, where auto-delete is on, everything older than its window (§1). No
  page I read documents any other cap **[inferred]**. One page reports that older YouTube
  Music entries can be missing **[S16, reported]**.
- **How long it takes**: "from a few minutes to a few days. Most people get the link to their
  archive the same day" **[S4, verified]**. The archive "expires in about 7 days", with at most
  five downloads **[S4, verified]**.
- **Recurring**: Takeout offers "every 2 months for one year", and can deliver to Drive,
  Dropbox, OneDrive or Box instead of by email **[S4, verified]**. That makes six exports a
  year, each a full archive rather than a delta **[inferred]**. It cannot meet `docs/00`'s
  "in the log by the next morning". It is a safety net, not the capture.

## 3. Ongoing capture

### 3.1 The YouTube Data API has no watch history

The `watchHistory` related playlist was deprecated on 11 August 2016. Since 15 September
2016, "requests to retrieve playlist items (`playlistItems.list`) in either of those playlists
now return empty lists" **[S5, verified: the revision history]**. Today's `channels` resource
lists only `likes`, `favorites` (deprecated) and `uploads` under `relatedPlaylists` **[S6,
verified; page updated 2026-09-16]**. No replacement exists in the Data API.

### 3.2 Google's Data Portability API: sanctioned and recurring, with an open question

Google's Data Portability API exports "user activity data from products such as … YouTube"
to an app the user authorises **[S17, verified]**. The YouTube resource is
`myactivity.youtube`. Its records have the same fields as Takeout's, with no duration **[S12,
verified]**.

- **Recurring.** The user grants access "once, 30 days, or 180 days" **[S18, verified]**.
  During that time the app may export again after 24 hours: "Requested resources have already
  been exported. You can initiate another export after …" **[S18, verified]**.
  `myactivity.youtube` supports `start_time`/`end_time` filters, and "you can use Time Filters
  with Time-Based Access to export the new data since your last export" **[S19, verified]**.
  That makes a daily, incremental pull of every YouTube and YouTube Music watch from every
  device.
- **Mechanics.** `InitiatePortabilityArchive` with the resource returns a job id.
  `GetPortabilityArchiveState` is polled, and a complete job yields signed Cloud Storage URLs.
  "The time it takes … can vary from minutes to hours" **[S20, verified]**.
- **Where.** Only for accounts in the 27 EU states, Switzerland and the UK **[S21, verified:
  the list]**, and not for users under 18 **[S22, verified]**. Whether the owner's account
  qualifies is the owner's to confirm.
- **The open question: can a personal, unverified app use it?** Google says apps using the API
  "are subject to a verification process", with a security assessment for restricted scopes
  **[S22, verified]**. The API's own policy exempts only apps "used only by users within your
  organization" **[S23, verified]**. Google's general OAuth help says an app for "personal use
  (fewer than 100 users)" can run without verification, users clicking through the
  unverified-app warning **[S24, verified]**. A project left in *Testing* status gets refresh
  tokens that expire in 7 days **[S25, verified]**. A 7-day token would defeat a 180-day grant,
  so the app would have to be published unverified. **Whether that works with a Data
  Portability scope is not verified.** A one-hour spike answers it (§6).
- **Terms.** This is the path Google built for exactly this purpose. The costs are consent
  renewed twice a year and the policy's requirements to encrypt at rest and limit use to
  visible features **[S23, verified]**.

### 3.3 Takeout on a schedule

This is the fallback if §3.2 fails. It gives the same records up to two months late, and the
owner downloads a file by hand (§2). It is also worth keeping beside §3.2 as a second copy of
the source, because it costs nothing.

### 3.4 A browser extension: the only route to seconds watched

A content script on `youtube.com` and `music.youtube.com` can watch the page's `<video>`
element. From its play, pause, seeking and ended events it records the video id, the start
time, the seconds actually played and the playback rate, and posts them to the tracker. Both
sites play through an HTML5 video element **[inferred; not checked against the current
markup]**.

- **Gives**: the only true "how long" on YouTube, and the only live signal independent of the
  account's history setting.
- **Misses**: the phone app, the TV, every browser or profile it is not installed in, and
  incognito unless allowed. For those, the history record (§2, §3.2) is the only trace.
- **Cost**: a small Manifest V3 extension (a content script and a service worker), loaded
  unpacked in Chromium or self-distributed for Firefox. It is a few hundred lines **[inferred
  estimate]**. The standing cost is upkeep: YouTube is a single-page app whose navigation and
  markup change. Reading only the video element and the URL's `v=` keeps that dependency
  small.
- **Off the shelf**: Web Scrobbler, an open-source scrobbling extension, can post to a
  webhook. Its events are `nowplaying`, `scrobble`, `paused` and `resumedplaying`. Each event
  carries a song object with `duration`, `currentTime` and the page's `originUrl` **[S26,
  verified: the webhook wiki, v3.2.0+]**. It is built for music, and whether it reports
  non-music YouTube videos is **not verified**. For YouTube Music it may make a custom
  extension unnecessary. A trial costs an evening.
- **Terms.** YouTube's terms forbid accessing the service "using any automated means (such as
  robots, botnets or scrapers)" without permission **[S7, verified; terms effective 15
  December 2023]**. An extension that observes playback the owner started by hand is, in my
  reading, not automated access **[inferred; not legal advice]**. It must never fetch pages,
  start playback or read beyond the page being watched. The Data API's developer policies also
  forbid an API client from scraping, or from using "any technology other than YouTube API
  Services to access or retrieve API Data" **[S27, verified]**. If the extension and the
  enrichment job count as one API client, the safe line is this: the extension records what
  the owner did (id, times, seconds), and titles and lengths come from the API **[inferred]**.

### 3.5 Considered and rejected

- **`ytmusicapi`'s `get_history`**: an unofficial library that drives YouTube Music's
  internal API with the owner's browser session. Its docs say only that each item's `played`
  "indicates when the playlistItem was played" **[S28, verified]**, so the granularity is
  unknown. It is automated access in the sense of the terms' item 3 **[inferred]**. Rejected.
- **Reading `youtube.com/feed/history` or My Activity**: scraping, excluded by `docs/00` and
  by the terms **[S7, verified]**.
- **An Android media-session scrobbler** would reach the phone, where the extension cannot.
  **Not researched here**; it is a Q-F candidate.

## 4. Durations and enrichment: `videos.list`

`videos.list` takes a comma-separated list of video ids **[S29, verified]** and returns, per
video:

- `contentDetails.duration`: "The length of the video … an ISO 8601 duration", for example
  `PT#M#S` **[S30, verified]**.
- `snippet.channelId`, `snippet.channelTitle`, `snippet.title`, `snippet.categoryId` and
  `snippet.publishedAt` **[S30, verified]**. A video's `channelId` "can change over time",
  for example when a video is reassigned **[S30, verified]**.

**Cost.** "A call to this method has a quota cost of 1 unit" **[S29, verified]**. The default
allocation is "100 `search.list` calls, 100 `videos.insert` calls, and 10,000 units per day
combined for all other endpoints". Those two methods got their own buckets on 1 June 2026
**[S31, S5, verified]**. More quota is available by request form **[S32, verified]**.

**Key or OAuth.** "A request that does not provide an OAuth 2.0 token must send an API key"
**[S33, verified]**. Public video metadata needs only a key. OAuth is for private user data,
which enrichment does not touch.

**How 50,000 rows fit.** Rewatches collapse to unique ids first. Third-party pages put the
limit at 50 ids per call **[S34, reported]**. Google's page states no limit **[S29,
verified: none stated]**. At 50 per call, 50,000 unique videos take 1,000 calls, which is
**1,000 units, a tenth of one day's quota**. Even at one id per call it would be 50,000
units, which is five days. Removed and private videos come back as not found **[S29,
verified: the `videoNotFound` error]** or are left out of the response (**not verified**
which). Either way they stay without a length.

**The 30-day rule, which shapes the model.** The developer policies allow an API client to
store Non-Authorized Data "not longer than 30 calendar days", after which it must be deleted
or refreshed **[S27, verified]**. Refreshing 50,000 videos monthly costs the same 1,000
units, so the rule is cheap to obey. It does, however, change the data's shape: video length
and category are a refreshable **cache**, not columns of the log. Title, channel name and
channel id come from the owner's own Takeout record, not from the API, so the log can keep
them permanently **[inferred]**. Q-C should keep the two apart.

## 5. What "how long" can mean, and joining the two records

| Path | "How long" | Kind |
|------|-----------|------|
| Extension | Seconds of media actually played, excluding pauses and skipped spans | measured |
| History + `videos.list` | The video's length: an upper bound for one play | length |
| History + `videos.list` + the next record | `min(length, time until the next watch)` | estimate |
| History, video removed or private | Nothing | unknown |

The estimate works because watching is mostly sequential. For YouTube Music, where one song
follows the next, it is close. For an evening of abandoned videos it overcounts
**[inferred]**. Each event should carry its duration together with the **kind** of duration,
so a total can say how much of itself is measured. That is an input to Q-C, not a decision.

**Matching.** A history record and an extension record for the same watch share the video id
and a nearby time. The history's `time` is probably logged when playback starts
**[inferred; not verified]**. So the join is on the video id, pairing each extension record
with the nearest unclaimed history record within a window of minutes, one-to-one and in
order, so that rewatches pair up correctly. A matched pair keeps the history record as the
event and the extension's seconds as its measured duration. An unmatched history record is
viewing the extension could not see (phone, TV). An unmatched extension record means the
history setting excluded it, or it was a signed-out watch. The window's width is tuned
against the owner's first week of real data.

## 6. Recommendation

**Takeout JSON for the backfill, the Data Portability API for daily capture (scheduled
Takeout if the spike fails), `videos.list` for lengths, and the extension later, for measured
seconds on desktop.** This loses nothing Google keeps, and it gets the timeline running
without writing an extension first.

What the owner can do today, in about five minutes:

1. **My Activity → YouTube History.** Confirm it is on, with watched videos included. Look
   at auto-delete. If it is 3, 18 or 36 months, the oldest history is being deleted monthly
   (§1). Turning it off is a privacy choice only the owner can make, but the Takeout should be
   requested before the next month's deletion either way.
2. **Takeout.** At `takeout.google.com`, deselect all and select *YouTube and YouTube Music*.
   Under its content options keep *history*. Under formats, set *history* to **JSON**. Export
   once, delivered by email. Most arrive the same day (§2), and the link lasts about 7 days.
3. Optionally add a second, scheduled export every 2 months as the safety net (§3.3).

What the tracker does next, in order:

1. **Spike the Data Portability API (about an hour).** Create a Google Cloud project, enable
   the API, and publish the consent screen unverified. Grant `myactivity.youtube` for 180
   days from the owner's account, run one export, and run another 8 days later. That second
   export proves the refresh token outlived the 7-day testing limit (§3.2). Pass: daily
   capture needs no extension. Fail: scheduled Takeout carries the history, and freshness
   becomes the extension's job.
2. **Import the Takeout**: drop ads, split by `header`, strip the localised verb, and keep the
   channel id from `subtitles`.
3. **Enrich** with `videos.list` under an API key, 50 ids a call, cached and refreshed within
   30 days (§4).

**For Q-F.** The browser extension moves from "needed for YouTube capture" to "needed only for
measured durations, and only on desktop". Q-D's starting leaning was that live capture needs
something running where the watching happens. If the spike passes, that holds for *how long*
but not for *what and when*. M1 can ship with estimated durations marked as estimates, and
the extension becomes a separate, later decision. Web Scrobbler's webhook should be tried
before building one. If the spike fails, the extension is the only same-day signal on desktop,
and the case for building it in M1 is stronger.

## 7. Not verified

- Whether an unverified, personal app can hold a 180-day Data Portability grant (§3.2): the
  spike's question.
- Whether Shorts appear in the history, and how they are marked (§2).
- Which host YouTube Music records' `titleUrl` uses. Sources conflict; `header` is used
  instead (§2).
- Whether `time` is logged at the start of playback (§5).
- The 50-id limit per `videos.list` call: third-party only (§4). Whether missing videos are
  left out of the response or return an error.
- The auto-delete choices of 3, 18 and 36 months: seen only in a search snippet of Google's page
  (§1).
- Whether Web Scrobbler reports non-music YouTube videos (§3.4).

The owner's first Takeout settles the Shorts and URL questions minutes after it arrives. The
spike settles the first. A week of extension data beside the history settles the timing.

## Sources

All read on 2026-09-23.

- **S1**: History on/off; paused history records nothing; TV controls separate.
  https://support.google.com/youtube/answer/95725
- **S2**: Auto-delete after 3, 18 or 36 months (search snippet).
  https://support.google.com/youtube/answer/95725?hl=en
- **S3**: 36-month default since 24 June 2020.
  https://blog.google/innovation-and-ai/technology/safety-security/keeping-private-information-private/
- **S4**: Takeout duration, schedule, delivery, link expiry.
  https://support.google.com/accounts/answer/3024190
- **S5**: `watchHistory` withdrawn 2016; quota buckets 2026-06-01.
  https://developers.google.com/youtube/v3/revision_history
- **S6**: `relatedPlaylists` today (updated 2026-09-16).
  https://developers.google.com/youtube/v3/docs/channels
- **S7**: Terms of Service, effective 15 December 2023.
  https://www.youtube.com/static?template=terms&hl=en&gl=US
- **S8**: Google's activity-record schema, YouTube examples.
  https://github.com/google/takeout
- **S9**: Record example, Music header, removed videos.
  https://playbackstats.com/guides/youtube-watch-history-json
- **S10**: No duration; a few seconds counts; HTML or JSON.
  https://portmap.dtinit.org/articles/watch-history2.md/
- **S11**: `subtitles.url` as a `/channel/` URL (a converter's output example).
  https://github.com/MehdiHadizadeh/youtube-history-converter/blob/main/README.md
- **S12**: `myactivity.youtube` fields (updated 2025-02-13).
  https://developers.google.com/data-portability/schema-reference/my_activity
- **S13**: Music entries flagged by header; Topic channels.
  https://github.com/beebls/youtube-music-history-scrobbler
- **S14**: Code: `header == "YouTube Music"`, id sliced at 32.
  https://raw.githubusercontent.com/cinfulsinamon/ytmusic_wrapped/python3/main.py
- **S15**: Title strings depend on account language.
  https://github.com/cinfulsinamon/ytmusic_wrapped/blob/python3/README.md
- **S16**: Older Music entries reported missing (2026-07-27).
  https://musicprofileviewer.com/blog/youtube-music-history/
- **S17**: What the API is; YouTube among its products.
  https://developers.google.com/data-portability
- **S18**: Once / 30 / 180 days; one export per 24 h.
  https://developers.google.com/data-portability/user-guide/time-based
- **S19**: Time filters on `myactivity.youtube`; incremental.
  https://developers.google.com/data-portability/user-guide/time-filter
- **S20**: Archive job flow; minutes to hours.
  https://developers.google.com/data-portability/user-guide/introduction
- **S21**: Countries where it is available.
  https://support.google.com/accounts/answer/14452558
- **S22**: Verification, security assessment, under-18.
  https://developers.google.com/data-portability/user-guide/overview
- **S23**: Organisation-only exemption; encryption; limited use.
  https://developers.google.com/data-portability/policy
- **S24**: Personal use under 100 users without verification.
  https://support.google.com/cloud/answer/13464323?hl=en
- **S25**: 7-day refresh tokens in Testing (updated 2026-05-26).
  https://developers.google.com/identity/protocols/oauth2
- **S26**: Webhook events and payload.
  https://github.com/web-scrobbler/web-scrobbler/wiki/Webhook-API
- **S27**: 30-day storage; no scraping (updated 2026-09-14).
  https://developers.google.com/youtube/terms/developer-policies
- **S28**: `get_history`'s `played` field.
  https://ytmusicapi.readthedocs.io/en/stable/reference/library.html
- **S29**: 1 unit per call; errors; no id limit stated.
  https://developers.google.com/youtube/v3/docs/videos/list
- **S30**: `contentDetails.duration`, `snippet` fields.
  https://developers.google.com/youtube/v3/docs/videos
- **S31**: Default allocation and per-method cost.
  https://developers.google.com/youtube/v3/determine_quota_cost
- **S32**: Quota extension form.
  https://developers.google.com/youtube/v3/getting-started
- **S33**: API key vs OAuth.
  https://developers.google.com/youtube/registering_an_application
- **S34**: 50 ids per call (search excerpt).
  https://www.technetexperts.com/youtube-api-videos-list-id-limit/
