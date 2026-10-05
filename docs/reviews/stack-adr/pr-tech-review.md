Reviewed at b3aeb20eb0c2

**Verdict:** Three findings. The one that matters: this PR names a layering check to enforce
`docs/03`'s new `sources/` rules. Ported the way the ADR describes, with its constants changed,
that check passes both of the violations those rules forbid. The other two are smaller. A rule
said to give every new module an owner gives none to an entry point. And the "survives a reboot"
claim behind reason 4 holds only with a task principal the ADR does not name.

### 1. A constants-only port of `check_layering.py` enforces neither of `docs/03`'s `sources/` rules
- **`docs/03-architecture.md:97`** says the port "enforces this". `docs/adr/0002-the-stack.md:70-71`
  says it "ports with its constants changed", and `:192-193` says "with the check that holds it".
  The sibling's check has no `sources/` rule. It places each unit outside
  `api/ services/ repos/ models/ domain/` by what imports it (`leaf_importers`).
- **Failure:** I ran the sibling's check against a fake package, with `PACKAGE = "constellate"`
  and `SANCTIONED_SKIPS` emptied. (a) `sources/spotify.py` imports `repos/` and `models/`, and no
  service imports it, which is the interface shape `docs/03:88-90` prescribes. The check classes
  `sources/` as an entry point and says "consistent". (b) `services/ingest.py` imports the adapter
  directly. The check still says "consistent", because it never flags an import of a unit outside
  the layers. `docs/03:88-91` forbids both. `.claude/agents.local.md:80-82` tells
  `pr-architecture-review` to trust this check.
- **Confidence:** certain
- **Fix:** the port places `sources/` as its own unit: it imports only `domain/` and leaves, and
  no layer imports it. It carries tests in `scripts/tests/` for (a) and (b), both of which pass on
  a constants-only port. In this PR, write that where the port is briefed (`docs/03:97` and the
  handoff's `:46-47`), and drop "constants changed". Also decide whether `sources/` may import
  `services/` to subclass the interface. `docs/03` is silent on it, and the port has to know.

### 2. The rule said to give every new module an owner gives none to an entry point
- **`.claude/agents.local.md:46-49`**: a module the rows do not name "belongs to the agent whose
  layer imports it … so the next one added does not need this table edited to have an owner."
- **Failure:** `docs/03-architecture.md:54-55` makes "an importer run as a command" an entry point
  in the package, and `:95` says "Nothing imports an entry point." Take the first Spotify-export
  importer, `python -m constellate.import_spotify`. It is M1's first ingestion work under
  `docs/07-roadmap.md:90-92` (backfill before live capture). No row names it (`:43` names
  `main.py` and `poll.py`), and no importer exists for the rule to assign it by. So
  `impl-director` has no owner to cut it to. The sibling avoids the gap by listing each of its
  entry points (`seed.py`, `devsession.py`, `demo_seed.py`) in `impl-backend`'s row.
  `pr-direction-review`'s follow-up is on the same lines but covers different files
  (`pyproject.toml`, `export_openapi.py`).
- **Confidence:** certain
- **Fix:** add one clause to the rule: a module nothing in the package imports is
  `impl-backend`'s. This has to be prose, because the director needs the owner before the file
  exists and a check could only report after.

### 3. The OS-scheduled task survives a reboot only with a principal the ADR does not name
- **`docs/adr/0002-the-stack.md:140-141`** says "It survives a reboot and a crash with nothing of
  ours supervising it". Reason 4 (`:200-202`) rests on that claim, as does the case against the
  worker (`:135-138`, `:262-263`). `:142-145` names `StartWhenAvailable` and `WakeToRun` as "the
  two a sleeping PC wants".
- **Failure:** a task registered the default way has `LogonType` `InteractiveToken` and fires only
  while the owner is signed in. That covers `Register-ScheduledTask` without `-Principal`,
  `schtasks /create` without `/RU` and `/RP`, and the dialog's default "Run only when user is
  logged on". After a power cut or a crash reboot, Postgres starts as a service, but no poll runs
  until somebody signs in. That is the same behaviour as the "OS task at logon" worker the ADR
  rejects at `:137-138`. The handoff tells whoever writes the task to verify two setting names,
  not this one.
- **Confidence:** likely. Whether it happens depends on how the installer registers the task.
- **Fix:** name the principal (`S4U`, "whether the user is logged on or not") beside the two
  settings. When the definition lands under `infra/`, the `infra` area's tests should assert all
  three settings, so a test fails if one is dropped.

**What carried it**
- The definition's rule that a bug is a mismatch with code that did not change. It came into play
  at the ADR's "ports with its constants changed": I read the sibling's `leaf_importers` and then
  ran a constants-only port against a fake package. That turned a suspicion into finding 1.
