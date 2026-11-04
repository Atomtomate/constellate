# impl-director plan check — M1, round 4 (folding the direction review of the re-cut)

*2026-11-04. pr-direction-review read the round-3 re-cut at `fd4b1ef` and filed eight findings
(`docs/reviews/m1-recut/pr-direction-review-plan.md`). Four are mine, four land in docs a session
hand edits in parallel (`docs/02` §1/§8, `docs/07`, `docs/08`, ADR-0002). I verified each at the
file it cites. `impl-director.md` is amended in place with `[C4]` markers. No reviewer was run (a
plan, not code).*

## Per finding

1. **"All nine answered" overcounts — VERIFIED.** The C3 banner (impl-director.md:38-42) and
   check-3:25 say all nine are answered and nothing waits on the owner. Decisions 4 (the owner's
   data requests / account steps, #15/#16/#12/#13) and 5 (the #11 spike) are **owner actions**, not
   answers, and all those issues are open; PR #27 recorded ten decision answers, not these. Amended:
   a `[C4]` note under the banner — six answered (1,3,6,8 as leaned; 2,7 against), 9 met by the
   record step, 4 and 5 outstanding as actions that gate a lane's *close*, not its code.

2. **#20's two leanings written as the owner's — VERIFIED.** `gh issue view 20`: the owner's own
   comment (2026-11-03) chose stored sessions; the second comment (2026-11-04) is explicitly "From
   PR #27's review pass (pr-direction-review, finding 4)" and carries both leanings (a command; defer
   the credential). So they are the reviewer's, posted under the owner's login — digest rec 2's class.
   ADR-0004 delegates the call, so the choices stand; only the attribution was wrong. Amended both
   bullets (impl-director.md:306-313) to "the director's call, as #20's leaning has it", naming the
   reviewer as the leaning's source.

3. **#28 settlement filed as the owner's; auth_session unplaced — VERIFIED (doc = hand's; plan =
   mine).** `docs/02` §8's settlement bullet sits under the heading "Decided by the owner … each as
   the ask put it"; the hand moves it below that list as "Settled by the director". auth_session was
   on neither list, dropped by the wrong test ("not a log table"). **Decision now: `owner_id` goes on
   `auth_session` too** — the §8 test is "the owner's own rows", and a session is the owner's own, so
   it carries the column like the four log tables (a configured UUID, one value while one owner).
   Amended Lane 3/`0003` (impl-director.md:295) from "no owner_id" to "owner_id too", the director's
   call within the owner's words.

4. **Uniqueness consequence misstated — VERIFIED (doc = hand's; plan = mine).** Corrected in Lane 1
   (:202) and cross-referenced at decision 7 (:138). The right reading: `item_ref (namespace, value)`
   is a *world* row with no `owner_id`, shared across owners **by design — not a collision**;
   `observation.record_key` carries `owner_id`, so a second owner's identical key *would* collide;
   a global `source.key` means a second owner cannot hold **any** `source` row (all owners use the
   same keys), so `source.owner_id` stays inert until a later migration. Settlement: leave that
   migration for when a second user arrives (not made now).

5. **"Deferred to Q-F" names an empty home — VERIFIED.** Q-F names no credential question; its home
   is ADR-0004's "Not decided here". Amended the plan (:310) to "stays ADR-0004's open item"; the
   hand adds a Q-F pointer to ADR-0004's caveat and the transport-agnostic-lookup constraint.

6. **Lane 3 told to fold a `docs/03` line already folded — VERIFIED.** `docs/03`'s "Not decided
   here" (now lines ~218-227) lists only the poll interval and the public URL; its 401 row (:163)
   already cites ADR-0004. The sign-in line left is ADR-0002's "Not decided here"
   (`docs/adr/0002-the-stack.md:242-244`). Amended the plan (:318) to drop the stale step and name
   ADR-0002's line; folding it to ADR-0004 is the hand's edit this round, not Lane 3's.

7. **Lane 9's `docs/07` line dropped — VERIFIED.** The record-step handoff (Dismissed; What remains
   open) passed it to this re-cut; check-3's "Lanes 4…9 unchanged" dropped it, and `docs/07`'s M1
   does not name the export the lane builds. Amended Lane 9 (:469) with a `[C4]` session step: before
   the lane codes, the hand adds a `docs/07` M1 bullet naming the plain-format export, citing
   `docs/00`'s v1 criterion. Recording, not a new owner choice — a bullet suffices, no owner message.

8. **Two docs left stale — VERIFIED (hand's, no plan change).** `docs/02` §1's field lists for
   Observation/Source/Ingest run omit the `owner_id` that §7/§8 place on them; `docs/08`'s Answered
   #28 entry still reads "settles which tables". The hand adds it to the three §1 entries and §8-links `docs/08`.

## What the session hand should write, so the two halves agree

- **`docs/02` §8** — the `owner_id` settlement is its own item below the owner's list:
  *"Settled by the director (2026-11-04, `impl-director-check-3/4.md`, within the owner's words):
  `owner_id` is on the owner's own rows — `event`, `observation`, `ingest_run`, `source`, and
  `auth_session` (M1's sign-in table) — not on the world/catalogue tables. It holds one configured
  owner UUID, no users table. Uniqueness stays global now; the consequence for a second owner:
  `item_ref` is shared across owners by design (not a collision), `record_key` would collide, and a
  global `source.key` blocks any second-owner `source` row — so the column buys nothing for a second
  user until a later migration makes `source.key` per `(owner_id, key)` and `record_key` per owner.
  That migration is left for when a second user arrives."*
- **`docs/02` §1** — add `owner_id` to Observation, Source, Ingest run field lists.
- **`docs/07` M1** — a bullet: the plain-format export of the owner's own records, `docs/00`'s v1
  criterion.
- **`docs/08`** — Q-F gains a pointer to ADR-0004's credential caveat; the #28 Answered entry points
  at §8 as settled.
- **ADR-0002:242-244** — the "how the owner signs in" entry in "Not decided here" points at ADR-0004.

## The nine decisions, honest status

- 1 key type (UUIDv7): **answered by the owner** 2026-10-19, as leaned.
- 2 sign-in: **answered against the leaning** 2026-11-03 — ADR-0004, stored revocable sessions.
- 3 import choices: **answered by the owner** 2026-11-03, as leaned.
- 4 owner-provided inputs (#15/#16/#12/#13): **owner actions, still outstanding** — gate lane close.
- 5 the #11 spike: **owner action, still outstanding** — the owner's to run.
- 6 where it runs (Q-E store half): **answered** 2026-11-03, as leaned (Postgres as a service).
- 7 owner column: **answered against the leaning** 2026-11-03 — "add it now".
- 8 null item + `event.service`: **answered by the owner**, as leaned, in the record.
- 9 record-before-code: **met** by the PR #27 record step and ADR-0004.
- #28 sub-points and #20's two questions: **settled by the director** within the owner's words
  (dates 2026-11-04), including `owner_id` on `auth_session` (finding 3).

## Does Lane 1's brief in check-3 change?

**No.** `owner_id`-on-`auth_session` sits in the `0003`/Lane 3 task, not among check-3's two
handable briefs (Lane 2a, Lane 1); `auth_session` is explicitly not Lane 1's, so Lane 1's brief
stands as check-3 wrote it. What changes is the `0003` brief inside Lane 3 (owner_id added) and the
uniqueness *consequence* wording — both in `impl-director.md`, not a brief handed this round.
