# impl-director plan check — M1, round 1

*2026-10-11. Direction and broader-context check of the three specialist plans against
`impl-director.md` (the plan of record, which I authored and have now amended in place; the
changes are marked `[C1]` there), `docs/02-domain-model.md`, `docs/03-architecture.md`,
ADR-0002/0003 and the overlay's ownership map. Implementation detail inside a layer is the
specialist's and is not judged here. `gh` was not called (rate-limited).*

Plans read in full: `impl-database-plan.md`, `impl-backend-plan.md`, `impl-frontend-plan.md`.
None missing. All three planned under the leanings and said what each decision changes, as asked.

## What each got right

- **Database** cut Lane 1 to exactly `docs/02` §7, drafted every repo signature and the
  later-lane "small tasks", honoured the SQL line (the lock is its SQL), and caught the four
  invariants ADR-0003 forces that my cut left implicit (the lock, re-sourcing deletes, candidates
  with all observations, the run row committed before the first batch).
- **Backend** split Lane 2 cleanly into pure `domain/` and the orchestration, located re-sourcing
  in the one service, shaped `SourceAdapter` from the sources that actually have cursors, and read
  the layering correctly on where matching and the vocabulary enums live.
- **Frontend** found the real client-facing holes in the read contract (nullable item, local days,
  the estimate field, ids on totals rows), located the 401 wiring off the shell, and was right
  that no issue names its screens and that the client cannot "run from the start".

## Accepted and changed in `impl-director.md`

1. **`event.service`** (database pushback 2). A null-item event has no item to read a service
   from, yet `docs/02` §1 shows it on the timeline and the service filter must not drop it.
   Service is invariant per event (matching never crosses services), so this is not a *source* on
   the event and does not break ADR-0003. Added to Lane 1 under decision 3's null-item leaning;
   dropped under the placeholder-item alternative. `docs/02` §1 gains the row (session, with #17).
2. **Candidate lookup is a span read, matched in `domain/`** (backend pushback 2; declines the
   database's `find_candidates_by_name` doing name-equality in SQL). The windows and name-key
   equality are tunable rules (ADR-0003; `docs/02` §2), so they may not live in a repo. Lane 1
   amended; the repo may still narrow by item id.
3. **Re-sourcing is Lane 2's, not 4c's** (both database and backend). The three behaviours written
   into Lane 2; the cut had named it only under the adapter.
4. **`SourceAdapter` shaped by all documented sources** (backend pushback 4), `fetch(cursor)`
   cursor-optional. My "shaped by Lane 4a" was wrong — a file has no cursor.
5. **Repo scope and the later-lane small tasks** (database pushback 1): Lane 1 ships only what
   Lane 2 steps 1–5 call; timeline/totals/disconnect/enrich repos are briefed when their lane
   plans. My own SQL-line rule already said this; the cut's Lane 1 bullet now matches it.
6. **`/totals` split into three paths, rankings top-N by `limit`** (backend §6; database and
   frontend concur on top-N). Declines frontend's single `?group=` endpoint: three typed responses
   beat one with every field nullable, and periods vs rankings paginate differently. The top-N
   departure from the cursor convention is reasoned and confined to aggregates; `docs/03` gets a
   note (session).
7. **Local-day fields on the read contract** (frontend pushback 3): `local_date` on `/events`,
   `time_zone` on `/me`, local-date range filters, a `kind` filter. The server owns the one
   configured zone (`docs/02` §8); the client recomputing local days would disagree with the
   totals buckets. Resolves the backend/frontend disagreement in frontend's favour on direction.
8. **The `kind` filter ships; private-session and YouTube-Music-split filters wait on a column**
   (backend §6, frontend §3): `incognito_mode`/`header` are raw-only, so those two totals ship
   unfiltered until a later migration — out of M1 scope, surfaced under decision 3.
9. **Last.fm credit is Lane 7's display duty** (frontend pushback 6), not 4c's; 4c keeps the cap
   and the delete-all path.
10. **Lane 7 is two gated PRs, not "from the start"** (frontend pushback 2); the session files the
    missing screen issues (frontend pushback 1); the `Health` screen retires with the timeline,
    the endpoints stay (frontend pushback 7, confirmed — no diagnostics screen).
11. **Backend regenerates `schema.d.ts` in its contract PR** (backend pushback 7): `web.yml` fails
    otherwise and the map forbids a hand-off just to run codegen. Noted as a mechanical exception
    and a map gap (friction filed).
12. **Smaller, accepted into the lanes**: cache rows carry the supplying Spotify source id and a
    merged item's length is the longest fresh (Lane 5); audiobook author maps to `show` (`docs/02`
    §6, not an owner ask); the item-precedence order is backend's reading of ADR-0003, tunable in
    `domain/`, confirmed not an owner decision; the stale record edits per lane (session's).
13. **Decision 2 sharpened** (database pushback 5): the stateless-cookie vs stored-session
    sub-choice named, with stored sessions as a separate `0003` not blocking Lane 1. Leaning:
    stateless. Typo `httatonly` fixed.

## Declined, with the reason

- **Name-matching in SQL** (`find_candidates_by_name`): declined — see accept 2; matching is a
  tunable domain rule, not a repo query.
- **A single `/totals?group=` endpoint** (frontend's sketch): declined — see accept 6; three typed
  responses serve the generated client better.
- **SQLite emulation of `date_trunc` totals** (not proposed, confirmed): declined as a design; the
  at-zone cases are Postgres/CI hand-run, which the verification section already allows.

## Unresolved — round 2 or the owner

- **Owner, decisions 1–3** (list below). Decision 1 before Lane 1's migration; 2 before Lane 3;
  3 before Lanes 4 and 6 — none blocks Lane 1.
- **Backend ↔ frontend, before the contract commits**: one agreed field name each for the per-row
  no-number count and the per-response left-out count; and the cookie's `SameSite` (backend is the
  setter; Strict and Lax both carry on same-origin `fetch`). A hand-off detail, not directional.
- **Database ↔ backend**: the candidate span read's exact signature (one method or a by-item
  narrowing plus the span) — settle in round 2, constrained to no name-key matching in SQL.
- **The ownership-map gap** on who regenerates `schema.d.ts`: I ruled the backend lane does it
  mechanically; the owner should bless the rule in the overlay (friction names it).

## The owner decisions, as they now stand (one message)

1. **Key type (#10).** Leaning UUIDv7, uniform. Settle before the migration (rewrites every FK
   after).
2. **Sign-in scheme.** Leaning a stateless signed HTTP-only cookie (no table; revoke-all by
   rotating the secret). Stored revocable sessions instead add a separate `0003_auth_session` and
   do not block Lane 1.
3. **`docs/02` §8 imports.** Leaning: import everything and filter in totals; split YouTube Music
   by `header`; strip `ip_addr`, keep `conn_country`; one configured zone; a null item (not a
   placeholder) — which adds the immutable `event.service` column, and leaves private-session and
   YouTube-Music-split totals *unfiltered* until a later migration promotes `incognito_mode` and
   `header`.
4. **Owner inputs** (verification only): #15 export, #16 Takeout, #12 Last.fm, #13 Spotify app,
   #11 spike.
5. **Run the #11 spike early** — it unblocks the YouTube daily-capture lane either way.
