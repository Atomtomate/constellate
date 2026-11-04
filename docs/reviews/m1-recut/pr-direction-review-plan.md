Reviewed at fd4b1ef

**Verdict:** Mostly. The re-cut follows the two reversed answers where they lead: stored sessions
become `0003`, `owner_id` lands in Lane 1, and the contract stays additive. But it reports two
owner decisions that were never taken, gives the owner leanings that were a reviewer's, and files
its #28 settlement under the owner's heading in a sentence that gets the consequence wrong. Fix
those before Lane 1 is briefed.

### 1. "All nine are now answered" counts two the owner has not answered
- **What** — The banner says decisions 4 and 5 were answered "as their leanings (PR #27 recorded
  them)" and "Nothing below still waits on the owner". Decision 4 is owner actions with no leaning.
  Decision 5 is the #11 spike, which is "the owner's to run". Neither is among PR #27's ten answers.
- **Where** — `docs/reviews/m1-plan/impl-director.md:38-41`; `impl-director-check-3.md:25`; commit
  `50c96bc`'s answer table; issues #11–#16, all open; digest recommendation 2.
- **Why it matters** — The coordinator reads this banner first, and it tells them to stop asking.
  The spike's "run it early" then goes unprompted. A failed spike puts Q-F, or an amended done-when,
  in front of the owner (decision 5's C2), and that is still ahead.
- **Suggested resolution** — Change the plan. Say 1, 3, 6 and 8 were answered as leaned and 2 and 7
  against the leaning. Say 9 is met by PR #27. List 4 and 5 as owner actions still outstanding.

### 2. Issue #20's two leanings are written as the owner's
- **What** — "A command, not endpoints or a screen" and "deferred to Q-F" are both labelled "the
  owner's leaning". Both leanings come from PR #27's direction review (finding 4), posted from the
  owner's `gh` login. The owner said nothing on either.
- **Where** — `impl-director-check-3.md:48-49`, `:53-54`; `impl-director.md:306-307`, `:309-310`;
  issue #20, second comment ("From PR #27's review pass").
- **Why it matters** — This is digest recommendation 2's class again: a relay becomes "the owner's"
  and is cited later as the owner's decision. ADR-0004 does let the re-cut settle the first
  question, so the call stands. Only the attribution is wrong.
- **Suggested resolution** — Change the plan to "the director's call, as #20's leaning has it
  (ADR-0004 delegates it)".

### 3. The #28 settlement is filed as the owner's and reads "the log" narrower than the record
- **What** — The new bullet sits in §8's list "Decided by the owner … each as the ask put it", and
  says it is "within the owner's words". It reads "the log tables" as the owner's own rows only. But
  §5 calls the item "the log's table", and §3 says a hand-set `item_creator` link "is the owner's
  own record". `auth_session`, the eleventh table M1 builds, is on neither list. The plan leaves
  `owner_id` off it as "not a log table", a different test from §8's.
- **Where** — `docs/02-domain-model.md:670`, `:684-692`; `:476-477`; `:337-338`;
  `impl-director.md:31` ("the four log tables"), `:295`.
- **Why it matters** — A derived reading filed as one of the owner's answers will be quoted as one.
  §3 and §8 now classify `item_creator` in opposite ways.
- **Suggested resolution** — Change the doc. Move the bullet below the owner's list as "Settled by
  the director". Reconcile §3's hand-set link with it. Name `auth_session`, and its own reason, in
  the bullet.

### 4. The uniqueness sentence misstates what a second user hits
- **What** — §8 lists `item_ref (namespace, value)` as a collision a second user's record would hit.
  But the same bullet makes `item_ref` a shared world row, so the uniqueness is the design working,
  not a collision. Global `source.key` (`spotify-export`, …) is worse than the sentence admits: a
  second owner cannot have any source row at all, so `source.owner_id` stays inert even once a
  second user exists.
- **Where** — `docs/02-domain-model.md:688-692`, `:162-176`; `impl-director-check-3.md:39-42`;
  `docs/adr/0003-the-ingestion-seam.md:162-166` (leaves only matching and `record_key` open).
- **Why it matters** — The owner chose "Add it now" over "a migration later", and the option said
  the column "buys nothing until a second user exists". As settled, the column still needs that
  later migration. The record says otherwise, and the owner reads it.
- **Suggested resolution** — Change the doc, so it states the real consequence. Then the director
  either makes `source.key` unique per `(owner_id, key)` now, which is cheap before any data, or
  says the later migration remains.

### 5. "Deferred to Q-F" names a home that does not hold the question
- **What** — The plan defers how a non-browser client presents a credential "to Q-F / the
  extension". `docs/08` Q-F names no credential question.
- **Where** — `impl-director-check-3.md:53-57`; `impl-director.md:309-313`;
  `docs/08-open-questions.md` Q-F; ADR-0004, "Not decided here".
- **Why it matters** — With this re-cut, #20's done-when is met and the issue can close. After that
  the question survives only in a plan file and an ADR's caveat. Whoever designs the extension
  starts from Q-F and will not find it there.
- **Suggested resolution** — Change the doc. Add a line to Q-F pointing at ADR-0004's caveat and the
  plan's constraint that sessions are looked up by token, whatever carries it. Or say "stays
  ADR-0004's" instead of Q-F.

### 6. Lane 3 is told to fold a `docs/03` line PR #27 already folded
- **What** — The C3 note says Lane 3 "folds `docs/03`'s 'Not decided here' line to point at
  ADR-0004". That line is gone: `docs/03` lists only the poller's sampling and the URL there, and
  its 401 row already cites ADR-0004.
- **Where** — `impl-director.md:318-319`; `docs/03-architecture.md:166`, `:220-227`; commit
  `50c96bc` (its sign-in row, "`docs/03`'s 401 row and 'Not decided here'").
- **Why it matters** — It sends the lane after a stale step and hides the line that is actually
  left: ADR-0002's own "Not decided here" still lists sign-in.
- **Suggested resolution** — Change the plan. Drop the step, or point it at
  `docs/adr/0002-the-stack.md:242-244`.

### 7. Lane 9's `docs/07` line was handed to this re-cut, and dropped
- **What** — The record-step handoff passed the Lane 9 line for `docs/07` to "the director's
  re-cut", because "a milestone's scope is not changed in passing". Check-3 says only "Lanes … 9 are
  unchanged". `docs/07`'s M1 still does not name the plain-format export, yet the plan builds it as
  M1 scope.
- **Where** — `docs/handoffs/2026-11-03-m1-record-step.md` (Dismissed; What remains open);
  `impl-director.md:479-480`; `impl-director-check-3.md:66-68`; `docs/07-roadmap.md` M1.
- **Why it matters** — A lane builds what the roadmap's milestone does not list, and the handoff's
  open item has nowhere left to go.
- **Suggested resolution** — Record it. Either put it to the owner as M1 scope, which is the
  handoff's own reasoning, or add a `docs/07` bullet citing `docs/00`'s v1 criterion. Check-3 should
  say which.

### 8. Two docs the settlement left stale
- **What** — §1's field lists for Observation, Source and Ingest run do not mention `owner_id`,
  which §8 now places on all three. `docs/08`'s Answered entry still says "issue #28 settles which
  tables", which §8 has now done.
- **Where** — `docs/02-domain-model.md:116-117`, `:158-188`; `docs/08-open-questions.md:102`.
- **Why it matters** — §1 is where a reader goes first for a table's fields, and Lane 1's specialist
  reads it. The change reached §7 and §8 and stopped one section short.
- **Suggested resolution** — Change the docs. Add `owner_id` to the three §1 entries, as Event has
  it, and point `docs/08` at §8.

**Decisions**
- Stored sessions as `auth_session` in a separate `0003`, gated on `0002`: recorded (ADR-0004; plan
  C1).
- `auth_session` holds a token hash and `expires_at`, with no `owner_id`: recorded in the plan only
  (finding 3).
- Five repo capabilities, against the option text's "three repo functions": recorded, as derived.
- M1 lists and revokes sessions, revoke-all included, through `python -m constellate.sessions`:
  recorded, but misattributed (finding 2).
- The non-browser credential deferred; the lookup kept independent of the cookie: recorded,
  misattributed, home missing (findings 2 and 5).
- `owner_id` on `event`, `observation`, `ingest_run` and `source`, not on the six world tables:
  recorded as the director's, but filed under the owner's (finding 3).
- `owner_id` holds one configured UUID, with no users table: recorded (`docs/02` §8).
- Uniqueness stays global: recorded, with its consequence misstated (finding 4).
- `DraftEvent` gains no owner field, and the service stamps `owner_id`: recorded (check-3, Lane 2a).
- `owner_id` is never on the contract: recorded (the plan's Contract impact).
- Decisions 4 and 5 treated as answered: silent and unsupported (finding 1).

**Follow-ups**
- `docs/02` §3's ref list still lacks `spotify:show-name`. That is check-2's item, which the handoff
  also names as the re-cut's, due when 4a lands.
- `docs/reviews/m1-plan/impl-backend-plan.md:82-84` still cuts Lane 3 stateless ("a session table:
  Lane 1's"). Lane 3's brief should say the C3 note supersedes it.
- Issue #20's done-when is met once this lands, so the closing step can close it.

**What carried it**
The ten-row answer table in commit `50c96bc`'s message, read against the C3 banner. The banner's
"all nine are now answered" could only be checked against the answers PR #27 actually recorded.
