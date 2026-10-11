Reviewed at a7cfbe4
(the plan round; no code)

**Verdict:** The plan's dependency directions are right. Imports point the way `docs/03` draws
them, adapters stay behind `SourceAdapter`, importers and the poller are entry points, and the
SQL line holds. `python scripts/check_layering.py` is clean on the scaffold (22 modules). Four
placements are wrong: a name-matching rule left in SQL, the zone served from the session
endpoint, the local day with no owner, and a read use case put in the seam's module.

### 1. Name-key equality for item resolution stays in SQL, beside `domain/`'s own
- **`impl-database-plan.md:73`** (`find_items_by_name … # casefold =`), which
  `impl-backend-plan.md:60` and `:71` call in step 3 for a Last.fm name ref: "same title and
  album artist" gets one answer in `repos/` and another in `domain/`.
- **The crossing** — `services/ingest.py` asks `repos/items.py` whether a title and a creator name
  match, and gets a SQL case-fold. `domain/matching.py`'s `name_key` (NFKC, casefold, strip;
  `impl-backend-plan.md:47`) answers the same question for event matching and builds the
  `spotify:artist-name` refs. SQLite's `lower()` folds ASCII only, which makes a third answer.
- **The rule** — `impl-director.md:115-120` [C1]: name-key equality is a tunable rule, and "no
  name-key matching is SQL"; `api/src/constellate/CLAUDE.md`: "a rule about the log … belongs in
  `domain/` or `services/`". C1 removed `find_candidates_by_name` and left its twin.
- **The fix** — the repo narrows by a key `domain/` already computed (items linked as album artist
  to the creator whose `spotify:artist-name` ref is `name_key(artist)`), and a `domain/` function
  picks the one whose `name_key(title)` matches. This adds a function; decisions 1–3 leave it as is.

### 2. The bucketing zone reaches the client through the session endpoint
- **`impl-director.md:175-177`** (Lane 3: "`/me` carries `time_zone`"), and
  `impl-frontend-plan.md:123`: the client gets the zone that shaped `/events` and `/totals` from
  the sign-in router, because it already calls `/me`.
- **The crossing** — `api/routers/auth.py`'s `MeResponse` reads `config.timezone`, a setting the
  backend adds in Lane 6 (`impl-backend-plan.md:140`), so Lane 3 has to ship it first.
  `/totals/periods` carries the same fact again as `timezone` (`impl-director.md:248`).
- **The rule** — none is written. On its own terms the zone is decision 3's and belongs to the read
  model, not the session. The "if otherwise" lines show this: auth at Caddy deletes `/me` and the
  zone "needs a new home" (`impl-frontend-plan.md:160`), and a per-event zone moves it onto events
  (`:162`). Its home moves with a decision that has nothing to do with the zone.
- **The fix** — carry the zone on the read responses it shaped (`EventPage` beside
  `/totals/periods`, one spelling), or give it a read of its own if `/sources` needs it too.
  `/me` stays the session's. This adds a field or an endpoint.

### 3. The local day has no owner: buckets in SQL, `local_date` and date filters unplaced
- **`impl-director.md:239-243`** [C1] and `:256`: the plan says the timeline's headings "match the
  totals buckets", but it places only the buckets, as `date_trunc(… at time zone :tz)` in
  `repos/` (`impl-database-plan.md:150`, `impl-backend-plan.md:163`).
- **The crossing** — `local_date` and the local-date bounds go to whoever builds them.
  `api/src/constellate/CLAUDE.md:54` gives "which local day does an instant fall in" to
  `domain/`, which means Python's `zoneinfo` over the `tzdata` wheel (`impl-backend-plan.md:140`),
  while the buckets read Postgres's zone data. The headings match only while the two agree.
- **The rule** — ADR-0002 (The store) puts totals by local day in the database;
  `api/src/constellate/CLAUDE.md`: "If a rule is needed by two queries, it becomes a shared helper
  in `repos/`".
- **The fix** — one `repos/` helper for the local-day expression, used by `totals_by_period`,
  `list_timeline`'s `local_date` and every local-date filter, with the service passing in the
  zone. This adds a helper. Under a per-event zone (decision 3) its argument changes, not its owner.

### 4. The `/sources` read use case lands in the seam's module
- **`impl-backend-plan.md:139-140`** (Lane 6: `services/{events,totals,sources}.py`) and `:51`
  (2a: `SourceAdapter`'s members in `services/sources.py`): one module becomes both the adapter
  seam and a status read.
- **The crossing** — `services/sources.py` would import `repos/` for the latest runs per source.
  The interface the adapters satisfy, which `scripts/check_layering.py`'s `sources/` rule names,
  then has a query dependency, and a reader who opens the seam finds a read use case there.
- **The rule** — `docs/03`: "`sources/` is reached only through an interface `services/`
  declares"; `api/src/constellate/CLAUDE.md`: "The seam is `services/sources.py`'s
  `SourceAdapter`". That module's imports should be the seam's and nothing else.
- **The fix** — name the read `services/source_status.py` and keep `services/sources.py` for the
  protocols. Lane 5's `CatalogueAdapter`, which has no module yet, goes there too. No code added.

**Follow-ups**

- `api/src/constellate/CLAUDE.md:54` gives the local day to `domain/`, and ADR-0002 (The store)
  gives totals by local day to the database: for `pr-direction-review` and the session.
- Lane 4d's Spotify connect (OAuth) and disconnect have no door yet. As commands they add nothing
  to the contract; as endpoints they would be the first write path outside Lanes 3 and 6.

**Friction**

Not written: the brief confines writes to `docs/reviews/m1-plan/`. The brief's first line
("Reviewed at a7cfbe4 (the plan round; no code)") fails `check_docs.py`, whose `REVIEWED_AT` in
`scripts/reviews.py` accepts a bare sha only. So the parenthetical is on line 2.

**What carried it**

Following `find_items_by_name` from the database plan's signatures (`impl-database-plan.md:73`)
into what the backend needs from Lane 1 (`impl-backend-plan.md:71`), against C1 at
`impl-director.md:120`. C1 had applied its rule to one of the two lookups that do this matching.
