Reviewed at 6e8c8a387ade

**Verdict:** Mostly. It closes M0 and slots the calendar as the owner directed, but it records two
choices that no dated owner decision covers (YouTube's capture paths; M3's feeds and band list),
narrows `docs/02` inside a standing constraint, cites three rules to ADRs that do not contain them,
and leaves `docs/03`, `docs/02`'s banner and the overlay's extension row calling Q-C and Q-D open.

### 1. YouTube's half of Q-D is recorded as the owner's answer, with no owner decision behind it
- **What** — `docs/00` attributes every capture path to "the owner's answers to Q-D (2026-09-23)"
  and defers the extension unconditionally, but the owner-decision lists cover Spotify's paths only;
  YouTube's are the research's recommendation, which makes the extension depend on the spike.
- **Where** — `docs/00-vision-and-scope.md:55-56`, `:65-68`, `:81`;
  `docs/08-open-questions.md:78-90`; `CLAUDE.md:10-14`; against
  `docs/handoffs/2026-09-23-coordinator-wind-down.md:28-37`, `docs/02-domain-model.md:629-631` and
  `docs/01-data-sources-youtube.md:3-5`, `:329-337`.
- **Why it matters** — if spike #11 fails, scheduled Takeout cannot meet `docs/00`'s own "in the log
  by the next morning" (`:97`), and the YouTube document says the extension's case for M1 is then
  stronger; the out-of-scope row closes that branch without anyone having chosen to close it.
- **Suggested resolution** — if the coordinator's brief relayed the owner's acceptance of YouTube
  §6, cite it with its date in Q-D's entry; otherwise say at `docs/00:55` that YouTube's paths are
  the recommendation pending #11, and make the extension row conditional on the spike, as Q-F is.

### 2. M3's bullets and done-when settle the calendar idea's open questions
- **What** — the owner decided the slot, scraping and the Proton and Google subscription, but M3
  also commits to Ticketmaster, TMDB, Steam and IGDB, to "the bands among the atlas's favourites",
  and to a done-when on "a favourite band": the idea's leaning and its open questions 2, 3 and 6,
  which it calls "Recorded, not resolved" and says "decide the shape".
- **Where** — `docs/07-roadmap.md:87-92`; `docs/ideas/concert-and-release-calendar.md:18`,
  `:235-237` (IGDB "once the terms question is settled"), `:266-284`; owner decision 5 in
  `docs/handoffs/2026-10-06-coordinator-handoff.md:31-43`.
- **Why it matters** — `docs/CLAUDE.md` calls the roadmap "what we committed to build"; an M3 brief
  builds these feeds and this band list as decided, though the owner chose neither and IGDB's
  storage terms are unread.
- **Suggested resolution** — change the doc: M3 names what the owner decided (the hand-typed
  calendar, the ICS feed, then feeds) and points at the idea's questions 1-3 and 6 for which feeds
  and which bands; the done-when waits on the answer to question 2.

### 3. A new standing constraint forbids the stand-in title `docs/02` specifies
- **What** — the constraint ends "titles and names come from the owner's own records" with no
  exception, while `docs/02` titles a track from the Web API or Last.fm until the export names it,
  and §4 puts Last.fm's scrobbles outside "the owner's own records".
- **Where** — `CLAUDE.md:137-140`; `docs/02-domain-model.md:114-118`, `:288-292`, `:319-324`.
- **Why it matters** — Last.fm is the live tail, so every play since the last export rests on a
  stand-in; #12 is built against a constraint that outranks `docs/02` ("changing one needs an ADR"),
  so a reviewer blocks it or its implementer moves titles where the model never put them.
- **Suggested resolution** — change the constraint: "... from the owner's own records, save the
  stand-in a live source gives until the export names it (`docs/02` §1)".

### 4. Three rules in the diff cite an ADR that does not contain them
- **What** — Q-E cites ADR-0002 for the poller as "a bounded sampling run (the owner, 2026-09-23)",
  which ADR-0002 leaves "the owner's to confirm", and ADR-0003's amendment for five-day backups,
  which it never mentions; the checklist files Last.fm's re-sourcing under ADR-0003's "where their
  source's terms require it", though Last.fm's terms require deletion only on termination.
- **Where** — `docs/08-open-questions.md:18-20`, `:23-26`; `.claude/agents.local.md:162-165`; issue
  #13; against `docs/adr/0002-the-stack.md:254-255`, `docs/03-architecture.md:33-37`,
  `docs/adr/0003-the-ingestion-seam.md` (Decision, last bullet), `docs/02-domain-model.md:420-422`.
- **Why it matters** — `docs/CLAUDE.md`'s first trap: a citation that looks reviewed. The sampler's
  confirmation survives only in a folded handoff ("stated to the owner without objection"), and the
  checklist has reviewers enforce `docs/02`'s deletion as if the Accepted ADR allowed it.
- **Suggested resolution** — a dated revision note in ADR-0002's Consequences confirming the shape
  and its basis, with `docs/03:33-37` following; cite `docs/02` §4 alone for backups; amend
  ADR-0003's deletion rule to cover re-sourcing a live play, or have `docs/02` keep the scrobbles.

### 5. Answering Q-C and Q-D stopped one file short of the docs that still call them open
- **What** — `docs/03` still lists Q-C and Q-D under "Not decided here" and draws the extension "if
  Q-D needs one" beside a poller whose only source is the now-optional Web API; the overlay gives
  `extension/` "if Q-D calls for one"; `docs/02`'s banner offers the model "for the owner to accept
  or correct", built on "documents on open pull requests".
- **Where** — `docs/03-architecture.md:11-20`, `:41-42`, `:116-119`; `.claude/agents.local.md:43`;
  `docs/02-domain-model.md:3-10`. PR #9 rewrites none of these lines.
- **Why it matters** — `docs/03` is "the standard a change is held to" and M1's lanes start there;
  an agent reading it waits on questions this PR closed. The banner leaves unsaid whether the model
  beyond its two owner-decided parts is accepted, which `docs/08`'s Answered entry now implies.
- **Suggested resolution** — change the docs here: `docs/03`'s shape and "Not decided here" point
  at the Answered entries; the overlay row says the extension comes later (Q-F); `docs/02`'s banner
  says what the owner decided and that `docs/08` records Q-C answered.

### 6. Q-E's host requirements omit the public URL the PR itself derives
- **What** — the idea file now says Proton and Google fetch the feed from their own servers, so its
  URL is "a requirement on the host Q-E chooses", but Q-E's list of "what the decisions so far
  require" does not carry it.
- **Where** — `docs/ideas/concert-and-release-calendar.md:157-159`;
  `docs/08-open-questions.md:11-26`.
- **Why it matters** — Q-E is answered when M1 needs it, from that list; a LAN-only host chosen then
  blocks M3's done-when, and the requirement sits in an idea file nobody choosing a host opens.
- **Suggested resolution** — add a bullet to Q-E: from M3, a feed URL reachable from the internet,
  for the owner's 2026-10-06 subscription decision.

### 7. An idea the roadmap holds but has not adopted has no place in `docs/ideas/CLAUDE.md`
- **What** — the idea stays `shaped` and splits its checklist's Decision line, reasoning that "an
  idea moves one status at a time", while `docs/ideas/CLAUDE.md` defines `adopted` as "Promoted to
  the roadmap", which M3 now is.
- **Where** — `docs/ideas/concert-and-release-calendar.md:2`, `:23-24`, `:31-33`;
  `docs/ideas/CLAUDE.md:87`, `:101-103`; `docs/ideas/_template.md` (one Decision line).
- **Why it matters** — the convention moved in one idea file only; the next idea the owner slots
  meets the same two rules in conflict, and `docs/ideas/CLAUDE.md` says a changed convention is
  changed there "in the same commit".
- **Suggested resolution** — change `docs/ideas/CLAUDE.md` and the template: say what an idea in the
  roadmap before `speced` is, or that a slot is adoption and the idea moves to `adopted`.

**Decisions**

- Q-C answered by `docs/02` and ADR-0003 — recorded for the owner's two parts; the rest silent (5).
- Q-D's Spotify half as the owner chose it — recorded (2026-09-23; Premium 2026-10-05).
- Q-D's YouTube half, and the extension deferred unconditionally — silent (1).
- M0 done 2026-10-05; M1 restated, the scaffold first — recorded (the briefs; wind-down handoff).
- The calendar as M3, constellations M4, the apps M5 — recorded (the owner, 2026-10-06).
- M3's feeds, band list and done-when — silent (2).
- The idea kept `shaped` while on the roadmap — recorded in the idea, against its convention (7).
- Public pages scrapable for the feeds; the feed subscribable from Proton and Google — recorded.
- Two standing constraints — recorded (ADR-0003; owner approval); the title clause silent (3).
- The overlay's checklist as a derived copy — recorded in its section; one citation wrong (4).
- The poller as a bounded sampling run — recorded only in a folded handoff; cited to ADR-0002 (4).
- Q-E's host requirements — recorded, without the public feed URL (6); Q-G opened — recorded.
- Branch protection undecided; the `docs/ideas/` row withheld — recorded (handoff, PR body).
- The two script fixes; six handoffs folded into issues #11-#18 — recorded.

**Follow-ups**

- `docs/01-data-sources-spotify.md:31-34` and §5 (`:367-406`): the recommendation and the owner's
  steps (Last.fm "optional insurance", the tracker's own `recently-played` poll, "say whether the
  account has Premium") predate the owner's 2026-09-23 choice and carry no note of it.
- `docs/ideas/concert-and-release-calendar.md:2` against `:18`: `shaped` means "Ambiguity resolved"
  (`docs/ideas/CLAUDE.md:85`) while the file leaves that box unchecked, since PR #6.

**What carried it**

The two coordinator handoffs' numbered "Decisions the owner took" lists, held against every "the
owner, <date>" and "the owner's answers" the diff writes: what the lists lack is findings 1 and 2.
