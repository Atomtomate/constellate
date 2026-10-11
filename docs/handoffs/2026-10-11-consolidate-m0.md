# M0 consolidated: questions answered, constraints added, handoffs folded, M1 issues filed
**Summary:** Closed M0 in the record: Q-C and Q-D answered, Q-E's requirements and a new Q-G, the roadmap with M0 done and the calendar as M3, `docs/00` corrected to the owner's answers, ADR-0003's two standing constraints and the reviewer checklist, six handoffs folded into eight issues, and two script fixes.
**State:** Open — the review pass, then the coordinator merges; PR #9 rebases onto it; the owner's decisions below.

## What was done

Branch `claude/consolidate-m0` in `C:\wt\constellate-consolidate`, from `main` and rebased onto
`94c11ac`. Briefed by the coordinating session on 2026-10-05, with three addenda on 2026-10-06.

- **`docs/08`**: Q-C answered by `docs/02` and ADR-0003; Q-D by the two data-source documents,
  Spotify's paths as the owner chose them, Premium confirmed 2026-10-05. Q-E lists what the
  ADRs require of the host; Q-F the extension's narrowed role; Q-G, new, what the calendar adds.
- **`docs/07`**: M0 done 2026-10-05, each bullet dated; M1 restated with the decided paths and
  the scaffold first; the calendar inserted as M3 (the owner, 2026-10-06), so constellations
  are M4 and the apps M5. On GitHub: M0 closed, M3 and M4 re-described, M5 created.
- **`docs/00`**: the in-scope capture paths are the owner's answers, the log never depending on
  the poller; the out-of-scope table defers the calendar and the extension and records the
  scraping stance; what nothing decided stays *proposed*.
- **The calendar idea**: three dated decisions (its milestone, scraping, Proton and Google
  Calendar subscriptions, the last verified on both help pages); `adopted`, which is what
  `docs/ideas/CLAUDE.md` calls an idea the roadmap holds.
- **Instruction files, approved by the owner in the session**: the root `CLAUDE.md`'s banner,
  ADR-0003's two standing constraints, and the public-repository sentence; the overlay's banner,
  domain-model line and a reviewer checklist of domain invariants; `docs/CLAUDE.md`'s table.
- **Scripts**: `review_briefs.py` names `Atomtomate/constellate` from `gh_json.REPO`, with a
  test. `test_gates.py`'s head-gating test failed the first commit of any fresh branch that
  touches `scripts/`, because it took `origin/main` to be "not HEAD"; it now uses the zero sha.
- **Folded**: the coordinator's wind-down, the four lane handoffs and the founding handoff, each
  State line naming where its content and open items went.
- **The review pass's fold** reached past the brief's files where an answered question had left
  a document stale: a dated note in ADR-0002 that the sampler's shape was settled on 2026-09-23;
  `docs/02`'s banner; `docs/03`'s poller, clients and "Not decided here"; a note on the Spotify
  document's §5 that the owner chose otherwise; the open calendar handoff's State; and
  `check_prs.py`'s docstring, which still called the repository private.
- **Issues**, product board, M1: #11 the Data Portability spike, #12 the Last.fm source and its
  three unknowns, #13 the playback sampler, #14 the scheduled task, #15 the Spotify export
  importer, #16 the Takeout importer, #17 retiring `docs/02` §7's sketch. Agents board: #18 the
  nightly worktree sweep. #10, the key type, already existed and was not duplicated.

## How it was verified

- `python scripts/check_docs.py` passes, and the pre-commit hook ran it on every commit; the
  record scripts' 339 tests pass.
- `python scripts/check_board.py --fetch` passes: 9 open issues, each on its board, and six
  milestones mirroring this branch's roadmap.
- The calendar's subscription claims were checked against each page's raw text on 2026-10-06,
  not only through a summarising fetch: Proton's help page, Google's, Proton's feedback forum
  and the Calendar API reference.
- The standard review pass: the reports are under `docs/reviews/consolidate-m0/`, and the PR
  body's Review pass section says what was acted on and what was dismissed.

## What remains open

- **`main`'s board check fails until this PR merges**: M5 was created on GitHub on 2026-10-06,
  and `main`'s roadmap has no M5 heading yet ("GitHub milestone M5 is not in the roadmap").
- **PR #9, the scaffold, rebases onto this one.** Expect conflicts in the overlay's banner and
  at the end of the root `CLAUDE.md`'s standing constraints; the overlay's domain-model line
  is written exactly as #9 writes it.
- **The calendar idea's handoff stays open**: its first three questions are the owner's, and
  the root `CLAUDE.md` still has no `docs/ideas/` row (below).
- **M1's remaining cut** (the `videos.list` cache job, the timeline and totals, sign-in) is the
  director's after the scaffold; no issue was filed for it here.

## Needs a decision

- **Branch protection on `main`**, available since the repository went public. Leaning: protect
  `main` — a PR required, the `Record` check required (and the scaffold's checks once they
  run), no force-push or deletion, no required approval, since the owner cannot approve their
  own PR. The draft flag stays the readiness signal.
- **The `docs/ideas/` row in the root `CLAUDE.md`**: "Idea capture. Has its own `CLAUDE.md` —
  read it before filing one." The coordinator asked for it; it is an instruction-file edit the
  owner had not approved when this was written, so it is not in this PR. Leaning: add it.
- **The owner's exports and accounts**, which nothing else can start: request Spotify's
  extended streaming history (#15); check YouTube History and auto-delete, then request a JSON
  Takeout (#16); connect Spotify to Last.fm (#12); confirm the Google account is in the EU,
  Switzerland or the UK for the spike (#11).
- **`docs/02` §8's choices**, before the importers. Leanings: import everything the export
  holds — private sessions, podcasts, audiobooks, video plays — and filter in totals, since a
  dropped record never returns; split YouTube Music from watching by `header`; strip `ip_addr`
  on import and keep `conn_country`, which a per-event time zone would need; one configured
  time zone for local days; an unidentifiable watch as an event with no item, as §1 has it.

## What carried it

The folded handoffs' own "What remains open" sections, read whole before anything was filed:
every issue traces to one of their lines, and each fold names the issue its line became.
