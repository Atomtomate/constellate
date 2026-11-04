Reviewed at beb11317c061

**Verdict:** Fix before merge: the export–poller pairing misses every play paused for more than two
minutes, and the play is then counted twice; two smaller gaps sit beside it.

### 1. Medium: the export–poller pair compares a poller "end" that leaves out pauses

- **file:line** `api/src/constellate/domain/matching.py:97`: `Play.at(Moment.END)` is
  `started_at + duration_ms`, but the poller's `duration_ms` is listened time with pauses left out
  (`docs/01-data-sources-spotify.md` §2), while the export's `ts` is the wall-clock end. For a
  paused play the two ends differ by the pause, and the 2Δ + 1 min window (`matching.py:63`) misses.
- **Failure:** a 180 s listen starts 12:00:00, is paused 7 min and ends 12:10:00. The poller has
  `started_at` 12:00:00 and `duration_ms` 180 000, so its computed end is 12:03:00. The export has
  `ts` 12:10:00, so `started_at` is 12:07:00 and its end is 12:10:00. On the branch,
  `pair_in_order([Slot((poller,))], [export], MatchWindows())` returns `(None,)`; with a 90 s pause
  it pairs. The scrobble cannot rescue it, because its start is also 7 min from the export's derived
  start. Under the plan's re-sourcing rule the unmatched live event is kept, so the play counts 360 s
  for 180 s. Podcast episodes have no other pair (Last.fm never scrobbles them), and they are the
  plays most often paused.
- **Confidence:** certain about the behaviour; how often pauses run past 2 min, only the owner's
  data can say.
- **Fix:** Code: pair on the observed end (the export's `ts`, the poller's closing sample) at
  `Moment.END`. The draft has no field for the poller's end, so `docs/02` §2 changes first, then a
  test of the paused play above.

### 2. Low: a draft accepts text Postgres cannot store, so one bad record fails its batch

- **file:line** `api/src/constellate/domain/draft.py:101-117`: `__post_init__` says it refuses
  "what no column could hold". It still accepts U+0000 in `record_key`, `ItemHint.title`,
  `CreatorHint.name` and `raw`, and NaN or Infinity in `raw` (`json.dumps` allows NaN by default).
- **Failure:** on the branch, `DraftEvent(..., record_key="k\x00", item_hint=ItemHint("spotify",
  ItemKind.TRACK, "a\x00b"), raw={"name": "a\x00b", "x": float("nan")})` builds. Postgres refuses
  NUL in `text`, and `\u0000` or `NaN` in `jsonb`. The insert therefore raises inside the batch's
  transaction rather than the record counting as rejected. Scrobblers submit arbitrary metadata, so
  for `lastfm-scrobbles` the cursor would never pass such a record, every later poll would fail on
  it, and the live tail would stop. SQLite stores all of it, so the default test backend never
  sees the failure.
- **Confidence:** likely. Postgres's refusals are documented behaviour; this was not run against
  Postgres, because Docker is down.
- **Fix:** `json.dumps(..., allow_nan=False)`, and refuse `"\x00"` in the key, the title, the names
  and the serialised `raw`, each as a `ValueError`.

### 3. Low: no test pairs a YouTube extension play with its Takeout or Portability record

- **file:line** `api/tests/test_domain_matching.py`: no test pairs anything through the YouTube
  window (`matching.py:66-67`). `youtube-extension` appears only as the stream with no window to the
  export, and Takeout only as never pairing with Portability.
- **Failure:** with that `MatchWindows.between` branch monkeypatched to return `None`, all 82 tests
  still pass (run on the branch). That regression would turn every desktop watch into two events,
  Takeout's `start_only` and the extension's `measured`.
- **Confidence:** certain
- **Fix:** a test pairing `youtube-extension` drafts with `youtube-takeout` and `google-portability`
  slots, inside and just outside `google_extension`.

## Follow-ups

- `api/src/constellate/domain/vocab.py`'s docstring says a test pushes every member through the ORM,
  but no such test exists: `models/` has no CHECKs yet, and the pinning test compares against
  literals typed into the test. Lane 1, or 2b, adds the guard with the first migration.

## What carried it

`docs/01-data-sources-spotify.md` §2 describes how the poller measures: "while `is_playing` is true,
the play's listened time grows". Read next to `Play.at` while checking what the export–poller END
window actually compares, it exposed finding 1.
