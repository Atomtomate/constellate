# A fix-round brief that names a lane plan that does not exist and a tree that is not clean
**Agent:** the session-docs and impl-database lanes of the scaffold's second and third fix rounds (workflow subagents), and the session-docs lane of the first; filed by the session from their returned friction text
**Summary:** a reconstructed scope, an exact-match edit script aborted on anchor drift, and three session-owned files edited by specialists, each because the round's brief stated the tree and the lane's plan as facts a lane could not verify were true
**Retro:** Unprocessed

## What you were doing

Acting on plan-critic findings on branch `claude/scaffold`, in a workflow whose fix stage
ran one agent per lane in parallel on the same worktree, each brief written by the
coordinating session from a template shared by every lane.

## What happened

Three things, each lane's words quoted.

The brief's READ block told every lane to read "your own plan
`docs/reviews/scaffold/<your-lane>-plan.md`". The session-docs lane: "The lane brief pointed
at `docs/reviews/scaffold/<your-lane>-plan.md`, which does not exist for session-docs (only
the three specialist plans do); the session's scope had to be reconstructed from
`impl-director.md`'s 'Session' bullet."

The third round's brief said "the tree is clean — the whole scaffold is committed", true when
the brief was written and false the moment four lanes started writing. The impl-database lane:
"The worktree was NOT clean when I started, contrary to the brief ... harmless since the lanes'
files are disjoint from mine, but a brief that says 'the tree is clean' is a claim to verify
with `git status` before trusting the diff." The first round's session-docs lane paid for the
same thing differently: "Other lanes edited three files in my lane between my read and my
write, so an exact-match replacement script aborted mid-run on anchor drift."

And the first round's session-docs lane reported that the specialists had edited
session-owned files to match their own code fixes — `api/CLAUDE.md`, `api/tests/CLAUDE.md`,
`api/src/constellate/CLAUDE.md` — "outside the ownership map's 'the CLAUDE.md files are the
session's'". The edits were right and were kept; the map was crossed without anyone deciding
to cross it.

## What it cost

One reconstructed scope; one aborted edit script and the turn to re-run it; a crossing of
the ownership map that only surfaced because the lane that owned the files said so. No
finding was lost.

## What would remove it

In the coordinating session's fix-round template, not in a definition: say "the tree is clean
at `<sha>`; other lanes write beside you from now on, so `git status` is the truth and the
diff against `<sha>` is yours only where the ownership map says so", and name the plan file
only for the lanes that have one. For the map crossing: a fix-round brief should say what a
specialist does when its code fix makes a session-owned `CLAUDE.md` sentence false — report
it in `notes_for_others`, never edit it — since the ownership map's prose row is a rule the
specialists' definitions do not quote.
