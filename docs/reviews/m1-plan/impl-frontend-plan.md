# impl-frontend plan — M1's Lane 7 (the web client) and Lane 3's frontend half

*Plan before code, read against `impl-director.md`, the scaffold at `a7cfbe4`, `docs/02`,
`docs/03` and ADR-0002/0003. Nothing was run, no code written. Planned under the three leanings.
`web/CLAUDE.md` is a `CLAUDE.md`, so the session's (overlay): its edits are listed, not made.*

## Where the cut does not survive my reading

1. **No issue names these screens** (the consolidation handoff: M1's remaining cut got none), and
   I build what an issue names. File four, each with route, endpoint and "done": sign-in
   (`/sign-in`; `POST /auth/login`, `GET /me`; a wrong password stays on the form, a stale cookie
   from any screen lands there); timeline (`/timeline`; `GET /events`; newest first, filters in
   the URL, "Load more" until `next_cursor` is null); totals (`/totals`; five groupings, four
   figures a row); sources (`/sources`; last success, last run, counts, Last.fm credit).
2. **"Lane 7 runs from the start, only `schema.d.ts` waits" does not hold.** Every hook and route
   names a response type, so no screen compiles before its schema exists, and plumbing merged
   ahead of its first caller is dead code. So two PRs: **W2**, sign-in, with the plumbing as its
   first commits, stacked on Lane 3's backend branch; **W3**, timeline, totals, sources (one
   commit each), stacked on W2 and Lane 6's contract. I write the plumbing early, unmerged.
   **Ask of Lanes 3 and 6:** the response models and regenerated `openapi.json` in the lane's
   *first* commit (a router answering an empty page is valid); else W3 starts at their last.
3. **Lane 6's endpoints leave holes that `docs/02` and `docs/03` already fix** (shapes below):
   - `item` is **nullable**: an unidentifiable watch is an event with no item (`docs/02` §1), so
     the row needs a placeholder; and since the item carries the service, a service filter drops
     these events. Lane 6 decides whether they stay in, and says so in the description.
   - **Local days.** A local day is a date and the zone one setting; the client must not compute
     either, or a timeline heading and a totals bucket can disagree. So `/events` items carry
     `local_date`, `from`/`to` are local dates (a date picker yields one), and `/me` carries
     `time_zone` (IANA) for clock times. Else I group by the browser's zone, wrong when travelling.
   - **A date string never goes through `new Date(s)`**: `"2026-10-05"` parses as UTC midnight and
     renders as the 4th west of Greenwich. `lib/format.ts` formats the parts in UTC; its test sets
     `TZ=America/Los_Angeles`.
   - **The estimate** is `length_ms` beside `duration_ms`; the basis says "about" or "up to", and
     the client derives none (§1: computed at read). **Totals** need `unattributed_events` (§1: "a
     total says how many events it left out") and ids on creator and item rows, so a row links to
     the timeline filtered by it. Four numbers are shown as four: **the client never sums them and
     never re-sorts a list**. Rankings are top-N.
   - A **`kind` filter** on both: decision 3's leaning imports podcasts and audiobooks "and
     filter in totals". Private-session and YouTube Music filters need `incognito_mode` and
     `header` promoted to columns first (§1); I build neither until then. `item.detail` and `raw`
     stay off the contract: nothing generic renders them.
4. **The 401 wiring cannot live in `main.tsx`**: the shell imports `routes/` alone, `ApiError` is in
   `api/`. So `api/sessionExpiry.ts`, free of React, started by `hooks/useSession.ts`: sign-in,
   sign-out and expiry all end as one event, `GET /me` answering 401.
5. **The target device is unnamed.** The definition says the README names it; it does not
   (ADR-0002: "phone-friendly"). I write it in: base styles for 360-430 px, one widening at 48rem,
   44 px touch targets, 16 px inputs; checked at 390x844, 360x740 and 1280x800.
6. **The Last.fm credit is a rendering duty** the cut files under Lane 4c (Spotify §6: "a credit
   and a link to Last.fm wherever the data is used"). An event carries no source, so no row can
   say it: a footer in the signed-in layout, and again by the Last.fm row on sources.
7. **`Health` is the scaffold's smoke test.** It stays the guarded index through W2, so sign-in
   lands on something real; unless the director wants a diagnostics page, the timeline commit
   deletes `routes/Health.tsx`, `hooks/useHealth.ts` and the `health` key, and `/` redirects to
   `/timeline`. The scaffold's "arrives with M1" sentences go as their feature lands.

## Lane 3 — sign-in, frontend half (W2). Gate: decision 2 and Lane 3's contract commit

- `api/errors.ts` (+ test): `isUnauthenticated`; `unwrapNoContent` (any 2xx, body unread: `unwrap`
  throws on a 204); `describeError(error)` giving `{message, requestId}` with a `default` branch
  (the class forbids an exhaustive list) and "Could not reach the server" for a plain `Error`;
  tests: `unexpected_response` hits the default, the request id passes through.
- `api/sessionExpiry.ts` (+ test): `watchSessionExpiry(queryClient)` returns the unsubscribe. Any
  other query failing `unauthenticated` invalidates `session`; the session query failing so
  removes every other query, so no finished session shows after the next sign-in. Node tests:
  the first re-runs the session `queryFn` once, not in a loop; the second leaves one query.
- `api/queryKeys.ts`: `session`, the one shared key (a hook reads it, `sessionExpiry` touches it);
  the timeline, totals and sources keys stay in their hooks.
- `hooks/useSession.ts`: `GET /me`, `retry: false`; `status` is `pending`, `signed-in`,
  `signed-out` or `unavailable` (any failure but 401, so an outage never bounces to the form),
  plus `timeZone`, `error`, `refetch`. `useSignIn.ts`, `useSignOut.ts`: the POSTs, each
  invalidating `session` on success.
- `components/ErrorNotice.tsx`: `{error, onRetry}`: the `describeError` text, the request id as
  "Reference", a Retry button. Every screen uses it; the section's first file.
- `routes/SignIn.tsx` (outside the guard): one `current-password` field; `unauthenticated` reads
  "That password was not accepted", else `ErrorNotice`; success goes to `state.from`, else `/`.
- `routes/SignedInLayout.tsx` (+ `.test.tsx`, jsdom): guard and chrome in one module. `pending`
  "Checking session"; `signed-out` `<Navigate to="/sign-in" replace state={{from}}>`;
  `unavailable` an `ErrorNotice`; `signed-in` the nav (a link per screen, added with its commit),
  `<Outlet/>`, the footer credit. The guard is courtesy; the API's `RequireSession` is the
  boundary. Test: four statuses, `from` survives the redirect, the link count, `/sign-in`
  outside the layout so it cannot loop.
- `App.tsx`: `/sign-in`, then the layout around the existing index. `main.tsx`: `QueryClient`
  defaults `retry: false` (three backoff retries hold a 401 on a spinner for seven seconds; Retry
  is in the UI) and `staleTime: 30_000` (a focus refetch re-requests every page of an infinite
  query).
- `layering.test.ts`: a `components: [hooks, routes]` row (props in; the route fetches) and a
  probe; `lib: [hooks, routes, components]` and its entry in the shell's row come with `lib/` in
  W3. "At least five files" becomes "every directory the shallow listing finds has a file in the
  recursive walk" (fails if the walk breaks, never needs raising); the pattern gains `import("…")`
  and bare `import "…"`, a probe each.
- `package.json`: `jsdom`, exact pin, with the first DOM test; no testing-library for one file.
  `index.css`: tokens and the phone-first base; `*.module.css` beside the routes.

## Lane 7 — the screens (W3). Gate: Lane 6's contract commit and W2

Inside the guard, one route per commit: `/timeline` (`?service&kind&from&to&creator&item`),
`/totals` (`?group&service&kind&from&to`), `/sources`; filters live in the URL; `*` stays.

- **Timeline.** `lib/format.ts` (+ test): clock, span and local-date formatters and
  `durationLabel(event)`, an exhaustive switch ending in `never` so a fourth basis breaks `tsc`:
  `3:12`, `about 3:40`, `up to 3:40`, `length unknown`. One `en-GB` constant; the UI is English.
  `lib/filters.ts` (+ test): URL input is untyped, so an unknown service, kind or group is dropped
  and a date must be real (`2026-02-31` is not); ids pass through one `parseId`; option lists are
  `Record<Service, string>` so a new enum value breaks `tsc` where a hand-copied list drifts.
  `lib/groupByDay.ts` (+ test): consecutive grouping by `local_date` over the flattened pages,
  order kept, one heading when a day spans a page. `hooks/useTimeline.ts`: `useInfiniteQuery`,
  `getNextPageParam: (last) => last.next_cursor ?? undefined`, the cursor back as received.
  `routes/Timeline.tsx`: filter bar with a clearable creator or item chip; rows of clock time,
  title (`Unidentified play` if `item` is null), creators in credit order, service, kind,
  `durationLabel`; "Load more", not scroll-paging; empty and error states.
- **Totals.** `hooks/useTotals.ts`; `routes/Totals.tsx`: tabs for the five groups, the filters,
  cards not tables on a phone. A row: a label and four figures labelled apart (measured;
  estimated; at most more; plays without a length). Buckets labelled from `bucket_start`; creator
  and item rows link to the timeline by id; `unattributed_events` above 0 prints "N plays with no
  item are not in this list".
- **Sources.** `hooks/useSources.ts`; `routes/Sources.tsx`: a card per source: last success as a
  time and an age, the last run's outcome (`failed` first-class), the four counts, the error, or
  "never run". No staleness threshold (cadence is the poller's); a failing one must not look quiet.

## The contract I build against (for Lanes 3 and 6 to plan against; theirs to correct)

```
GET  /me            MeResponse {time_zone}                401 envelope when signed out
POST /auth/login    {password}; /auth/logout -> any 2xx   wrong password: 401 unauthenticated
GET  /events        ?cursor&limit&service&kind&from&to&creator&item    from/to: local dates
  EventPage  {items: EventOut[], next_cursor|null}        started_at desc, id desc, published
  EventOut   {id, started_at, local_date, duration_ms|null, duration_basis, length_ms|null,
              item: ItemOut|null}
  ItemOut    {id, service, kind, title, creators: CreatorOut[]}            no detail
  CreatorOut {id, name, kind, service, role|null}         kind artist|channel|show; role in credits
GET  /totals        ?group=day|week|month|creator|item&service&kind&from&to&limit
  TotalsResponse {group, rows: TotalsRow[], unattributed_events}           0 for time groups
  TotalsRow  {bucket_start|null, creator|null, item|null, measured_ms, estimated_ms,
              upper_bound_ms, unknown_events, events}     omitted range: bounded, documented
GET  /sources       SourcesResponse {items: SourceOut[]}
  SourceOut  {key, service, last_success_at|null, last_run: RunOut|null}
  RunOut     {started_at, finished_at|null, outcome ok|failed|null, error|null,
              counts: {new, duplicate, matched, unmatched}}        typed, not an open object
```

## Tests and commands

Node by default; a DOM only in `SignedInLayout.test.tsx`. Tested: `format` (the TZ case, every
basis), `filters`, `groupByDay` (counts asserted), `errors`, `sessionExpiry`, the guard, a probe
per new layer row; not that a screen renders. Fixtures are literals typed by the generated
schema, so a contract change breaks them at `tsc`. From `web/`: `npm ci`, `npm run check:api-types`,
`npm test`, `npm run build` (what `web.yml` and the `web` gate run). **Real browser: not
promised.** I look for a browser tool at W2's start and the report says whether I had one. It
needs a dev API with rows: Lane 4a's fixture import (a committed sample of a dozen plays), or
before that an uncommitted stub on `API_PROXY_TARGET`, marked so. At the three sizes: sign-in
with a real cookie, a deleted cookie mid-session, load more, each group, a null item, long titles.

## If the owner decides otherwise

- **Key type (#10).** UUIDv7: ids are `string`; `bigint`: `number`. Ids are opaque to the client
  (`String(id)` for keys and URLs); `parseId` is the one function that changes.
- **Sign-in.** Bearer token: `client.ts` gains one `onRequest` middleware and a token store (a
  script-readable secret is the owner's to accept); `sessionExpiry` unchanged. Basic auth or a
  login at Caddy: no `/me`, no sign-in route, no guard, the browser prompts on 401, and
  `time_zone` needs a new home (a field on the `/events` and `/totals` responses).
- **§8 imports.** Dropping a class (private plays, podcasts): nothing. A zone per event:
  `time_zone` moves from `/me` onto each event, `formatTime` takes it per row, `local_date`
  survives. A placeholder item for a null item: the null branch goes and those plays join item
  totals.

## Not in my plan

An atlas screen, an event detail page, an import upload screen, charts, client-side aggregating
or sorting, a theme toggle, offline or PWA, i18n, `extension/`, `web/scripts/`, anything in `api/`.

## Needs, and what I hand on

- **Lane 3 backend:** `/me` with `time_zone`; the cookie `HttpOnly`, `SameSite=Lax`, `Path=/api`,
  `Secure` off on `http://localhost:5173` (one origin: `fetch` sends it unchanged); login
  throttling, if any, as a 429, which the closed code set carries as `invalid_request`.
- **Lane 6:** the shapes above. **Lane 4a:** the committed sample export. **The session:** the
  four issues, and `web/CLAUDE.md`: the pure-section sentence names `lib/` and `components/` with
  their rules, the `health` and "nothing needs a DOM yet" sentences go, the threshold sentence
  names the new check. `web/README.md` (mine): route table, device line.
