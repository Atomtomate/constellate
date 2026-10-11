# `src/constellate/` — the layers

`docs/03-architecture.md` ("Layers inside the API package") names the six directories, the one
direction dependencies run in, and the rules for `domain/`, for `sources/` and for the modules
outside the layers; this is the detail it expands, and repeats none of it. Read the root
`CLAUDE.md` and `api/CLAUDE.md` first.

**No sanctioned skips.** There is no list here of routers allowed to reach `repos/` directly:
the first router with genuinely no logic to put in a service brings the list back together with
the rule that sanctions it, rather than an empty table waiting for one. `models/` may build a
table expression — `text()` in a `server_default` — but never runs a query.

**`__init__.py` counts as a leaf**, since no import names it but every import runs it: a
re-export added there would have `models/` load `services/` at import time. The request id's
contextvar lives in the leaf `request_context.py` for the rule's other half, that a leaf
imports none of the four: `logging_config.py`'s filter reads what `api/request_id.py`'s
middleware sets, and a value both reach lives below both rather than the filter importing
`api/`.

**The seam is `services/sources.py`'s `SourceAdapter`, a `Protocol`.** An adapter has the right
members and never subclasses it; a leaf imports no module of `sources/` any more than a layer
does, and a helper only an adapter imports is a leaf too, held to a leaf's rule.

**`poll.py` is the poller** `docs/03` describes, `python -m constellate.poll`. Today it logs
that no source is configured and exits 0, so the scheduled task can be wired before a source
exists. Once it has adapters to run, it will skip an unconfigured source with a log line rather
than abort the run — the design its docstring carries, not behaviour it has yet.

**The readiness probe's `select 1`** (`docs/03`, Health) is sanctioned in `check_layering.py` by
file and statement together, so a second statement in `api/routers/health.py`, or that one
anywhere else, is a violation like any other.

**Only `logging_config.py` configures logging** — a handler, a level, `basicConfig`,
`dictConfig`, `.handlers`, `.propagate` — and `check_layering.py` holds every other module to
it. An entry point calls `configure_logging()` once before it logs; `main.py` does at import.
Everything else takes `logging.getLogger(__name__)` and installs nothing — except a module run
as a command, which names its logger (`constellate.poll`): under `python -m`, `__name__` is
`__main__`, no child of `constellate`, and the handler would never see its records. The
formatter writes one JSON object per record with a fixed key set and silently drops `extra=`
fields, which is what keeps a careless call site from writing a token into a structured log; a
message or an exception's text names the row's id, never a credential, a hash or an email.

**Writes commit where they complete**, never in `db.get_session`: FastAPI tears a yield
dependency down after the response is sent, so a commit there cannot affect the status code — a
failure would return 201 for an event that was never stored. The test session fixture does not
commit either, for the same reason (`api/tests/CLAUDE.md`).

## What belongs where

| Question | Layer |
|----------|-------|
| What columns does an event have? | `models/` |
| How do I fetch this efficiently? | `repos/` |
| Is this draft event complete? Which local day does an instant fall in? | `domain/` |
| What happens when a poll lands, or an export is imported? | `services/` |
| How does what Spotify or Takeout returns become a draft event? | `sources/` |
| What status code, what JSON shape? | `api/` |

If a rule is needed by two queries, it becomes a shared helper in `repos/`; a rule about the
log rather than the database belongs in `domain/` or `services/`.
