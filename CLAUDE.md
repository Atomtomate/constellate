# Constellate

A log of what the owner listens to on Spotify and watches on YouTube — when, and for how
long — and, on top of it, an atlas of favourite videos, music and websites and of the
thematic constellations between their creators, so that "what would you recommend?" and
"who were those creators again?" are answered with a link rather than from memory. The
tracker first, the atlas after, apps last. The brief, and everything derived from it, is
[`docs/00-vision-and-scope.md`](docs/00-vision-and-scope.md).

**The project is at M0.** The stack is decided (ADR-0002) and its scaffold is the next PR;
there is no product code and no schema yet. What exists is the written plan, the agent fleet
and the record. The open questions the first schema and the first source wait on are
`docs/08-open-questions.md`'s Q-C and Q-D.

## Working agreement

The owner wants control over what happens.

- **Ask before major implementation decisions.** Anything that would be expensive to
  reverse, settles an open question in `docs/08-open-questions.md`, or contradicts an ADR.
  Offer a recommendation with it — a question without a leaning is just work handed back.
- **Feature branch per task, PR at the end of it.** Never commit to `main`.
- **A PR opens as a draft and stays one until it is ready to merge**, and ready is the one
  signal that it may be. Ready means the closing step's gates are met: CI green; the
  standard pre-review pass below run on the branch, its four reports committed under
  `docs/reviews/<branch>/` and its findings folded; the PR body's **Review pass** section
  saying what was acted on and what was dismissed, with reasons; the handoff written. The
  one exception is a PR with no behaviour or decision content — docs, tooling,
  bookkeeping — which may be marked ready with a Review pass section that says the pass
  was not run and why. A PR that stacks on another is based on that branch, says "merge
  after #N", carries the `reviewable` label once its own gates are met, and stays a draft
  until its base has merged; GitHub then retargets it to `main`, because this repository
  deletes head branches on merge. **A PR waiting on one in another repository** — a fleet
  definition, typically — says "merge after `owner/repo#N`" and stays a draft the same
  way. Ready is a property of the commit the pass saw: a commit after the flag goes up
  returns the PR to draft until a second wave has seen it. **A draft that is finished and
  still cannot go ready states `Blocked: <reason>` in its body**, on a line of its own —
  the one fact about a PR nothing can derive, and the line `scripts/close_report.py`
  reads. `python scripts/check_prs.py --fetch` at the closing step reports a ready PR that
  breaks what it can see. GitHub cannot enforce any of this on a private repository on the
  free plan, so the draft flag is the guard.
- **The owner reviews everything** and sends comments back to act on.
- Keep commits logically ordered so `git log -p` reads in sequence.

### Who this session talks to

Four agents are entry points from here. Each owns the choosing below it, so this session
does not route work itself:

- **`impl-director`** — implementation work by default, including work inside a single
  layer. It plans across the layers, says what each owns and in what order, and hands off;
  it writes no code. Its file-ownership map is in `.claude/agents.local.md` (ADR-0002), and
  the scaffold PR is the first work it cuts.
- **`manager`** — every few sessions, and always before a retro: reads the record since its
  last digest and writes one under `docs/digests/`, judged and ranked. The owner reads it
  first; the retro takes its list first. It changes nothing.
- **`retro`** — runs instead of new work, once every few sessions, after the `manager`.
- **`ops`** — the running stack, not the repository. **There is no stack yet**; the overlay
  says so, and `ops` invoked before there is one should stop.

Invoke them by name, and write a prompt that stands alone — every agent starts cold. The
other seven are reachable but not a menu this session chooses from: the implementation
specialists (`impl-database`, `impl-backend`, `impl-frontend`) are briefed by the director,
or directly **only when the owner asks for that agent by name**; the reviewers
(`pr-tech-review`, `pr-direction-review`, `pr-parsimony-review`, `pr-architecture-review`)
have disjoint scopes and all four run on every PR. Their scopes, models and how to brief
one are in the fleet's [`.claude/agents/CLAUDE.md`](.claude/agents/CLAUDE.md); this
project's answers to the generic fleet are in
[`.claude/agents.local.md`](.claude/agents.local.md), the overlay (ADR-0001).

### The standard pre-review pass

**Run all four review agents on every PR once its code is done — before the turn that
reports it, not when asked — and act on what they find.** `scripts/hook_stop.py` holds a
session to it. Run them in parallel — their scopes are deliberately disjoint, so expect
little overlap, and where two reach the same conclusion from different directions treat
that as the strongest signal available. A reviewer's brief is
`python scripts/review_briefs.py`'s output, never freehand.

**Verify before acting** — the fleet manual's "Using them" says what that means, for a
reviewer's claim and for one read in a handoff or an issue.

Fix what is real, then tell the owner what was found **and what was dismissed, with
reasons** — including findings you disagreed with. Never quietly bury one. The follow-ups
a reviewer recommends outside its scope get the same treatment: done, filed, or declined
with a reason.

### Finishing, and the retro

A task ends with a handoff in `docs/handoffs/` and a closing step that keeps the record
and the two GitHub boards — product work, and the agent setup — in step with what it did:
the scripts under `scripts/` say what drifted, and `scripts/README.md` lists the order to
run them in. Every few sessions, and always before a retro, the `manager` runs. Once every
few sessions the `retro` agent runs instead of new work. Both conventions are in
[`.claude/agents/CLAUDE.md`](.claude/agents/CLAUDE.md).

## Where things are

| Path | What |
|------|------|
| `docs/adr/` | Decisions. Check status: Accepted, Proposed, Superseded or Parked. |
| `docs/00`, `03`, `07`, `08` | Scope, architecture, roadmap, open questions. `02` (domain model) arrives with Q-C's answer. |
| `docs/investigations/` | **Parked** research. Nothing here influences a design decision until deliberately unparked. |
| `docs/handoffs/` | One file per finished task: what was done, verified, and left open. |
| `docs/friction/` | One note per time an agent's process failed it. Written by the agent, read by the `retro`. |
| `docs/reviews/` | A branch's review pass: one report per reviewer, and the implementation agents' plans. |
| `docs/digests/` | One file per `manager` run. |
| `api/` | The API package, `constellate`: FastAPI, SQLAlchemy and Alembic on Postgres (ADR-0002) — the layers, the migrations, the tests, and `api/openapi.json`, the contract every client generates from. See `api/CLAUDE.md`. |
| `web/` | The web client: React + Vite, TypeScript, a consumer of the client generated from the contract. See `web/README.md` and `web/CLAUDE.md`. |
| `compose.yaml` | The development Postgres: one server on `127.0.0.1:5432` shared with the sibling project, this project's database and role on it. The API runs on the host. |
| `infra/` | What runs the stack. Today the development database's bootstrap; the rig — the stack script, the Caddyfile, the scheduled task — is Q-E's and arrives with its answer. Edited from the session; no specialist owns it. See `infra/README.md`. |
| `scripts/` | Repo-wide record checks: what the closing step and the `retro` run rather than re-derive. See `scripts/README.md`. |
| `.claude/agents/` | The generic agent fleet, a git submodule (ADR-0001). Its `CLAUDE.md` is the fleet's process manual. |
| `.claude/agents.local.md` | This project's answers to that fleet. |
| `.githooks/` | Version-controlled git hooks. `post-checkout` populates the fleet submodule in a new worktree; `pre-commit` and `pre-push` run the checks CI runs (`scripts/gates.py`). Activating them: Environment gotchas. |

Read `docs/` before proposing architecture. Where the plan is silent, that is a question
for `docs/08-open-questions.md`, not a gap to fill by typing.

## Standing constraints

These are decided. Changing one needs an ADR, not a commit.

- **The fleet is consumed, not forked.** A definition is edited in `Atomtomate/agents` and
  reaches here as a pointer bump; the overlay is the only place this repository tells the
  fleet anything (ADR-0001).
- **A decision is written down before it is built on.** A stack, a schema, an import seam:
  an ADR or an answered question in `docs/08` first, code second.
- **The API is the only path to data.** Every client — the website, an extension, any app —
  consumes the contract on equal terms, and none gets privileged access; the poller and the
  importers reach the data through `services/` inside the API's own package (ADR-0002).
- **`api/openapi.json` is committed and CI-checked**, and every client generates from it.
  Regenerate it after any change to the API surface (ADR-0002).
- **One ingestion path.** Every source produces the same draft event and exactly one service
  persists it; a new source is an adapter, never a second write path (ADR-0002).
- **One language per deployable.** Python for the API package; TypeScript for the website and
  for the extension, each a deployable of its own; nothing crosses a language boundary but the
  contract (ADR-0002).

## Style

Applies everywhere. Language-specific rules are in the directory's own `CLAUDE.md`.

- **Every public module, class and function carries a docstring.** Enforced by the linter
  (ruff's `D1` rules, `api/pyproject.toml`), not left to good intentions. Tests are exempt, a test's name being its
  documentation, and so are generated migration files.
- **Docstrings say what and why; the signature says how.** Restating the parameter list in
  prose is noise. What earns its place: the constraint a caller must respect, the reason a
  surprising choice was made, what it does *not* do.
- **Comments explain why, never what.**
- **Name the concept, not the type.**
- **No dead code, no speculative parameters.** Deletion is free; something nobody calls is
  a thing the next reader has to understand before they can ignore it.
- Wrap at 100 columns.

## Documentation structure

`CLAUDE.md` files are the operating instructions, one per meaningful directory, each
covering only what is specific to it. Do not restate a parent's rules in a child.

| File | Covers |
|------|--------|
| `CLAUDE.md` (this) | The project, the working agreement, standing constraints, style |
| `docs/CLAUDE.md` | How the written record works |
| `api/CLAUDE.md` | Running the API package: its venv and commands, Python conventions, what CI fails on |
| `api/src/constellate/CLAUDE.md` | The layering: what belongs in which layer and why, the `sources/` seam, the entry points |
| `api/alembic/CLAUDE.md` | Migration rules — small directory, dangerous mistakes |
| `api/tests/CLAUDE.md` | Testing conventions: the two backends, which checks are CI's alone |
| `web/CLAUDE.md` | The client's conventions — the generated client, its layer rule, how it is tested |
| `.claude/agents/CLAUDE.md` | Writing and using the agents (the fleet's; read here, edited there) |

When a rule changes, change it in the one file that owns it. A rule stated twice is a rule
that will eventually contradict itself.

## Environment gotchas

- **The hooks gate a commit and a push, and they are the same checks CI runs.**
  `.githooks/pre-commit` runs the fast half of what the staged change calls for,
  `.githooks/pre-push` runs what the build would; both ask `scripts/gates.py`. Activate
  them once per clone with `git config core.hooksPath .githooks`. Past one, once:
  `--no-verify`.
- **`gh` is on PATH** on the dev machine and authenticated as the owner. **PowerShell 5.1
  mangles double quotes inside a `--body` or `--jq` argument**: write the body to a scratch
  file and pass `--body-file`.
- **The agent fleet is a git submodule at `.claude/agents/`, and `git worktree add`
  leaves it empty.** `.githooks/post-checkout` fills it once `core.hooksPath` is set
  (above). Without that, run `git submodule update --init .claude/agents` in the worktree
  by hand and start a *fresh* session. A session the app starts in a worktree it has just
  created can scan the roster before the hook has cloned the fleet: the sign is a first
  system reminder listing only the built-in agents while `.claude/agents/` is populated;
  the fleet manual's fallback says what to do meanwhile. To *edit* a definition, work in
  the fleet repository and open a PR there, then bump the submodule pointer here in a PR
  that says "merge after `Atomtomate/agents#N`".
- **This clone has `extensions.worktreeConfig` on.** A config value — `core.hooksPath` and
  `constellate.mode` included — can be set per worktree, so what one checkout reports is
  not necessarily true in another.
- **A throwaway worktree needs a short, unshared root.** `%TEMP%\claude\` is shared by
  concurrent sessions and a session scratchpad is deep enough to pass MAX_PATH; use a
  short path of your own (`C:\wt\<tag>`), and chain a probe's commands with `&&`.
- **Windows line endings.** `.gitattributes` forces LF in the working copy; the hooks are
  shell scripts and will not run with CRLF.
