Reviewed at 98442d769fff

**Verdict:** The fold took the first wave's code findings whole. `_WIRE` is one table,
`walkFiles.ts` and the import-type exemption are gone, and the CI headers point to the files that
explain them. The code the fold added is close to the least that does the work. Its weight is
prose, in the shape first-wave findings 1 and 4 removed: each deferral, the leaf rule and each
fix is told at three to five sites, and the copies of one deferral already disagree.

### 1. A deferral is told at every site near it, and the seam's copies already disagree
- **What** — The seam's wait is told five times in `api/src/constellate/`: `CLAUDE.md:29-30`,
  `services/sources.py:18-19`, `sources/__init__.py:8-9`, `poll.py:8-9`, `domain/__init__.py:8-9`.
  `CLAUDE.md` says the draft event type arrives with the first adapter, the other four the first
  migration. First-wave 4 named that copy, and the fold rewrote it instead of dropping it. Sign-in
  waits at five sites (`docs/03-architecture.md:159`, `api/tests/CLAUDE.md:45`, `conftest.py:158`,
  `web/src/api/client.ts:7`, `web/src/main.tsx:10`). The key type waits at two (`ids.py:13`,
  `base.py:22`), the pure sections at three (`web/CLAUDE.md:32`, `:40`, `layering.test.ts:44`).
- **Why it recurs** — The scaffold is mostly deferrals, and Q-E's and the extension's will copy
  this. Direction's first-wave 3 had each module name its wait so that none goes stale. But five
  copies are five places to go stale, and one already has.
- **The smaller version** — One owner each: `SourceAdapter`, `domain/__init__.py`, the 401 row
  with `anon_client`, `Owned`, `web/CLAUDE.md:32-34`. `poll.py` says "none yet" without the chain,
  and the other copies go. Prose, because no count can tell a retelling from the fact it retells.
- **Net effect** — About −18 lines. Settling a deferral is one edit, and no stale copy is left.

### 2. The leaf-or-entry-point rule is told at five sites, two of them in one file
- **What** — `docs/03-architecture.md:98-102` owns the two kinds. `api/src/constellate/CLAUDE.md`
  restates them at `:13-17`, though its `:3-5` says it "repeats none of" `docs/03`. Its `:20-21`
  lists the leaves, under a heading that says they are derived, not listed.
  `scripts/check_layering.py:17-22` tells the rule although `:7` already points at
  `leaf_importers`, whose `:242-258` tells it again. `scripts/tests/test_check_layering.py:492-497`
  adds the fold's history. The fold rewrote all five.
- **Why it recurs** — `CLAUDE.md:22-24` makes the copying procedure: a change to the rule also
  updates "that script's docstrings". Each rule the check learns next is told at all those sites.
- **The smaller version** — `docs/03` states the kinds. `CLAUDE.md` keeps only its own facts: that
  `__init__.py` counts, and why `request_context.py` is a leaf. The definitions, the list and the
  sync sentence go, as does `check_layering.py:17-22`. `leaf_importers` keeps why its algorithm
  works: derived, one pass is the closure, first reacher wins. Prose, for first-wave 1's reason.
- **Net effect** — About −14 lines. The next leaf or rule changes `docs/03` and the code, and no
  third file has to keep step.

### 3. The fold explains each fix where it made it, then again nearby
- **What** — `api/src/constellate/main.py:17-21` explains `servers`, then says `docs/03` explains
  it. `api/tests/test_app_config.py:6-7` and `:25-26` tell it twice more, both times about an
  injection the exporter no longer does. `errors.py:82-83`'s KeyError fall-through is retold at
  `test_errors.py:3-4` and `:14-16`. First-wave 4 left the 500 path to `_unhandled`
  (`errors.py:158-161`), yet `request_id.py:4-6` and `test_logging.py:93-95` retell it.
- **Why it recurs** — Each fix brings a test, and each new test's docstring repeats the production
  comment: `test_migrations.py:65-69` retells `alembic/env.py:16-18` the same way.
- **The smaller version** — The mechanism stays with its code. `main.py` keeps one line and the
  pointer. A test docstring says what the test pins and no more. What the code used to do belongs
  in the commit message, which already says it.
- **Net effect** — About −12 lines. Changing a mechanism means changing one comment.

**What carried it** — The commit messages, read against the first wave's report. e87da3e's
"say each fact once" and 94e6d04's "each module names what it waits on" were the two places to
diff for regrown copies. Reading the five waits side by side showed the drift in finding 1.
