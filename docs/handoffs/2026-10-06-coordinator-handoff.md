# Coordinator handoff: M0 merged, the scaffold building, the consolidation PR in flight
**Summary:** Two days of resumed work: PRs #1 to #6 merged and the repo public; the scaffold is being built by a workflow in its worktree and the M0 consolidation PR by a standby session; the coordinator's context is full and hands over mid-flight.
**State:** Open — the next coordinator finishes the scaffold PR (verify, review pass, merge) and merges the consolidation PR; the owner's exports are still not requested.

## Where things stand (2026-10-06, 22:00)

- `main` is `29e1590`: ADR-0002 (stack A), ADR-0003 (the seam), `docs/02`, `docs/03`, both
  data-source documents, the ideas directory with the calendar idea, five folded-to-be handoffs.
  The repository is public since 2026-10-05 and the Record workflow is green on every branch.
- **Scaffold**, branch `claude/scaffold` at `f1e25ea` (plan files committed, pushed), worktree
  `C:\wt\constellate-scaffold`. A workflow (run `wf_4ed2aa2f-5fb`, script
  `scaffold-build-wf_4ed2aa2f-5fb.js` under the session's `workflows/scripts/`, journal under
  `subagents/workflows/wf_4ed2aa2f-5fb/`) was mid-build: the Conventions step done (`docs/03`
  Conventions section, `compose.yaml`, `infra/`), `impl-database` and `impl-frontend` writing
  `api/` and `web/`, then `impl-backend`, the client schema, the layering port and gate areas,
  the CLAUDE.md files, a verifier and two fix rounds. Everything it wrote is **uncommitted** in
  that worktree. No PR is open for it yet.
- **Consolidation PR**, session "Constellate: consolidation", branch `claude/consolidate-m0`,
  not pushed when this was written. Its brief plus three addenda: Q-C and Q-D answered, Q-E's
  rig requirements, Q-F's note, new Q-G (what the calendar adds to the model); M0 done in
  `docs/07` and the calendar inserted as the new M3 with constellations M4 and apps M5, GitHub
  milestone M5 created and M3/M4 descriptions patched, M0 closed; `docs/00` corrected to the
  owner's answers and the scraping stance; root `CLAUDE.md` banner, ADR-0003's two standing
  constraints, the public-repository wording, a `docs/ideas/` row; overlay banner and the
  reviewer invariants; `docs/CLAUDE.md` table; `scripts/review_briefs.py`'s repository name;
  the five earlier handoffs folded and M1's first issues filed on project 7; the idea file's
  dated decisions (slot, scraping, Proton and Google Calendar link); the four-reviewer pass.
  It reports by `SendMessage` to "Constellate: coordinator"; if that session is gone, read the
  branch and `gh pr list` instead.

## Decisions the owner took on 2026-10-05 and 06

1. Ready PRs are merged by the coordinator; most things need no oversight.
2. The repository is public; "ready means CI green" stands as written.
3. Spotify Premium confirmed, so the Web API poller stays as an optional source.
4. Scaffold: the sibling's API conventions; development Postgres shared with the sibling's
   Docker instance through a repo-root `compose.yaml`; tests dual (SQLite default,
   `CONSTELLATE_TEST_DATABASE_URL` for Postgres); **every layer scaffolded now**, against the
   director's leaning; the infra gate area checks only `compose.yaml` and the docker probe.
5. Calendar: its own milestone between the collection and the constellations; scraping public
   pages allowed per site terms; must be subscribable from Proton Calendar and Google Calendar
   (an ICS feed; Proton has no API, so one-way; Google could take writes later, open).

## Resume sequence

1. Check whether the scaffold workflow finished: its journal, and `git status` in the worktree.
   If this session was cleared before the task notification, the agents died mid-write.
   Either way: run the plan of record's verification list (`docs/reviews/scaffold/
   impl-director.md`, "Verification (by command)") and compare the tree with the plan's cut
   and decision 4's layer list; commit what is complete as a WIP commit; re-run only what is
   missing or failing — a new workflow with the Verify and Fix stages copied from the script
   (lanes by `agentType`: `impl-database`, `impl-backend`, `impl-frontend`; session-owned
   files by a plain agent), all pointed at the worktree by absolute path.
2. When green: commit, `gh pr create --draft` ("merge after" nothing: it is on main), then the
   four reviewers in two waves from `scripts/review_briefs.py`, fold by lane, commit the
   reports last, `gh pr ready`, merge after CI. The scaffold's record edits (the overlay's
   contract/layers/toolchain sections, `docs/03`, root `CLAUDE.md` tables) will conflict with
   the consolidation PR on the overlay and the root `CLAUDE.md`: merge consolidation first,
   rebase the scaffold, re-run `check_docs`.
3. Merge the consolidation PR when it goes ready (its pass is owed and in its brief).
4. Then M1's lanes from the issues the consolidation PR files: the Spotify export importer,
   the Last.fm source, the playback sampler, the Takeout importer, the Data Portability spike.

## Sessions

Keep: "Constellate: consolidation" (mid-PR). This coordinator holds the running workflow;
clear it only after the scaffold's task notification, or accept step 1's recovery. Clear:
"Constellate: Spotify data source", "Constellate: YouTube data source", "Constellate: domain
model" (their work is merged; their worktrees `C:\wt\constellate-spotify`, `-youtube`,
`-domain`, `-stack`, `-handoff` can go: `git worktree remove`), "Planning session standby" (its
PR #6 merged), and the offline Remote Control duplicates of all of them.

## Traps met

- A workflow subagent reads the session's cwd, the stale main checkout; every brief must
  point it at the worktree by absolute path, and `request_directory C:\wt` must be granted.
- The owner's mid-turn message reached a running director as "the user's actual request";
  it planned the calendar instead of the scaffold until the check rounds corrected course.
- The first rebase of PR #4 replayed two commits onto one ADR-index line; a keep-both resolver
  left a duplicate row, which the pre-push hook caught. Resolve index rows by hand.
- The safety classifier timed out once on an `impl-database` subagent; its output was a plan
  file only, verified by `git status`.

## Needs a decision

- Branch protection on `main` now the repository is public (the consolidation handoff carries
  the leaning).
- The exports: the Spotify extended streaming history and the Google Takeout are still not
  requested; nothing else can start the backfill.

## What carried it

The plan of record's "Verification (by command)" list: it made the build workflow's verifier a
mechanical stage rather than a judgment, and the owner's five answers slotted into it unchanged.
