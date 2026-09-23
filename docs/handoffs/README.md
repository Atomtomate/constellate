# Handoffs

One file per finished chunk of work: what was done, how it was verified, what remains
open, what carried it (the agents' "What carried it" lines and the session's own, which
the retro reads), and whatever the next session needs to know that a diff or a PR
description would not tell it. See
[`.claude/agents/CLAUDE.md`](../../.claude/agents/CLAUDE.md#finishing-a-task-report-then-close)
for the convention this directory exists to satisfy.

Not a duplicate of the other places knowledge lives. A PR description argues for a change
to whoever is reviewing it. A memory file carries a standing fact forward across every
future session. A handoff is the narrow thing between the two: a record that *this task*
finished, in what state, and what follows from it.

Named `YYYY-MM-DD-short-slug.md`. Never deleted outright — the closing step (same file,
`#finishing-a-task-report-then-close`) may fold one into the docs it updated once that
content is fully absorbed there, the same way a superseded ADR is marked rather than
removed. The "what remains open" section is that step's input: each item becomes an issue
on the board, or is recorded as not worth one.

## The index is derived, not stored

A stored index table is a file every closing branch edits, and every other branch closing
around the same time edits too, so its merge conflicts come as regularly as the handoffs
themselves (the sibling project's #111). The row lives in the file it describes instead:
directly under a handoff's title, two lines, `**Summary:**` (one sentence) and `**State:**`
(`Open — …` while work continues, `Folded YYYY-MM-DD — …` once the closing step has
absorbed it elsewhere). Both lines are one line each, plain Markdown, file names in
backticks, never a link — `scripts/check_docs.py` resolves every relative link in the
record, and a header must never be the thing that breaks. `scripts/check_docs.py` fails if a
handoff is missing either line or holds a link in one, and holds a handoff to
`record.HANDOFF_CAP` lines; a table that will not fit goes in a file the handoff names.

To see the index, run it rather than read it:

```
python scripts/record_index.py handoffs          # every handoff, oldest first
python scripts/record_index.py handoffs --open   # only the ones still Open
```

On GitHub, the directory's own file list already is an index of a kind: the name carries
the date and the subject, and the first line of whichever file you open is its title.
`record_index.py` exists for the version with Summary and State next to it, which the
file list alone does not show.
