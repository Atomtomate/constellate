# `alembic/` — migrations

Small directory, dangerous rules. Read the root `CLAUDE.md` and `api/CLAUDE.md` first.

## The rule everything else follows from

**A migration must be safe against a database that already holds years of events.** The
project is a durable log of what the owner listened to and watched; once the first poll has
landed, `drop table` is not available, and a destructive column change has to decide what it
does with the rows that do not fit. Refuse and name them; do not invent data to get past it. A
migration that stops with a list a person can act on is worth more than one that guesses and
succeeds.

Right now the chain is one empty revision, `0001_scaffold`, anchoring it at a known id so the
first table migration has a `down_revision` to point at; the tables arrive with that migration,
cut from `docs/02-domain-model.md`'s schema. Mistakes are free until the first deploy, and the
habits formed now are the ones that will be in place after it.

## Writing one

```bash
alembic revision --autogenerate -m "what it does"   # from api/, with Postgres running
```

- `env.py` takes the URL from `constellate.config.settings` — `CONSTELLATE_DATABASE_URL` —
  never from `alembic.ini`, so one place knows how to reach the database; and it imports
  `constellate.models`, so a table class is visible to autogenerate only once
  `models/__init__.py` imports it.
- **Always autogenerate, then read what it produced.** It is a draft, not an answer.
  `compare_type` and `compare_server_default` are on, so a changed type or default shows up in
  it — and counts as drift in CI if it is missing from the revision.
- **Generate against Postgres**, not SQLite, so dialect-specific types render correctly.
- **Register the revision in `api/tests/test_migrations.py`**: a case and a `_COVERED` entry if
  it touches existing rows, or a `NO_ROWS` entry with the reason if it cannot.
  `test_all_revisions_are_covered_or_no_rows` fails on a revision in neither, and runs on
  SQLite too, reading the chain without a database.
- Forward-only. Never edit a revision that has been applied anywhere but your own machine.
- The CI checks below need a live database and no hook runs them, so run the three `alembic`
  commands by hand against the development Postgres before pushing a migration.

## What CI checks

`.github/workflows/api.yml`, against a Postgres service: `alembic upgrade head`, `downgrade
base`, `upgrade head` — every revision's downgrade exercised, not only its upgrade, so one that
cannot be reverted fails here and not on the day it has to be — and then `alembic revision
--autogenerate` has to produce an **empty** diff against the models. A non-empty one means
someone changed a model without writing the migration, and the two drift further with every
commit until a deploy fails. Both stay CI's alone (`scripts/gates.py` names them on the hook's
result line) because the drift check writes a revision into `versions/` to read it back, which
is not a thing to leave in a working tree when a run dies between the write and the delete.

## Not covered here

The models themselves: `../src/constellate/CLAUDE.md`.
