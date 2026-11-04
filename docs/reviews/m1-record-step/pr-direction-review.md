Reviewed at da0e45399cfc

**Verdict:** Mostly yes. Every owner answer reaches the file that owns it, in the owner's words, and
nothing parked or out of scope came in. But the record contradicts itself on `owner_id`, calls a
narrowing of a standing constraint "not a new decision", omits what stored sessions were chosen for,
and stops the bump and Q-E answers short of lines that still bind, one of them a gate.

### 1. "The one column that is not resolved" is false against this branch's own `owner_id`
- **What** — The overlay, ADR-0003 and §6 state the event's columns as an absolute (`service` the
  "one" unresolved, the "fifth", a closed list) while §7 and §8 put `owner_id` on the log tables.
- **Where** — `.claude/agents.local.md:174`; `docs/adr/0003-the-ingestion-seam.md:149-157`;
  `docs/02-domain-model.md:60-66`, `:523-524`, against `:533`, `:667`. Older absolutes the revision
  narrowed and left: `:18`, `:111` (columns resolved); `:18`, `:44` ("verbatim").
- **Why it matters** — The plan-round's finding 3 again, one column later. Reviewers enforce the
  overlay's checklist, so Lane 1's `event.owner_id` fails it or teaches them to skip it. ADR-0003's
  safety argument covers `service` alone; `owner_id` is also written once, and matching names no
  owner.
- **Suggested resolution** — Change the docs: "Its `service` is not resolved", no count, no closed
  list; a clause in ADR-0003's revision for `owner_id`; fix `:18`, `:44`, `:111`. Prose, as no table
  exists yet. Lane 1 then adds a test pinning which event columns the resolver may write.

### 2. §8 files `owner_id`'s open half under Decided, and its ranking omits the key type
- **What** — What `owner_id` holds and on which tables is open, yet sits in a Decided bullet, not in
  §8's Open or `docs/08`; the ranking omits the key the quoted ask calls hardest to change.
- **Where** — `docs/02-domain-model.md:11`, `:634-650`, `:661`, `:669-670`, `:691-701`;
  `docs/08-open-questions.md:99-102`; `docs/00-vision-and-scope.md:59`.
- **Why it matters** — If `record_key` and `item_ref` stay globally unique the column cannot serve
  the second user it exists for; if they include it, ADR-0003 and the overlay's invariant change. A
  users table meets `docs/00`'s "No accounts beyond that". Only the PR body says this gates Lane 1.
- **Suggested resolution** — File an M1 issue gating Lane 1, which `check_board.py` and
  `open_work.py` then count, and name it in §8's Open and `docs/08`'s entry. Add the key type to the
  ranking: prose, since no check can rank a cost.

### 3. `CatalogueAdapter` narrows a standing constraint and says it is "not a new decision"
- **What** — `docs/03` adds a source that yields no draft, under a heading saying changing these
  rules needs an ADR, and calls it a clarification, while three higher lines still say every source
  does.
- **Where** — `docs/03-architecture.md:51-53`, `:71-76`, `:92`; against the root `CLAUDE.md:140`,
  `docs/adr/0002-the-stack.md:188-190`, `:296-298`, `docs/02-domain-model.md:197`.
- **Why it matters** — The design is sound, and the plan-round's finding 9 asked for this sentence,
  but named the root line as the problem. A Lane 5 reviewer holding "every source" still blocks it,
  and this PR's own logic on ADR-0001 (a Consequence the answer makes false gets a revision) goes
  unapplied.
- **Suggested resolution** — Record it: a dated revision in ADR-0002's Consequences, what changed
  and why safe; drop "not a new decision"; fix `docs/02:197`; add the root's one word to Withheld.
  Prose, since no check tells a narrowing from a clarification; Lane 5's types then make the mistake
  impossible, a `CatalogueAdapter` having no way to return a draft.

### 4. ADR-0004's "Not decided here" omits what the owner chose stored sessions for
- **What** — The owner overrode the leaning to revoke and list single sessions, yet nothing says
  whether M1 builds that surface, or how the other named client presents a credential.
- **Where** — `docs/adr/0004-sign-in-stored-sessions.md:29-31`, `:43-44`, `:55-61`; against
  `docs/reviews/m1-plan/impl-director.md:233`, `:426-428` (login, logout, `/me` only), `:88-91` (a
  failed #11 can pull the extension into M1); root `CLAUDE.md`, "The API is the only path".
- **Why it matters** — "The owner can see which exist" is true only with endpoints or a command. In
  the contract they need a screen too, Lane 3 and 7 scope nobody cut; left out, the table costs
  Lane 3 its independence and buys nothing. `SameSite`, a lane detail here, decides whether an
  extension can sign in at all, against "on equal terms".
- **Suggested resolution** — Add both to "Not decided here"; put the first to the owner in the
  re-cut with a leaning, contract or command. Prose: a contract test cannot pin an unmade answer.

### 5. "Bump in the next close" is refused by the gate; the root and the retro still say otherwise
- **What** — A close commit moving the pointer after the reports counts as work the pass never saw,
  so the rule as worded makes the PR stale; two statements of the old shape are outside Withheld.
- **Where** — `docs/adr/0001-adopt-the-shared-agent-fleet.md:52-59`; Withheld item 2;
  `scripts/reviews.py:76`, `:152-158`; `scripts/check_prs.py:179`; `scripts/README.md:63`;
  `.claude/agents.local.md:153-154`. Old shape: root `CLAUDE.md:35-36` ("a fleet definition,
  typically"); `.claude/agents/retro.md:139-141`; `scripts/open_work.py:209`, `:228`, `:238`.
- **Why it matters** — The first close to follow the rule is blocked by `hook_stop.py` and failed by
  `check_prs.py`; its way out is a second wave, the cost the owner just ruled out. The digest named
  this (`docs/digests/2026-10-11.md:106`); the answer implies a pointer move is the record, and no
  file says so. The retro still moves the pointer before the fleet PR merges.
- **Suggested resolution** — Code first: `reviews.py` treats the `.claude/agents` gitlink as record,
  with a case under `scripts/tests/` (not Markdown: an agents-board issue, or a second wave here).
  Then the overlay's sentence; root `:35-36` in Withheld; a fleet PR for `retro.md`, or a stated
  exception in ADR-0001's revision, which should also say why it is safe (`docs/CLAUDE.md:35`).

### 6. The withheld merge rule rests on a role no operating file defines
- **What** — "The coordinator merges ready PRs" names a role the root, overlay, fleet manual and
  `scripts/README.md` never define, and "a stated wait" has no number and no one who states it.
- **Where** — PR body, Withheld item 1; root `CLAUDE.md:48` ("this session");
  `scripts/check_prs.py:6-8` ("the one signal the owner merges on", protection "is not configured"),
  not in Withheld though `gh api` confirms protection is on.
- **Why it matters** — The rule moves the owner's only check from before a merge to after it, so who
  holds the merge is what it must get exact. Every lane reads the root: one that thinks it
  coordinates may merge, one that does not leaves ready PRs standing. The ask's five days became "a
  stated wait".
- **Suggested resolution** — Outside the quote, one clause: the coordinator is the session the owner
  is talking to, never a briefed lane; state the wait. Fix the docstring with finding 5's commit.
  Prose: every session acts as one GitHub account, so no check can tell a coordinator from a lane.

### 7. Q-E's answer stops short, and "Still open" misdescribes what is left
- **What** — `docs/08` says only the URL and proxy remain, then lists backups, encryption at rest
  and a signed-out scheduler "the store aside"; lines treating Q-E as one answer still stand.
- **Where** — `docs/08-open-questions.md:19-31`; root `CLAUDE.md:117`, `infra/README.md:10-12` (the
  rig "arrives with" the answer); `.claude/agents.local.md:222-223`,
  `docs/adr/0001-adopt-the-shared-agent-fleet.md:74-75` (`ops` idle until a "public URL"); #14.
- **Why it matters** — Nothing open makes the sibling PC show the backups or encryption the plan
  settles before Lane 8 closes (`impl-director.md:99`). `ops` waits on a URL `docs/07`'s M1 never
  names, while a service and a task come first. The docs are silent on a native service beside the
  Docker development server `infra/README.md:21` puts on the dev PC at port 5432.
- **Suggested resolution** — Change the docs: split the open text into "the URL and proxy" and "what
  the chosen host must still show"; move `ops`'s trigger to the first service on the host; comment
  on #14. Prose: these are statements of status no script can derive.

### 8. The owner's "after M1" has no home on the roadmap or the board
- **What** — The chosen option commits the YouTube Music split and private-session filtering to
  "after M1", but neither `docs/07` nor any open issue carries them; only `docs/02` §8 does.
- **Where** — `docs/02-domain-model.md:675-677`, `:681-682`, `:687-689`; `docs/07-roadmap.md:53-58`;
  `docs/CLAUDE.md:22`; `gh issue list`.
- **Why it matters** — `open_work.py` reads roadmap bullets and issues, so nothing prompts the work.
  M1's "the totals match what the owner remembers" is judged on totals that count private plays and
  lump Music together, a limit stated only in a section about the model.
- **Suggested resolution** — File a product-board issue, which `check_board.py` then holds, asking
  the owner which milestone (leaning M2); add a "Not in M1" line to `docs/07`.

**Decisions**
- Null item with an immutable `event.service`; UUIDv7 keys; Q-E's store on the sibling PC, SQLite
  gone, no ADR; banners dropped; bump in the next close: the owner's, recorded.
- `owner_id` on the log tables: the owner's, recorded. Which tables and what value, sent to the M1
  plan: recorded in §8, absent from Open (2).
- The import set, narrowing "verbatim" by `ip_addr`, M1's totals counting private plays: the
  owner's, recorded; the post-M1 half has no home (8).
- `service` as a fifth column, not a fifth resolved one: recorded; the count is wrong (1).
- Item rank; `auth_session`, its hash and expiry; `RequireSession`: the plan's, recorded as movable.
- Stored sessions over the leaning: the owner's, recorded. An ADR, not a `docs/03` section:
  recorded. Password form, cookie attributes, challenge, to the sign-in lane: recorded. Whether M1
  builds list and revoke, and how a non-browser client signs in: silent (4).
- Remaining host requirements filed under "the URL and proxy": silent (7).
- `CatalogueAdapter`: recorded in `docs/03`; its classing as "not a new decision" is silent (3).
- That a pointer move counts as the record: implied by the answer, silent (5).
- Branch protection; the coordinator merges, the owner reviews by revert: the owner's, recorded in
  the PR body, withheld from the root. Who the coordinator is: silent (6).
- Closes #10 with `Owned`'s docstring lagging; `impl-director.md` not edited: recorded.

**Follow-ups**
- `docs/07-roadmap.md`: Lane 9's plain-format export, which `impl-director-check-2.md` gives the
  session to record as M1 scope, is still absent; stale before this branch.
- `docs/02-domain-model.md:229-231`: no `record_key` form for a Takeout record with no video id,
  which the null item now admits; only `impl-backend-plan.md:126` states one.

**What carried it**
- `docs/digests/2026-10-11.md:106`'s last clause, read against `scripts/reviews.py:76`, when
  checking what "in the next close" would have to pass (finding 5).
