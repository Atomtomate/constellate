Reviewed at d1f7201cd1eb

**Verdict:** The code is about the right size; the prose is a little heavy. The Python and the
TypeScript are close to the least that does the work. The extra weight is rationales told at three
to six sites each, one pair of parallel maps in the error envelope, and a ported test helper and
import exemption with nothing to apply to yet. The owner's decision 4 accepted the empty layers,
`ids.py`, `Owned` and `queryKeys.ts`, so none of them is counted here.

### 1. The CI and toolchain rationales are retold beside the files that own them
- **What** — `api/alembic/CLAUDE.md:44-52` owns the round trip, the drift check and why both are
  CI's alone. `.github/workflows/api.yml:7-11`, `:76-77`, `:84-86` and `scripts/gates.py:20-24`,
  `:205-208` retell it. `api/tests/CLAUDE.md:7-12` owns why the suite runs on both backends, and
  `api.yml:114-116` and `api/tests/conftest.py:3-5` retell it. `web/README.md:36-51` retells
  `web/CLAUDE.md`'s generated client, and `:59-64` retells the README's own `:20-24`. The overlay's
  `:189-196` copies `api/CLAUDE.md`'s Running it, against its own preamble ("points at it").
- **Why it recurs** — each new area copies its workflow header from these (ADR-0002 names
  `extension.yml` and Q-E's `infra` steps). Each CI-only step is explained once per file that
  names it, and each directory with both a README and a `CLAUDE.md` copies `web/`'s split.
- **The smaller version** — the why stays with its owner. Every other site keeps a one-line
  pointer, as `web/README.md:53-57` already does for the layer rule. This stays prose, because
  no count can tell a retelling from a pointer.
- **Net effect** — about −40 lines. A changed reason or command is one edit, not three to five.

### 2. The error envelope keeps two maps keyed by the same classes, plus a fallback for a miss
- **What** — `api/src/constellate/api/errors.py:82-95` holds `_STATUS` and `_CODE`, both keyed
  by the five service errors. `:148-153` handles a class missing from both maps, and
  `api/tests/test_errors.py:11-40` keeps both maps complete with two tests. Without the fallback,
  the `KeyError` leaves through `_unhandled`. A probe against the real app showed the same wire
  result: 500, `internal_error`, the fixed message and `X-Request-ID`.
- **Why it recurs** — every product code (`rule_violated` is next, per `docs/03`'s Conventions)
  needs a row in each map and in each test. `docs/03` already says the mapping is "in one place".
- **The smaller version** — `_WIRE: dict[type[ServiceError], tuple[int, ErrorCode]]`, with rows
  like `NotFound: (404, "not_found")`. The handler becomes `status, code = _WIRE[type(exc)]` and
  one `_render`, and one completeness test covers `_WIRE`. `_CODE_BY_STATUS` stays separate: it
  maps Starlette's statuses, and two codes will share 422.
- **Net effect** — about −20 lines. A new code is one row, and the handler loses a path whose
  only purpose was to be unreachable.

### 3. A ported walk helper, and an import exemption that applies to no file
- **What** — `web/src/test/walkFiles.ts` (17 lines, one caller) re-implements
  `readdirSync(SRC, { recursive: true })`, which the required Node (^22.18) already has: the same
  filter over it yields the same nine files. It is also the only file in `src/test/`, the one
  section `PURE_SECTIONS` names. So the `import type` exemption (`web/src/layering.test.ts:56-62`,
  `:97-104`) and its five cases (`:147-196`) guard imports no file makes.
- **Why it recurs** — it does not. It is a verbatim port (`impl-frontend-plan.md:91-92`).
- **The smaller version** — inline the one call. With `src/test/` gone, drop its row,
  `PURE_SECTIONS`, the exemption and its cases, and `web/CLAUDE.md:25-27` and `:38`'s
  pure-section clauses. The first `lib/` brings them back. The plan already deferred the sibling's
  `web/scripts/` rules the same way (`:85-89`), as `api/src/constellate/CLAUDE.md:8` does with
  sanctioned skips. Removing an allowance only makes the test stricter.
- **Net effect** — about −75 lines and one source directory, and rule 3 loses its special case.

### 4. Two modules tell their own rationale two to four times
- **What** — `docs/03-architecture.md:201-203` names `errors.py:173-176` as where the 500
  path's header is explained. `api/src/constellate/api/request_id.py` retells it at `:3-5`,
  `:27-28`, `:52-54` and `:82-85`, and says "referenced, not inlined" at both `:31-33` and `:92`.
  In `services/sources.py`, "neither layer imports the other" appears at `:3-6` and again at
  `:8-11`. "No members until `docs/02` and Q-D" appears at `:13-16` and again at `:29-31`, and
  `api/src/constellate/CLAUDE.md:24-29` tells both a third time.
- **Why it recurs** — when Q-D's answer adds the protocol's method, three "not yet" sentences have
  to change in one PR, and a missed one says the seam is empty when it is not. The backend lane
  writes every new module in this style.
- **The smaller version** — state each fact once per file, at the line it explains: the 500 path
  in `_unhandled` alone, and one module paragraph in `sources.py`, with the class docstring saying
  only what a member must satisfy.
- **Net effect** — about −15 lines. The next edit to either seam has one sentence to change.

**What carried it** — the definition's "read the argued-for parts first", applied to
`impl-director.md`'s decision 4 and the frontend plan beside it. Decision 4 ruled out four findings
that would have been naive. The plan's deferral of `web/scripts/` supplied finding 3's argument.
