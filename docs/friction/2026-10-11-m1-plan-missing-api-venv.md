# The M1 plan brief named an `api/.venv` the worktree did not have
**Agent:** impl-director
**Summary:** The brief promised a ready API venv at `api/.venv`; it was absent, so `impl-database` built a throwaway venv to probe SQLAlchemy and every M1 lane that runs the API must make one first.
**Retro:** Unprocessed

## What I was doing

The plan-before-code round for M1, in the worktree `C:\wt\constellate-m1` (branch
`claude/m1-plan`), checking the three specialists' plans against the cut in
`docs/reviews/m1-plan/impl-director.md`.

## What happened

Both my brief and the specialists' said: "The API venv is `C:\wt\constellate-m1\api\.venv`
(interpreter `…\api\.venv\Scripts\python.exe`) if a command helps you read the scaffold."
`ls -d api/.venv` from the worktree returns nothing — there is no `api/.venv`. The
`impl-database` plan records the same: "The worktree has no `api/.venv`, so I probed the
mechanisms in a scratch venv (SQLAlchemy 2.1.4, SQLite 3.50)", and its friction field notes no
note was written.

## What it cost

`impl-database` built a throwaway venv in the session scratchpad to probe the `TypeDecorator`,
JSON/JSONB and Alembic mechanisms its plan rests on, and flagged that its Postgres-dependent
claims stay hand-run because it could not run the real toolchain. Lower confidence in those
claims, and a step every M1 backend/database lane will repeat: a worktree made by `git worktree
add` carries no venv, so each lane must run `api/CLAUDE.md`'s "Running it" before any
`pytest`/`ruff`/`alembic`. No wrong decision followed, but the brief's "if a command helps you
read the scaffold" was not actually available.

## What would remove it

Either the lane-launching step creates `api/.venv` in a new worktree before briefing an agent
that it is there (one `python -m venv` plus the install `api/CLAUDE.md` names), or the brief
template stops asserting the venv exists and says "make it first, per `api/CLAUDE.md`". The
brief wording that over-promised is the launching session's to fix, not a repository file.
