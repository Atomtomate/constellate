Reviewed at beb11317c061

**Verdict:** Well placed across the layers. `domain/` imports only the standard library and
itself, `services/sources.py` only `domain/draft.py`, and `python scripts/check_layering.py` is
clean (26 modules, exit 0). Three placements inside them are wrong: the item's service is held by
the record instead of its source, the stream vocabulary by precedence instead of a module of its
own, and the id type is reached past its alias.

### 1. The item's service is held by the record's hint, not by the source that owns it
- **`api/src/constellate/domain/draft.py:57`**: `ItemHint.service` has each adapter state, per
  record, the service its source already declares, so an item's service and its event's come from
  two holders that nothing ties together.
- **The crossing**: Lane 2b takes the event's service from the adapter (`SourceAdapter.service`,
  `services/sources.py:29`, from which the source row is get-or-created). A creator's service comes
  from the same place, since `CreatorHint` (`draft.py:39`) carries none. An item's comes from
  `item_hint.service`. One draft gives three answers to "which service": two ask the source and
  one asks the record.
- **The rule**: `docs/02-domain-model.md` §1 says `service` "is set when the event is created,
  from the draft's source", and "its item, when it has one, is of that service too".
  `pr-direction-review` reaches this field from the promise. This finding is about placement.
- **The fix**: drop `ItemHint.service` and have the ingestion service give the item, its creators
  and the event the batch's one source service, so a mismatch cannot be built. This removes a
  field, which every adapter in Lanes 4a-4e would otherwise copy.

### 2. Matching takes the stream vocabulary from precedence and spells it again as literals
- **`api/src/constellate/domain/matching.py:18`**: `Play.stream` (`:89`) resolves through
  `precedence.stream_of`, so the pairing rules depend on the precedence module for a fact it only
  happens to hold.
- **The crossing**: `from constellate.domain.precedence import stream_of` resolves to `STREAM_OF`
  (`precedence.py:17-24`). Its comment justifies it by matching's rule ("matching never pairs a
  stream with itself"), and a pairing input with an unknown source raises "no place in the
  precedence orders". `MatchWindows.between` (`matching.py:59-67`) then spells `"google-history"`
  and the other streams again as bare strings, so a renamed stream turns that pair's window to None.
- **The rule**: nothing is written inside `domain/`. On its own terms the stream is ADR-0003's
  pairing unit ("Takeout and Portability counting as one stream", `docs/02-domain-model.md` §2),
  and both rule sets read it. It belongs to neither; while one holds it, the other moves with it.
- **The fix**: a `domain/streams.py` holding a `Stream` `StrEnum` and `stream_of`, imported by
  both modules, with `between` and the three orders naming members instead of strings. This adds
  a module.

### 3. Precedence reaches past `EntityId` to the concrete `uuid` type
- **`api/src/constellate/domain/precedence.py:8`**: `import uuid`, `o.item_id.int` (`:103`) and
  `uuid.UUID(int=...)` (`:105`) rebuild the type that `EntityId` aliases, so the alias no longer
  hides it.
- **The crossing**: `ObservationFacts.item_id: EntityId` resolves to `vocab.py:13`'s
  `type EntityId = uuid.UUID`. `resolve` breaks the tie on the id's integer and builds a UUID back
  from it, which fails for any other key type.
- **The rule**: `vocab.py:11-12` says "one alias, so changing it is one line", and the backend plan
  (`docs/reviews/m1-plan/impl-backend-plan.md`, 2b): "decision 1 bigint changes `EntityId` only".
- **The fix**: take the minimum over `(rank, o.item_id)` and return that id. A UUID already orders
  by its integer, so the import goes and the code gets smaller.

**Follow-ups**

- `api/src/constellate/models/` (Lane 1, not yet written): size `item.title`, `creator.name` and
  `observation.record_key` from `domain/draft.py:17-22`'s `MAX_*`. `models/` importing `domain/` is
  the permitted direction. Writing 500, 300 and 512 again would leave two holders, and nothing
  would tie them to what `draft.py` calls "the column's width".

**What carried it**

Tracing `SourceAdapter.service` out of `services/sources.py:29` into `draft.py`. Reading
`CreatorHint` next to `ItemHint` showed that a creator's service has no holder in the draft, which
is what shows the item's service is held in the wrong place.
