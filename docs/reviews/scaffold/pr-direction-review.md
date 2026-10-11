Reviewed at dd6ae24e3f66

**Verdict:** Mostly yes. The fold settles the first wave's six findings, two of them better than
asked (the leaf, sign-in's code). But its new account of what the source seam waits on moves the
draft event into a migration, and the key-type question sits where the record will not keep it.

### 1. The draft event is re-homed in a migration
- **What** — Rewording what each module waits on (first wave, 3), the fold says the first
  migration "defines" the draft event an adapter produces; `docs/03` puts that type in `domain/`,
  and `docs/02` §2 specifies it with no table behind it.
- **Where** — `api/src/constellate/sources/__init__.py:8-9`, `services/sources.py:18-19`,
  `poll.py:8`, echoing the unchanged `domain/__init__.py:8-9` ("the tables they map to");
  against `docs/03-architecture.md:84,89-91` and `docs/02-domain-model.md:185-200`.
- **Why it matters** — `docs/03` keeps `domain/` off `models/` "because the ORM is the database's
  shape and the rules are not". The first adapter's author reads these lines, which put the
  seam's type on `impl-database`'s side of the map; `sources/__init__.py` now gives it two homes.
- **Suggested resolution** — Prose: `check_layering.py` already refuses the import, and the
  sentence is what misleads. Each waits on "the draft event in `domain/`, `docs/02` §2's fields".

### 2. The key-type question is not where the code says it is decided
- **What** — `Owned` keeps UUIDv7 until the owner decides "in `docs/02` §7–§8". But §8's Open list
  never names the question and §7 still sketches `bigint` keys. So it lives only in PR #9's
  "Needs the owner" and two docstrings, and `ids.py` says it "is decided" there.
- **Where** — `api/src/constellate/ids.py:13-14`, `api/src/constellate/models/base.py:22-25`;
  against `docs/02-domain-model.md:515,609-652` and the root `CLAUDE.md` ("Where the plan is
  silent, that is a question for `docs/08-open-questions.md`").
- **Why it matters** — If the PR merges unanswered, the record lists nothing open about keys. The
  first migration's planner then finds `bigint` in `docs/02` and UUIDv7 in the base class it
  must use, and the leaning is in a closed PR body.
- **Suggested resolution** — Prose, since no check reads whether a question is open: a §8 Open
  bullet with both keys, the deadline and the leaning, and `ids.py` saying "the owner's to decide".

### 3. Sign-in's fold stops one sentence short
- **What** — The challenge and the cookie are gone, but `main.tsx` now names "the 401-redirect
  rule" and "M1's sign-in screen" as what arrives. The plan still has the sibling's session
  plumbing "ported only with sign-in (M1)". A screen plus a 401 redirect is `ADR-0014`'s shape.
- **Where** — `web/src/main.tsx:10-12`, `web/README.md:8-9`,
  `docs/reviews/scaffold/impl-director.md:141-143`; against `docs/03-architecture.md:223` and
  `docs/adr/0002-the-stack.md:234-235` ("a starting point, not a precedent").
- **Why it matters** — It is smaller than the first wave's finding 1, since no code takes it. But
  M1's sign-in planner reads these lines as what is coming, while the record leaves the scheme open.
- **Suggested resolution** — Prose: "sign-in, and what it adds here, arrive with M1's decision".
  The plan should say the sibling's plumbing is not ported.

**Decisions** (the fold's)
- Contextvar in the leaf `request_context.py`, no third module kind: recorded (`docs/03`, PR body).
- Leaves are whatever anything imports, entry points included: recorded (`check_layering.py`).
- No 401 challenge and no web credential, both M1's: recorded (`docs/03` 401 row, PR body).
- `HTTPException` headers pass through; an unmapped `ServiceError` is a 500: recorded (`errors.py`).
- `servers` set in the app from `root_path`'s constant: recorded (`docs/03`, One origin).
- UUIDv7 kept pending the owner: recorded in the PR body and docstrings only (finding 2).
- Decision 4's sub-calls "go the same way": recorded (`impl-director.md`); the handoff names none.
- The draft event type is a migration's: silent (finding 1).
- Sign-in as a screen with a 401 redirect: silent (finding 3).
- Shell routes only, no pure section until the first one: recorded (`web/CLAUDE.md`).
- Ruff on generated revisions, engine from settings: recorded (`alembic.ini`, `env.py`).
- Docstrings linted in `api/`, held by review in `web/`; overlay toolchain points: recorded.

**Follow-ups**
- `docs/03-architecture.md:218-221` lists Q-C and Q-D under "Not decided here".
  `claude/consolidate-m0` answers both without touching `docs/03`, so the promised rebase fixes it.
- `docs/reviews/scaffold/impl-director.md:144-147` says this PR edits only `docs/03` Conventions
  and the markers. It also edits root `CLAUDE.md`, the overlay, and `docs/03`'s layers and 401 row.

**What carried it**
- `docs/03`'s layer table ("the draft event among them"), read beside the fold's rewritten
  waits-on lines, when `sources/__init__.py` named two homes for one type.
