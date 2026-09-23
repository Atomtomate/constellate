# Spotify data source researched
**Summary:** Wrote `docs/01-data-sources-spotify.md`: the extended streaming-history export as the backfill, a dev-mode poller of playback state and `recently-played` for live capture, and periodic re-exports to reconcile.
**State:** Open — the owner reads the recommendation, requests the export, and says whether the account has Premium; Q-D's Spotify half and Q-C's fields then move in `docs/08`.

## What was done

- Researched how Spotify listening history is obtained, on a branch of its own
  (`claude/spotify-data-source`), and wrote it up as `docs/01-data-sources-spotify.md`. It
  covers the three download packages and the extended history's fields and flaws, the Web API
  as it stands after the February, March, May and July 2026 changes and the June 2026
  refresh-token expiry, Last.fm and ListenBrainz, what "how long" means on each path, how to
  match export and API plays, and a recommendation with the owner's steps.
- Every load-bearing claim names one of 37 numbered sources, each read on 2026-09-23 and marked
  verified on the page or reported by a third party; inferences are marked where they occur.
- Decided nothing: `docs/07` and `docs/08` are untouched, as the brief required. The document
  says which of Q-D's leanings it confirms and which it changes.

## How it was verified

- Spotify's developer pages (reference, quota modes, rate limits, scopes, PKCE, refresh tokens,
  redirect URIs, the 2026 changelogs, the migration guide and three blog posts) were downloaded
  and read as stripped text, not through a summarising fetch. That caught a summariser's error:
  it reported the July 2026 increase to 25 as *users* per app; the page says *Client IDs* per
  developer account, and users stay at five.
- Spotify Community threads, which refuse plain fetches, were read in the built-in browser.
  They were read, not signed in to.
- The ListenBrainz behaviour is from its maintainers' own document in the server repository;
  Last.fm's from its support FAQ and API pages.
- `python scripts/check_docs.py` passes. Every line is at most 100 columns except bare URLs,
  which cannot be broken.
- Not verified, and said so in the document: the development-mode quota's size and reset
  period; the privacy page's own wording on preparation time (it requires signing in); whether
  `played_at` marks the start or the end of a play; whether `recently-played` omits partial
  plays by design; what `currently-playing` returns in a private session.

## What remains open

- **The owner requests the extended streaming history today**, and account data with it. It
  can take up to 30 days, and nothing else backfills.
- **The owner says whether the account has Premium.** Development mode requires it of the app
  owner since February 2026; without it the API path is closed and capture is exports alone.
- **Q-D's Spotify half** can move to "Answered" in `docs/08` once the owner accepts the
  recommendation. Q-D's current leaning is right about the export and the 50-play window, and
  wrong in one respect: polling `recently-played` often is not enough, because it omits partial
  plays and never carries listened time.
- **Q-C** gains three inputs: the export has the album artist, not the track's artists, and no
  track length or ISRC; enriching them costs one request per distinct track under a quota; an
  event's duration needs a provenance (measured or estimated).
- **Q-E** gains a constraint: the poller runs around the clock and must survive a six-monthly
  sign-in.
- **M1's first spike**: measure the quota by polling at 30 s / 3 min with every `429` and its
  `reason` logged, and settle `played_at` and `timestamp` semantics against the owner's own
  plays.

## What carried it

Downloading Spotify's pages and reading them as text, rather than trusting a summarising fetch:
one summary turned "25 Client IDs" into "25 users", which would have reversed a finding. The
third-party `FINDINGS.md` in `anticuchito/spot-albums` (verified against the live API on
2026-08-04) was the one source with measured quota numbers; it is cited as reported, not as
fact.
