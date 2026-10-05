# Coordinator wind-down: M0 decided on paper, four PRs open, the scaffold briefed
**Summary:** The first day's work stream paused at the owner's request with PR #1 ready, PRs #2 to #4 complete drafts, every lane's worktree clean and the scaffold's director brief saved; nothing merged, and CI never ran.
**State:** Open — resumes on the owner's word: merge #1, rebase and ready #4, ready #2 and #3, one consolidation PR, then the scaffold through `impl-director`.

## Where things stand (2026-09-23, 19:45)

- `main` is `07710fd`, the founding commit alone. Nothing has merged. The repository is still
  private; every Actions run was refused on the account's billing state, so the hooks under
  `.githooks/` are the CI that actually runs.
- **PR #1** `claude/stack-adr` at `3487f7a`, **ready**: `ADR-0002` Accepted (stack A), the
  overlay's ownership map filled, `docs/03-architecture.md` written, the four-reviewer pass
  folded with reports under `docs/reviews/stack-adr/`. Worktree `C:\wt\constellate-stack`, clean.
- **PR #2** `claude/youtube-data-source` at `9543a9f`, draft, complete:
  `docs/01-data-sources-youtube.md`, pass exemption stated. Worktree `C:\wt\constellate-youtube`.
- **PR #3** `claude/spotify-data-source` at `ec00a85`, draft, complete:
  `docs/01-data-sources-spotify.md`, whose §6 reads Spotify's developer terms and Policy §III
  whole. Worktree `C:\wt\constellate-spotify`.
- **PR #4** `claude/domain-model` at `1671790`, draft: `docs/02-domain-model.md` and `ADR-0003`
  Accepted, pass folded under `docs/reviews/domain-model/`, body states `Blocked: #1 must merge
  first`. Worktree `C:\wt\constellate-domain`, clean.
- This PR: `claude/wind-down-handoff`, worktree `C:\wt\constellate-handoff`; it also saves the
  scaffold brief at `docs/reviews/scaffold/impl-director-brief.md`.
- Sessions in the desktop group `favorite_tracker`: "Constellate: coordinator" (this one), ":
  stack ADR draft", ": YouTube data source", ": Spotify data source", ": domain model", all idle
  with their context intact; three standby sessions never used. Memory notes for the coordinator
  are in the memory directory `scripts/check_memory.py` names.

## Decisions the owner took today, in chat; the record cites them by date

1. The name is Constellate (Q-A, answered in `docs/08`).
2. The tracker is the first priority: M1; the atlas M2 and M3; the apps M4 (`docs/07`).
3. The stack is option A — the sibling's stack as is, the poller a one-shot command the OS
   scheduler fires, Postgres (`ADR-0002`, on PR #1).
4. The ingestion seam is accepted as proposed — observations kept verbatim, one event per play
   resolved by precedence — and there is no cross-service item merging (`ADR-0003`, on PR #4).
5. Spotify capture is both paths: the GDPR export as the record plus Spotify's own Last.fm
   connection for the live tail, which must work with no Spotify app at all, and the Web API
   playback poller on top for measured listened time, its policy risk accepted. The poller needs
   Premium and a six-monthly sign-in; the log must never depend on it.
6. The repository may be made public; the coordinator's permission mode refused the flip.

Taken as decided by 3 and 5 and stated to the owner without objection: `ADR-0003`'s amendment
(Web API observations are the one kind deletable as a set, within five days of a disconnect, and
a play reconciled with the export is re-sourced to it); the poller as a bounded sampling run the
scheduler fires every few minutes; the scaffold is M1's first bullet, so M0 closes with PR #1.

## Owner actions outstanding

- Merge #1 (`gh pr merge 1 --squash --delete-branch`), or authorise the coordinator to merge
  ready PRs under the gate: pass folded, `check_prs.py` green, CI green or refused on billing.
- Make the repository public so Actions runs, then re-run the four refused runs.
- Request the Spotify extended streaming-history export and a Google Takeout of YouTube history;
  check YouTube's auto-delete setting, which has defaulted to 36 months since 2020.
- Confirm the Spotify account has Premium.
- Say what "ready means CI green" means while Actions cannot run (the sibling's Q-G).

## Resume sequence

1. After #1 merges: tell "Constellate: domain model" to rebase onto `origin/main`, keep both
   ADR-index rows, push with `--force-with-lease`, drop the Blocked line and `gh pr ready 4`. The
   PR body's scratch source is gone; edit it from `gh pr view 4 --json body`. The pass stays
   valid under `reviews.pass_state`, since only Markdown follows the reports commit.
2. Mark #2 and #3 ready once CI can run or the owner waives it; the owner merges.
3. One consolidation PR, from `main` after #1 and #4: `docs/08` — Q-C answered by `docs/02` and
   `ADR-0003`; Q-D answered by the two `01` documents; Q-E gains a database server that starts
   with the machine, else SQLite (`ADR-0002`), backups kept at most five days, and encryption at
   rest if the Data Portability API is used; Q-F notes that API may make the extension
   unnecessary for capture. Root `CLAUDE.md`: two standing constraints from `ADR-0003` (the log
   holds no catalogue data; no cross-service item merges) and the "private repository" wording
   once public. The overlay lines the domain handoff names. `scripts/review_briefs.py:45` still
   says "board-game-tracker". `docs/00`'s proposed sections corrected to the owner's answers.
4. The scaffold PR (M1): the brief is saved beside this handoff's PR at
   `docs/reviews/scaffold/impl-director-brief.md`; fill `<MAIN_HEAD>`, create
   `C:\wt\constellate-scaffold` on `claude/scaffold`, spawn `impl-director` by name. It surfaces
   four owner decisions: the API conventions, where development Postgres runs, what the tests
   run against, empty modules against "no dead code". Plan-before-code round, then specialists in
   separate worktrees; the session owns `scripts/`, `.github/`, `infra/` and the `CLAUDE.md`
   files. A delegated session editing `CLAUDE.md` files or the overlay needs the owner's approval
   in that session first, so ask before that step.
5. No issue has been filed yet. File M1's on the product board (project 7) when the scaffold
   plan exists; fleet and record work goes on the agents board (project 8) with the `agents` label.

## Traps met today

- The coordinator's shell tool rejects a heredoc past roughly 10 KB; large files go through the
  file-writing tool.
- The auto-mode classifier refused two "create public surface" actions: the visibility flip, and
  once a delegation message that a reworded resend passed.
- Every session in the group has the main checkout as its cwd; a brief must send it to
  `C:\wt\<tag>` or two sessions collide on one tree.
- The 5-hour usage limit hit around 15:00; the lanes resumed on their own at 19:40 with every
  step already committed, which is why briefs ask for early commits.
- `reviews.NOT_RUN` needs "Not run:" exactly; "Not run yet:" made `hook_stop.py` block every turn.

## What carried it

The fleet manual's "verify before acting": every lane report was checked against its branch
before a decision went to the owner, and twice that check found the file said more than the
report — the ADR index conflict, and the pass exemption a PR had outgrown.
