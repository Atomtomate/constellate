Reviewed at beb11317c061

**Verdict:** Mostly yes. ADR-0003's orders, in-order pairing and `docs/02` §2's windows hold, and
nothing later or parked came in. But three shapes from the plan of 2026-10-11 clash with what came
after: two with the decisions of 2026-11-03, one with a drift guard both plans gave this lane.

### 1. `ItemHint.service` restates the service the ADR's revision takes from the source
- **What** — The draft gives an item's service apart from its source's, so one draft can put an
  item of one service on an event of another, which ADR-0003's revision argues cannot happen.
- **Where** — `api/src/constellate/domain/draft.py:57`, beside `services/sources.py:29-30`;
  against `docs/adr/0003-the-ingestion-seam.md:151-157`, `docs/02-domain-model.md:94-96`,
  `:221-223`; `docs/reviews/m1-plan/impl-backend-plan.md:37`, written before that revision.
- **Why it matters** — The revision says `event.service` is safe unresolved because nothing on an
  event can be of another service. With two fields that holds only while every adapter keeps them
  equal by hand, and nothing checks when a per-service total and the item's service disagree.
- **Suggested resolution** — Code: drop `ItemHint.service`. Lane 2b gives the item and its
  creators the source's service, the value it gives the event, so `docs/02:95` holds by
  construction. Then a clause in step 2 of `docs/02` §2 says so.

### 2. "Counts the `ValueError` as rejected" is a drop at import that §8 does not name
- **What** — A record that fails validation is counted and never stored. The owner's later "import
  every row" admits one dropped class, Google Ads rows, and says a dropped row never returns.
- **Where** — `api/src/constellate/domain/draft.py:3-6`, `:101-117`; against
  `docs/02-domain-model.md:691-696`, `:187-188` (a file's hash is checked before parsing);
  `docs/adr/0003-the-ingestion-seam.md:46`, `:97`; `impl-backend-plan.md:41`, `:57`.
- **Why it matters** — The checks catch what no column could hold, in practice a parser bug, which
  ADR-0003 expects. The run still ends `ok`, so a fixed parser cannot re-read the file. Only
  undoing the whole run brings the rows back, though the ADR promises "a recompute over stored
  observations".
- **Suggested resolution** — Code in 2b: the hash check skips no run that rejected a record, with
  a `test_ingest.py` case that re-reads a re-offered file. Then name rejected rows in `docs/02` §8
  and in the ingest run's counts at `:185`.

### 3. The vocabularies' drift guard is claimed but not built, and both plans gave it to Lane 2
- **What** — `vocab.py` says a test pushes every member through the ORM. The only test compares
  them with a hand copy of `docs/02` §7, which issue #17 deletes.
- **Where** — `api/src/constellate/domain/vocab.py:3-5`; `api/tests/test_domain_draft.py:41-45`;
  against `docs/reviews/m1-plan/impl-director.md:208-210`, `impl-backend-plan.md:34-35`,
  `impl-database-plan.md:56-57`.
- **Why it matters** — Lane 1 expects Lane 2 to have it, and Lane 2 shipped before there was
  anything to guard. Neither PR owns it, so `models/`' CHECK literals can drift unseen while the
  docstring says they cannot. The PR body's list of deviations leaves it out.
- **Suggested resolution** — Code: Lane 1 builds its CHECK lists from `vocab`'s members, which
  `models/` may import (`docs/03-architecture.md:97`), leaving one source. Until then, the
  round-trip test goes in Lane 1's brief and `vocab.py:3-5` says what exists today.

**Decisions**
- `SourceAdapter` with `key`, `service`, `fetch(cursor) -> Iterator[Batch]`; the draft limits
  (UTC, int32 ms, 512-character key, 64 KB raw, cut titles): recorded (director C1; backend plan).
- A record that fails validation is rejected and counted, and the run goes on: recorded in the
  plan, never squared with `docs/02` §8 (2).
- `ItemHint` carries a service beside the source's: the plan's, silent against ADR-0003 (1).
- `item_ref` and `item_hint` come together or not at all: follows from `docs/02` §2 step 2.
- One Google stream, the precedence orders, the item rank, ties by value, an unranked source
  raising: recorded (ADR-0003; `docs/02` §2; PR body).
- Δ 30 s and Google–extension 5 min as guesses; the name fallback by `name_key` on album artist:
  recorded (PR body; ADR-0003 amendment 3; director C2).
- `Play` and `Slot` as pairing inputs; `CatalogueAdapter` waits for Lane 5: recorded (PR body).
- `EntityId` for the owner's UUIDv7: recorded. The vocabularies pinned to `docs/02` §7: silent (3).

**Follow-ups**
- `api/src/constellate/models/base.py:22-25` still leaves the key type to the owner, and
  `ids.py:13` places it there; both were stale before this branch. `vocab.py:11-12`'s "one line"
  is untrue against `precedence.py`'s `.int` arithmetic (tech's).
- `docs/01-data-sources-spotify.md:353` and `docs/01-data-sources-youtube.md:292` still say
  "nearest", which ADR-0003's amendment 2 overruled; stale before this branch.

**What carried it**
- Checking `impl-backend-plan.md`'s date (2026-10-11) against ADR-0003's revision and `docs/02` §8
  (2026-11-03) while tracing each 2a type back to its plan line (findings 1 and 2).
