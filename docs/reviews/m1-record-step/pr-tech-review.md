Reviewed at da0e45399cfc

**Verdict:** Fix before merge: the pointer rule this branch adopts trips the repository's own gates,
and five record defects would reach the lanes; none has written wrong data, since no code builds on
them yet.

### 1. Medium: a pointer move in a close's record commit reads as an unreviewed change

- **file:line** `docs/adr/0001-adopt-the-shared-agent-fleet.md:52`, and the withheld gotcha
  sentence, put the bump in "the next close's record commit", but `scripts/reviews.py:158` counts
  every path not ending `.md` as work the pass never saw, and the gitlink `.claude/agents` is such a
  path.
- **Failure:** A branch with its four reports committed, then a close commit of a handoff and the
  gitlink: `reviews.pass_state` returns `('stale', [...])`; the same close with only the handoff
  returns `('ok', [])` (run on a throwaway repository). `scripts/check_prs.py:179` then says "return
  it to draft until a second wave has", and `scripts/hook_stop.py:85` blocks the turn. A separate
  close branch with no reports returns `('none', [...])`, which `hook_stop.py:95` blocks in an
  unattended run. The first close to obey the owner's answer is sent for a second wave over a
  pointer move, the cost the answer removed.
- **Confidence:** certain
- **Fix:** Code, before the withheld sentence lands: treat the path `.claude/agents` as prose in
  `_touches_more_than_prose` (ADR-0001: nothing product-facing depends on it), with a case in
  `scripts/tests/` where a handoff plus the pointer reads `ok`.

### 2. Medium: "every row of an export" and "drop ads" are both on the record

- **file:line** `docs/02-domain-model.md:678` says every row of an export is imported and "a row
  dropped at import never returns", while `docs/01-data-sources-youtube.md:120` and `:325` and
  `docs/reviews/m1-plan/impl-director.md:266` drop Takeout's ad rows on import.
- **Failure:** A `watch-history.json` row with `details: [{"name": "From Google Ads"}]`. The ask
  itself calls Takeout "the export" ("split YouTube Music from YouTube by the export's header").
  Read so, §8 stores the row as a `start_only` event that no total can filter, since `details` is no
  column and §8 promotes nothing for it, so ads count as watches. Read as `docs/01` does, it is
  dropped and, on §8's own reasoning, never returns. Lane 4b gets two answers.
- **Confidence:** likely
- **Fix:** One clause in §8, saying the bullet is Spotify's export and Takeout's ads stay dropped;
  the leaning the owner took lists only Spotify's rows (`impl-director.md:56`). Lane 4b's fixture
  test then holds it: an ad row is dropped and counted.

### 3. Medium: no `record_key` is defined for a stored row with no identifier

- **file:line** `docs/02-domain-model.md:678` stores Spotify's video plays and every other row, but
  §2's keys (`:229`, `:231`) are `google-watch:<video id>@<time>` and `spotify-export:<uri>@<ts>`,
  neither saying what a record with no id keys on, and step 1 drops on that key.
- **Failure:** Two export rows with no recognised URI (the plan stores video plays as "a null item
  where no catalogue item is recognised", `impl-director.md:262`) ending in the same second, as `ts`
  is "to the second" (`docs/01-data-sources-spotify.md:87`): two skips with `ms_played` 0, say. Any
  placeholder for `<uri>` gives both one key, and step 1 silently drops the second as "delivered
  again". That is ADR-0003's "key too coarse", on a row §8 says is kept.
- **Confidence:** worth checking: how often such rows share a second is the owner's export's to say.
- **Fix:** A sentence in §2: an export row with no URI keys on `ts` and a hash of its `raw`. Lane
  4a's fixture then holds it: two such rows, both stored, counts summing to the rows read.

### 4. Low: the proposed protection sentence claims a check that does not bind this account

- **file:line** PR #27's body, "Withheld" item 1, proposed for `CLAUDE.md:42`: "the `record` check
  is required", with `enforce_admins.enabled: false` on `main`.
- **Failure:** `gh api user` is `Atomtomate`, and the repository reports `permissions.admin: true`;
  the root says `gh` is authenticated as the owner. GitHub documents required checks as not enforced
  on administrators under that setting, so a session's `gh pr merge --admin`, or `git push origin
  main` past the hook with the documented `--no-verify`, lands a commit with `record` red or unrun.
  A session reading the sentence takes a red merge to be impossible. Settings read; bypass not run.
- **Confidence:** likely
- **Fix:** Code, if the owner agrees: turn `enforce_admins` on, which still lets the coordinator
  merge on green, since no review is required. Otherwise say in the sentence that it does not bind
  admins.

### 5. Low: the overlay's "the one column that is not resolved" is false from the first migration

- **file:line** `.claude/agents.local.md:174` says so of `service`, while
  `docs/02-domain-model.md:533` puts `owner_id` on the log tables and
  `docs/reviews/m1-plan/impl-director.md:149` names `event` among them;
  `docs/02-domain-model.md:523` and ADR-0003's "fifth column" close the same list.
- **Failure:** Lane 1's `event` carries `owner_id`, set once and never resolved. A reviewer holding
  that migration to the overlay's checklist, which is what the section is for, reports a broken
  invariant, or the column is left off the table the owner's answer most plainly covers. §8 leaves
  the table list open, but no reading of "the log tables" omits `event`.
- **Confidence:** likely
- **Fix:** Prose, as no code exists to test yet: "Its `service` is not resolved", dropping "the one".

### 6. Low: ADR-0004's guard sentence, taken as written, leaves no way to sign in

- **file:line** `docs/adr/0004-sign-in-stored-sessions.md:36` has `RequireSession` guard "every
  endpoint but `/health*`"; `:30` gives a caller with no live session a 401.
- **Failure:** A signed-out `POST /auth/login` (`impl-director.md:233`) is guarded, answers 401, and
  no session can ever be created. `impl-backend-plan.md:100` plans an allow-list, so the lane will
  not build this; the ADR is what a later reader holds the lane to.
- **Confidence:** certain as written; the consequence is confined to the record.
- **Fix:** "every endpoint but `/health*` and the login", held by the plan's allow-list test.

**Follow-ups**

- `.claude/agents/retro.md:139` (fleet) moves the pointer to an unmerged fleet branch in a "merge
  after" PR, which the withheld "once it has merged, the next close moves" contradicts.
- `CLAUDE.md:35`: "a fleet definition, typically" no longer holds once the withheld sentence lands.
- `scripts/check_prs.py:7`: "branch protection ... is not configured" and "the one signal the owner
  merges on" are both out of date.
- `scripts/open_work.py:209` ("the bump PR") and `scripts/pr_body.py:23` describe the old bump.
- `docs/01-data-sources-youtube.md:325` still lists "split by `header`" in the import; M1 does not.
- `docs/01-data-sources-spotify.md:110`: "Whether the tracker keeps them is the owner's call" is now
  answered (`docs/02-domain-model.md` §8).

**What carried it**

The definition's "a bug is usually a mismatch between changed code and code that did not change":
following ADR-0001's revision into every script that says "bump" reached `reviews.py`'s `.md` test,
and a short probe turned the suspicion into `('stale', ...)`.
