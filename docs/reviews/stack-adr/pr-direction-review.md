Reviewed at b3aeb20eb0c2

**Verdict:** Yes, with findings. The owner's choice reaches the overlay, `docs/03` and the ADR
index intact. But one new standing constraint says more than ADR-0002 decides, the poller's
trigger is accepted on a premise the parallel Spotify research has moved, and the record gives
different answers on which PR carries the scaffold's checks and which milestone it belongs to.

### 1. The root `CLAUDE.md` makes every client TypeScript and cites an ADR that does not decide it
- **What** — `CLAUDE.md:132` says "TypeScript for each client". It is a standing constraint, so
  changing it needs an ADR. ADR-0002 does not contain it, and it rules out a native app.
- **Where** — `CLAUDE.md:132-133`. ADR-0002 sets the language only for the website and the
  extension (`docs/adr/0002-the-stack.md:178-182`). For apps it argues the opposite: at `:72-73`
  a phone app is "one more client of a contract", and at `:116-118` and `:258` option C loses
  partly for tying the contract to TypeScript clients. `docs/03-architecture.md:67-69` states
  the narrower rule. Q-F (`docs/08-open-questions.md:51-55`) and the out-of-scope row "Native
  mobile apps" (`docs/00-vision-and-scope.md:74`) leave the apps open.
- **Why it matters** — a Swift or Kotlin app for Q-F would need an ADR to overturn a rule nobody
  decided. `docs/CLAUDE.md:46-47` names this exact trap: a citation that looks reviewed but is not.
- **Suggested resolution** — change the doc to say what ADR-0002 says, as `docs/03` already does:
  TypeScript for the website and the extension. Prose, since no code exists yet for a check.

### 2. The poller's trigger is accepted on a premise the parallel Spotify research has moved
- **What** — ADR-0002 decides "fetch, ingest, store the cursor, exit" on a fixed OS schedule,
  where "every run starts clean", and says the research sets "the interval, not the trigger".
  The Spotify document in flight recommends sampling playback state every 30 s while playing
  and every 3 min when idle, keeping an open play between samples.
- **Where** — `docs/adr/0002-the-stack.md:139-142`, `:183-184` and `:243-246`, and
  `docs/03-architecture.md:30-32`. Against them: `docs/01-data-sources-spotify.md:236-241` and
  `:284` on `origin/claude/spotify-data-source` (PR #3), and `docs/02-domain-model.md:261` on
  `origin/claude/domain-model` (PR #4): "the playback poller's cursor is its open play". PR #4's
  ingestion-seam ADR builds on the one-shot trigger as settled.
- **Why it matters** — an OS scheduler fires on a fixed period (from memory, Task Scheduler cannot
  repeat faster than once a minute), so it cannot express 30 s / 3 min. The one-shot becomes a
  sampling loop bounded by each firing, or the worker ADR-0002 rejected. If the ADR does not
  say which, whoever writes `poll.py` decides, not the owner.
- **Suggested resolution** — before these PRs merge, add the case to ADR-0002's "Where the
  data-source research could change this" and say which shape the trigger takes. Also correct
  `:245`: the YouTube research's daily Data Portability job can be polled. Update `docs/03:30-32`
  to match. Prose: this is a decision record, and no code exists.

### 3. The ADR says its accepting PR ports the layering check and gate areas; this PR does not
- **What** — the overlay, `docs/03` and the handoff move `check_layering.py`, the gate areas and
  the workflows to the scaffold PR. The accepted ADR still gives them to the accepting PR, and
  two scripts still say the product areas arrive "with the stack ADR".
- **Where** — `docs/adr/0002-the-stack.md:227-232`, `scripts/gates.py:12`, `scripts/README.md:61`;
  against `.claude/agents.local.md:80-82`, `docs/03-architecture.md:97` and
  `docs/handoffs/2026-09-23-stack-adr-draft.md:45-49`.
- **Why it matters** — a later reader trusts the ADR, which says the port and the gates came with
  it. The ADR never records that they moved, or why.
- **Suggested resolution** — rewrite the ADR's bullet to name the scaffold PR. The ADR is accepted
  in this PR, so its text can still be corrected without a revision note. In the two script
  texts, change "the stack ADR" to "the scaffold PR". Prose: no check can count what a sentence
  promises.

### 4. The roadmap was not updated, and the scaffold has no milestone
- **What** — `docs/07-roadmap.md` still lists the stack as undone. The scaffold, which the root
  `CLAUDE.md` names as the next PR, fits no milestone: M0 is "no product code", and ADR-0002 says
  "Two toolchains from M1".
- **Where** — `docs/07-roadmap.md:15` and `:26-27` (`open_work.py --fetch` lists the bullet as not
  done), `CLAUDE.md:10-11` and `:52-53`, and `docs/adr/0002-the-stack.md:225`. Also
  `CLAUDE.md:102` and `docs/CLAUDE.md:10`, which still say `03` is still to come.
- **Why it matters** — the roadmap is the first file a reader opens to see where M0 stands, and it
  says the stack is undecided. The board holds product work to a roadmap milestone. Building
  product code before Q-C and Q-D are answered is a sequencing call the roadmap never makes.
- **Suggested resolution** — mark the bullet done with its date. Put the scaffold in a milestone
  in `07`, as M0's last bullet with "no product code" amended or as M1's first; that is the
  owner's call. Fix the two table rows. Prose; `open_work.py` already counts the "done" half.

### 5. `docs/03` leaves the API's conventions to the scaffold's code
- **What** — the error envelope, pagination and how times travel are "settled with the first
  endpoints the scaffold writes", under a heading that exists "so nobody fills the gap by typing".
- **Where** — `docs/03-architecture.md:104` and `:112-113`; against `CLAUDE.md:123-124` (an ADR
  or an answered question first, code second) and `.claude/agents/impl-backend.md:33-36`, which
  looks for these conventions in the overlay and the architecture doc.
- **Why it matters** — how times travel matters here: totals are by local day, and under PR #4
  events change after they are written. An `impl-backend` briefed on the scaffold will find no
  conventions and invent them.
- **Suggested resolution** — say either that the conventions are the sibling's, carried over with
  option A "as is", or that the scaffold's plan writes them into `docs/03` before its first
  endpoint, where the plan's direction review sees them. Prose.

### 6. Q-E does not mention the requirement ADR-0002 puts on it
- **What** — ADR-0002 requires Q-E's answer to provide a database server that starts with the
  machine, and makes SQLite the store if that cannot be met. Q-E's entry mentions neither.
- **Where** — `docs/08-open-questions.md:46-49`; `docs/adr/0002-the-stack.md:215-218`.
- **Why it matters** — whoever answers Q-E starts from its entry, and a host chosen without this
  requirement reopens ADR-0002. The branch left Q-C to Q-F to other lanes, but none of PRs #2 to
  #4 touches `docs/08`.
- **Suggested resolution** — add one sentence to Q-E pointing at ADR-0002's Consequences. Prose.

**Decisions**
- The sibling's stack, Caddy in front; package `constellate` at `api/src/constellate/` — recorded.
- The poller as a one-shot command fired by the OS scheduler — recorded; its fit to a playback
  sampler is not (finding 2).
- Postgres, with SQLite the fallback if Q-E cannot keep a server up — recorded (ADR-0002).
- The ownership map with `sources/` and `poll.py` new; `sources/` behind an interface — recorded.
- API as the only path to data, committed contract, one ingestion path — recorded (ADR-0002).
- "TypeScript for each client" — silent (finding 1).
- Last successful poll stored, shown on the site, reported by `status` — recorded (ADR-0002);
  M1 in `07` does not list it.
- The scheduled task's definition under `infra/`; no hosted platforms — recorded (ADR-0002).
- The `api/.venv`, `pytest` and `ruff` toolchain — recorded (overlay), as the sibling's.
- The layering port and the gates moved to the scaffold PR — recorded against ADR-0002 (finding 3).
- The scaffold as the next PR, during M0 — silent (finding 4).
- API conventions left to the scaffold's first endpoints — recorded against a standing
  constraint (finding 5).

**Follow-ups**
- `.claude/agents.local.md:42-51`: the rows and the unnamed-module rule cover modules only. They
  give no owner for `api/pyproject.toml` or `api/scripts/export_openapi.py`. Check against the
  sibling's overlay before the scaffold creates them.

**What carried it**
- `python scripts/open_work.py --fetch`, when checking what else is in flight. It listed PRs #3
  and #4, whose playback sampler is finding 2, and the unmarked roadmap bullet in finding 4.
