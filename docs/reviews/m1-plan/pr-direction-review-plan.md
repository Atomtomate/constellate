Reviewed at a7cfbe4
(The plan round; no code. The brief's first line, split so `scripts/check_docs.py` reads the sha.)

**Verdict:** Mostly yes. The cut covers M1's bullets in roadmap order, keeps ADR-0003's seam and
the build order, and C1's amendments are reasoned. But Lane 1 would settle two `docs/08` questions
whose deadline is the first migration (the owner column, Q-E's store) without asking. Nothing
plans the host the done-when needs. `event.service` and the owner's answers go unrecorded, and
three M1 obligations have no lane: the plain export, the daily jobs, the spike's fail branch.

### 1. Q-E falls due inside M1, and the plan neither asks it nor stands up a host
- **What** — Lane 1 is the first table migration, and after it ADR-0002's free switch to SQLite
  is gone. M1's done-when needs an unattended host. Q-E is on neither the owner's list nor a lane.
- **Where** — `impl-director.md:17-86`, `:291-296` (Lane 8 "closes with Q-E"), `:298-309`,
  `:360-361`; against `docs/adr/0002-the-stack.md:218-222`, `docs/08-open-questions.md:11-27`
  ("Open until M1 needs it"), `docs/07-roadmap.md:57-58`, `.claude/agents.local.md:217`.
- **Why it matters** — "A week ... with nothing typed" needs Postgres as a service, the task
  registered to run signed out, and encryption at rest if 4e passes. Every lane can close and M1
  still not be done. Lane 6's `date_trunc`-at-zone totals, plus real data, turn ADR-0002's free
  SQLite exit into code changes and a data move.
- **Suggested resolution** — Change the plan. Make Q-E decision 6, with a leaning. Its store half
  ("will the host keep Postgres running as a service?") is settled before Lane 1, the rest before
  Lane 8 closes. Add a session/`infra/` lane that brings the host up, verified by the done-when.

### 2. The first migration answers "an owner column from day one?" by leaving it out
- **What** — `docs/08` asks whether the log needs an owner column *from day one*. Lane 1 is day
  one, and the database plan lists "owner column" under "Not in this plan" with no ask behind it.
- **Where** — `impl-database-plan.md:178`; `impl-director.md:89-131`; against
  `docs/08-open-questions.md:54-55`, `docs/00-vision-and-scope.md:83`, `docs/02:656`.
- **Why it matters** — The root `CLAUDE.md` says to ask before settling a `docs/08` question.
  Once 0002 exists, "no" is fixed, and reversing it means migrating every table: the retrofit
  `docs/08` names as the cost of waiting.
- **Suggested resolution** — Add it to the one message with a leaning (no: one user is the scope
  and `docs/00` defers multi-user), and move the answer to `docs/08`'s Answered.

### 3. `event.service` contradicts three written rules, and decision 3 does gate Lane 1
- **What** — The column is reasoned (check-1, accept 1), but the fold only adds a row to §1's
  table. That leaves `docs/02` saying per-service totals read the item's service and the event
  names no service, ADR-0003 naming four event columns, all resolved, and the overlay's line.
- **Where** — `impl-director.md:44-59`, `:102-108`, `:126-128`; `impl-director-check-1.md:27-31`,
  `:83`; against `docs/02-domain-model.md:87-89`, `:505-509`,
  `docs/adr/0003-the-ingestion-seam.md:55-56`, `.claude/agents.local.md:173-175`.
- **Why it matters** — It is the one event column written once instead of resolved from
  observations, the property ADR-0003 rests on, so a Lane 1 reviewer holding it to these lines
  blocks it. Decision 3 says "none of them blocks Lane 1", yet its null-item half sets 0002's
  shape (`event.service`, nullable `item_id`), so the order can run Lane 1 before the answer.
- **Suggested resolution** — Before Lane 1, ask the owner "null item, hence `event.service`" as
  its own line, beside the database plan's alternative (per-service reads join observation to
  source). The fold rewrites those `docs/02` lines and the overlay's line, and adds a dated note
  to ADR-0003 that `service` is fixed at creation.

### 4. The owner's answers are folded in with the code instead of written down before it
- **What** — Each answer becomes a stale-line fold inside the lane's own PR. Nothing writes
  decisions 1-3 down before Lanes 1, 3 and 4 build on them, and the item rank the plan rules
  "not the owner's" lives only in this review directory.
- **Where** — `impl-director.md:78-86`, `:126-131`, `:181-183`; against the root `CLAUDE.md:133-134`
  ("an ADR or an answered question in `docs/08` first, code second"), `docs/02:632-655`,
  `docs/03-architecture.md:221`, `docs/adr/0002-the-stack.md:234`, ADR-0003's `:77`.
- **Why it matters** — §8 still says "open" while 0002 settles the key type and the null item.
  Sign-in, a security scheme the sibling kept as an ADR, would first appear as a `docs/03` edit
  beside its code. This is the digest's second class: an answer relayed in a session's words and
  later cited as decided.
- **Suggested resolution** — Add a record step before Lane 1: quote and date the answers in
  `docs/02` §8 and close #10; record sign-in as a new ADR or a `docs/03` section before Lane 3;
  write the item rank into `docs/02` §2 as ADR-0003's detail.

### 5. Decision 3's leaning is not what the lanes build
- **What** — The owner is asked to lean "import everything ... Spotify video plays ... since a
  dropped record never returns" and "split YouTube Music ... by `header`". The backend plan skips
  `Streaming_History_Video_*`, and in M1 the split has no column, no filter and no defined step.
- **Where** — `impl-director.md:46-49`, `:56-59`, `:200-204` (4b "split ... by `header`");
  `impl-backend-plan.md:118`, `:25-26`; against `docs/02-domain-model.md:45-47`, `:638-640`.
- **Why it matters** — The owner would answer a leaning the code contradicts. Lane 2 refuses
  before parsing any file whose SHA has an `ok` run, so a record skipped in that file never
  returns: the leaning's own reason. With no column behind it, 4b's "split" invites a new
  `service` or `kind` value outside 0002's checks.
- **Suggested resolution** — Change the plan. Store video plays (null item, counted), or tell the
  owner they are skipped and why. Drop "split" from 4b, or promote `header` in Lane 1 (one column,
  which `docs/02` calls cheap) and ask whether the split belongs to M1.

### 6. The plain-format export is neither in a lane nor out of scope
- **What** — `docs/00` makes "the whole log can be exported, in a plain format, at any time" a
  v1 success criterion, and `docs/02` §4 makes it the long-term copy. No lane builds it, and
  "Not in scope" does not name it.
- **Where** — `impl-director.md:89-296`, `:331-342`; against `docs/00-vision-and-scope.md:99`,
  `docs/02-domain-model.md:425-431`, `docs/08-open-questions.md:18-19`; `docs/07:39-58` is silent.
- **Why it matters** — Once the live tail runs, backups last at most five days, so without the
  export no copy of the log is older than that. That breaks the vision's "kept for years ...
  never dependent on either service" (`docs/00:29-31`), and with the roadmap silent too, nothing
  will build it.
- **Suggested resolution** — Add a small lane (an entry point, no contract change), or name it in
  "Not in scope" with its milestone. Either way, `docs/07` says which.

### 7. Lane 8 schedules the optional poller; the backbone and the daily jobs have no lane
- **What** — Lane 8 is "the poller's scheduled task", gated on 4d. Last.fm's tail (4c), the
  Portability pull (4e) and Lane 5's `videos.list` refresh-and-delete must also fire unattended.
- **Where** — `impl-director.md:291-296`, `:223-231`; `impl-backend-plan.md:167-172`; against
  `docs/02-domain-model.md:344-349`, `:433-440`, `docs/08-open-questions.md:23-25` ("with the
  daily jobs beside it"), `.claude/agents.local.md:187` ("Nothing depends on the poller").
- **Why it matters** — If the owner never registers the Spotify app (#13), the lane that
  schedules the backbone never opens. Once Lane 5 stores Data API rows, a 30-day delete run only
  by hand breaks YouTube's policy, a retention invariant the reviewers enforce.
- **Suggested resolution** — Gate Lane 8 on 4c and list every command it registers (poll,
  enrich, the Portability pull). Close Lane 5 only once its job is scheduled.

### 8. If the spike fails, the done-when's YouTube half fails, and the plan rules out the fix
- **What** — "Not in scope" rules the extension out entirely, though `docs/00` defers it only if
  #11 passes. If the spike fails, scheduled Takeout is a hand download up to two months late.
- **Where** — `impl-director.md:70-74`, `:334-335`; against `docs/00-vision-and-scope.md:79`,
  `docs/01-data-sources-youtube.md:189-193`, `:336`, `docs/07-roadmap.md:57`.
- **Why it matters** — Then "a week of real ... watching in the log with nothing typed" cannot
  hold, and the YouTube document says the extension's case for M1 is stronger. The plan again
  rules out the option consolidate-m0's direction review (finding 1) got `docs/00` to keep open.
- **Suggested resolution** — Make the "Not in scope" line conditional on #11 passing. Say in
  decision 5 that a fail puts Q-F (the extension in M1), or an amended done-when, to the owner.

### 9. A second source protocol is decided in a specialist plan and recorded nowhere
- **What** — Lane 5's `sources/youtube_data_api.py` sits behind a new `CatalogueAdapter` that
  yields facts, not drafts. The director's Lane 5 does not name it, and the standing constraint
  and `docs/03` say every source produces the draft event.
- **Where** — `impl-backend-plan.md:167-172`; `impl-director.md:223-231`; against the root
  `CLAUDE.md:140-141`, `docs/03-architecture.md:62-66`, `:85`, `api/src/constellate/CLAUDE.md`.
- **Why it matters** — A reviewer will read it as a second write path past a standing constraint.
  Or the next catalogue source (Spotify's `GET /tracks`) copies it with no written rule: that it
  writes only the cache, through the one cache write.
- **Suggested resolution** — Record it in a sentence in `docs/03`'s `sources/` row and "One
  ingestion path": a catalogue-only source has its own protocol and writes only the cache.

**Decisions**

- Key type, sign-in, §8 imports: put to the owner; no record home (4); leaning vs lanes (5).
- Null item, hence `event.service`: reasoned, folded into decision 3, docs not rewritten (3).
- No owner column in 0002: silent (2). Postgres kept before Q-E, no host lane: silent (1).
- Item precedence order (export first, Last.fm last): recorded only in the plan (4).
- Spotify video plays skipped: silent (5). Music/private-play filters out of M1: recorded (5).
- Plain export left out (6); Lane 8 without the daily jobs (7); extension out even on a failed #11
  (8); `CatalogueAdapter` (9): silent.
- `spotify:show-name` creator ref: backend plan only; `docs/02:135-137`'s list should gain it.
- Matching in `domain/`, span read in `repos/`, re-sourcing in Lane 2, `SourceAdapter` from all
  sources; three `/totals` paths, top-N with no cursor (a `docs/03` note); `local_date` and
  `/me.time_zone`; importers as commands; Last.fm credit in Lane 7; `Health` screen retired;
  phone-first; ISRC merge in Lane 5; sampler at 30 s / 3 min: recorded.
- The backend lane regenerates `schema.d.ts`: recorded; the overlay already says so.

**Follow-ups**

- `impl-director.md:329` says "(friction filed)" for the codegen gap; none is in `docs/friction/`,
  and `.claude/agents.local.md:73-77` already has the changing lane commit both files.
- `.claude/agents.local.md:42` still says `extension/` "if Q-D calls for one", though Q-D is
  answered (consolidate-m0 direction, finding 5).

**Friction**

- The brief's first line does not match `scripts/reviews.py`'s `REVIEWED_AT`, so `check_docs.py`
  fails a report that opens with it; I split it in two. I wrote no note, because the brief
  confines writes to `docs/reviews/m1-plan/`.

**What carried it**

- `docs/08`'s Q-E and "Smaller, for later", read against the database plan's "Not in this plan":
  "before the first migration" and "from day one" both fall on Lane 1 (findings 1 and 2).
