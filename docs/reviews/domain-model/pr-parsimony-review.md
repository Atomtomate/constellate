Reviewed at 65e93951b0ee

**Verdict:** The model's shape is about right for what it answers. The record, though, states
its rules more than once. ADR-0003's Decision is told again in model §2 and §8, and §4's Spotify
rules are told at two to four sites each. About 50 of the 854 lines are second copies, one pair
has already drifted, and each of the first wave's fixes has to land two to four times.

### 1. ADR-0003's Decision is told again in model §2 and §8, and one copy has already drifted
- **What** — §2 restates the precedence (`:237-245` = ADR `:69-73`), the matching (`:230-233` =
  `:63-68`), the cursor (`:208`, `:256-258` = `:76-77`) and closed plays (`:194-195` = `:77-78`).
  §8.1 `:583-589` restates the Alternatives, and ADR `:145-149` restates §3. `dd4b061` cut the
  playlist context from the upsert alternative (direction-review 2), but model `:588` still has it.
- **Why it recurs** — tech-review 1, 3 and 5 each cite both files, so each fix is two edits, and
  every ADR drawn from a doc (Q-D, Q-E) copies the shape. `docs/CLAUDE.md` keeps prose "only
  where it argues something the ADR does not", and ADR `:85-86` lists what §2 is to hold.
- **The smaller version** — §2 keeps the draft table, key formats, matching table and cursors,
  and cites the ADR for the rules. The ranks live in one file: the model's, if they are tuned
  like the windows, as `:609` says (ADR `:67-68` says only the windows are). §8.1 and ADR
  `:145-149` become one-line citations. A `check_docs.py` count of 8-word runs shared with an
  Accepted ADR's Decision finds 22 here (`:98`, `:208`, `:233`, `:237-245`). It misses paraphrase
  (`:230`, §8.1), which is left to the existing prose rule, since no count can tell it apart.
- **Net effect** — about 12 lines from the model and 8 from the ADR. Each seam rule has one home.

### 2. Inside the model, rules are retold beside the "(§N)" pointer that already names their home
- **What** — The Spotify API-plays deletion, owned by §4 `:386-392`, is retold at `:98-100` and
  `:249`. §4's `:393-396` retells §1 `:115-116`, `:134-136` and §3 `:300-303`, so "artist URIs
  come only from the API" is said three times. §4's table `:325-331` retells the bullets below it
  cell by cell, and §8 `:605-608` retells the readings §4 `:403-408` leaves open. The Basis
  table's "From" column (`:74-76`) repeats the Source table's "Gives" column (`:150-156`).
- **Why it recurs** — every first-wave fix here lands at two or three of these sites: tech-review
  2 (`:328`, `:330`, `:377-385`), 3 (`:98`, `:249`, `:386`) and 4 (`:115`, `:393`), and
  direction-review 3 (`:403`, `:605`). Each source §6 foresees adds a row to both tables.
- **The smaller version** — keep the pointer and drop the retelling. `:98-100` ends "or where its
  source's terms require it (§4)". Cut `:249`'s deletion sentence, `:393-396`, the §4 table and
  the "From" column. §8's entry becomes "Spotify's terms: the readings §4 leaves open". Prose, not
  a check: a count cannot tell a retelling beside a pointer from a summary, and root `CLAUDE.md`'s
  "a rule stated twice" already covers it.
- **Net effect** — about 17 lines. Each §4 rule is one edit, and a new source is one table row.

### 3. The handoff retells the model a third time
- **What** — `docs/handoffs/2026-09-23-domain-model.md:10-22`, "The model in one line each",
  retells the model's own "The model in brief" (`docs/02-domain-model.md:14-36`) and the PR
  body's "The model".
- **Why it recurs** — `docs/handoffs/README.md` limits a handoff to what "a diff or a PR
  description would not tell". The consolidation PR works from this handoff (direction-review 4).
  If the bullets are not updated to match the fold's corrections (tech-review 2,
  direction-review 2), the answered Q-C entry in `docs/08` would copy stale rules from them.
- **The smaller version** — "`docs/02-domain-model.md`, the brief's eight sections, summarised
  in its own 'The model in brief'." No new rule is needed: the README already says this.
- **Net effect** — about 11 lines. Once the fold edits the model, the handoff is still true.

**Follow-ups**
- `docs/02-domain-model.md` §7 and §1's "Fields:" sentences will copy M1's first migration. That
  PR should delete §7 and have §1 point at the schema.
- The consolidation PR's two standing constraints in root `CLAUDE.md` should be the rules' one
  statement, with model §3 and §4 citing them. ADR `:148-149`'s "Reversing it would take an ADR"
  already restates root `CLAUDE.md:118`.

**What carried it** — `git show dd4b061` beside model §8.1. The acceptance commit edited the
ADR's upsert alternative and left the model's copy at `:588`, so the two copies no longer agree.
