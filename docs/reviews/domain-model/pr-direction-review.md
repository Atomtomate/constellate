Reviewed at 65e93951b0ee

**Verdict:** Mostly yes. The change answers Q-C as M0 asks, but it builds on a stack acceptance
nothing records, adds a deletion the owner has not accepted, and uses superseded Spotify research.

### 1. ADR-0003, Accepted, rests on a stack acceptance nothing in the repo records
- **What** — ADR-0003 and the model say the owner accepted the stack ADR's option A.
  `0002-the-stack.md` on #1 still says `Status: Proposed`, #1's body says accepting it "is a PR
  of its own", and #4's body allows merging the two "in either order".
- **Where** — `docs/adr/0003-the-ingestion-seam.md:9`, `docs/02-domain-model.md:6` (and §2, §7);
  `docs/adr/0002-the-stack.md:3` on `origin/claude/stack-adr`; root `CLAUDE.md:123`;
  `docs/CLAUDE.md:46` ("Citing an ADR that does not contain the decision").
- **Why it matters** — merged first, `main` has an Accepted ADR whose premise is a file that is not
  in the tree. Merged second, it cites a Proposed ADR as accepted. `check_docs.py` passes both
  ways, because the name is in backticks, which `ADR_MENTION` never sees.
- **Suggested resolution** — record the acceptance in `0002-the-stack.md` (Status, date, by whom)
  and make #4 "merge after #1". Then add a check: `check_adrs` counts a backticked `NNNN-*.md`
  as a mention, and fails an Accepted ADR that names an ADR that is not Accepted.

### 2. The amendment adds a deletion to a Decision the owner accepted "as proposed"
- **What** — the acceptance commit `dd4b061` also changed the ADR. It added to the Decision that
  Spotify Web API observations are deleted once the export joins their event, and on
  disconnect. It also cut "the poller's playlist context" from the upsert alternative's reasons.
  Its own note says "The owner accepted the decision as proposed".
- **Where** — `docs/adr/0003-the-ingestion-seam.md:79-83`, `:120-131`, `:162-164`; model §4
  `:386-401`, `:414-415`; root `CLAUDE.md:18`; `docs/00-vision-and-scope.md:28`.
- **Why it matters** — this deletion is the one step no recompute can undo (the ADR's own `:122`).
  It rests on a reading Spotify §6 marks as inferred, and it makes the log depend on Spotify
  re-supplying plays after a disconnect, which bends 00's "never dependent". The header reads as
  if the owner accepted all of it.
- **Suggested resolution** — ask the owner about the deletion as a separate question, with a
  leaning, and record the answer next to `Accepted:`. Restore the removed reason, and say in the
  amendment why it no longer applies. Prose: a script cannot count whose consent a clause had.

### 3. The Spotify half used §6 at `3623499`; #3's tip now recommends a path the model skips
- **What** — `ec00a85` on #3, two minutes before the fold, reads Policy §III as plausibly
  covering this tracker. It recommends export plus Last.fm with no Spotify app "for zero
  Spotify-terms risk", and names Last.fm in "What the domain model may assume". The model
  mentions no Last.fm and calls both clauses merely open.
- **Where** — `docs/02-domain-model.md:403-408`, §6, `:605-608`;
  `docs/adr/0003-the-ingestion-seam.md:63-68`, `:100-101`; `docs/01-data-sources-spotify.md:564`,
  `:632`, `:641` on `origin/claude/spotify-data-source`; handoff `:8-9` names the tips it read.
- **Why it matters** — a scrobble has names but no URI and no duration. ADR-0003 matches on "the
  same item ref" and falls back to names only for relinked Spotify tracks, so a scrobble and its
  export row would become two events. The promise that a new source is "an adapter, a source
  row and its place in the precedence order" fails for the source the research proposes.
- **Suggested resolution** — add Last.fm to §6 and say how a name-only observation matches (an
  ADR-0003 amendment if matching widens); list the API-or-zero-risk choice in §8. Prose: a
  script cannot count what a design covers.

### 4. The deferred updates stop one file short, and the handoff's list stops two more short
- **What** — `docs/07-roadmap.md:24`'s M0 bullet stays open once the doc exists, and nobody names
  it. The handoff's consolidation item names `docs/08` and root `CLAUDE.md`. It leaves out the
  overlay's "**not yet written** (Q-C)" and "None decided", and Q-E's requirements from §4.
- **Where** — `docs/handoffs/2026-09-23-domain-model.md:40-42`; `docs/07-roadmap.md:24`;
  `.claude/agents.local.md:75`, `:131-133`; `docs/08-open-questions.md:56-60` against
  `docs/02-domain-model.md:345-347`, `:352-354`, `:400-401`.
- **Why it matters** — the consolidation PR works from the handoff, so what it leaves out stays
  stale. Reviewers keep holding changes to scope alone. Whoever answers Q-E reads `docs/08`, and
  could pick backups that keep the cache past 30 days, or a host without encryption at rest.
- **Suggested resolution** — mark `docs/07:24` done here. Add the overlay lines and Q-E's three
  requirements to the handoff's consolidation item. Prose: a script cannot say which sentence
  a model makes untrue.

**Decisions**
- One event per play from immutable observations, by per-column precedence — recorded (ADR-0003).
- `record_key` from the upstream record, shared by Takeout and Portability — recorded (ADR-0003).
- Match on item ref in per-pair windows, one lock per service — recorded (ADR-0003).
- Spotify API observations deleted on re-sourcing and disconnect — recorded, owner's consent not.
- No item merging across services — recorded (owner; ADR-0003, §3); the constraint is deferred.
- Merging within a service on ISRC — recorded as the model's proposal (§3).
- Catalogue facts are a cache, never a log column; 30 days read as "kept current" — recorded (§4).
- Cache in its own schema, outside long-lived backups; backups re-cut on disconnect — §4 only.
- The stack is option A of the stack ADR, on Postgres — silent: no document records acceptance.
- The Spotify Web API capture plan over the export-plus-Last.fm path — silent.
- Titles from the owner's records; album in `detail`; creator not an item — recorded (§1, §3).
- A favourite is a row, not a flag; atlas tables point at the log, never back — recorded (§5).
- An event may have no item — recorded (§1), open in §8.

**Follow-ups**
- PR #4's title and body still say ADR-0003 is Proposed and allow merging "in either order".
- `scripts/review_briefs.py` names the repository "the board-game-tracker repository".

**What carried it** — the handoff names the tip it read (`3623499`); diffing it showed finding 3.
