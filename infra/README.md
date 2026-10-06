# `infra/` — what runs the stack

What is here now is the development database's bootstrap, and nothing else:

- `postgres/init-constellate.sql` — creates the `constellate` database and the role that owns
  it on the Postgres that `compose.yaml` at the repository root describes. That file says how
  one server on port 5432 is shared with the sibling project; this one says how the database
  gets onto it.

The serving rig is Q-E's (`docs/08-open-questions.md`): the stack script, the Caddyfile, the
scheduled task's definition and its installer arrive with the PR that answers it, and ADR-0002's
Consequences say they belong here when they do. Until then the `infra` gate area
(`scripts/gates.py`, `infra.yml`) checks only `compose.yaml`; the Caddyfile-validate and
stack-script checks the ADR's appendix names arrive with that same PR. No specialist owns this
directory; it is edited from the session (`.claude/agents.local.md`).

## Creating the database

On an empty volume nothing is needed: `docker compose up -d` from the repository root starts
Postgres, and the image's entrypoint runs the script once, at first start. On a server that
already holds data — the sibling's `boardgame-tracker-db-1` on the dev PC, or this one after
its first start — run the same file by hand, once, as that container's superuser (its
`POSTGRES_USER`: `bgtracker` in the sibling's, `postgres` here):

```sh
docker exec -i boardgame-tracker-db-1 psql -v ON_ERROR_STOP=1 -U bgtracker -d postgres \
  < infra/postgres/init-constellate.sql
```

PowerShell has no `<`: pipe the file in instead, `Get-Content -Raw <file> | docker exec -i …`.
In this project's own container the file is already mounted, so no redirection is needed:
`docker compose exec -T db psql -v ON_ERROR_STOP=1 -U postgres -d postgres -f
/docker-entrypoint-initdb.d/10-constellate.sql`. The script is idempotent, so running it against
a server that already has both is harmless. What it fixes — role `constellate`, password
`constellate`, database `constellate`, on `127.0.0.1:5432` — is what `config.py`'s default URL
names, so a fresh checkout reaches the database with no setting set.
