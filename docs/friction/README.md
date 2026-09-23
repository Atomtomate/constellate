# Friction notes

One file per time the *process* failed an agent: the definition it ran under was wrong or
had to repeat itself, a tool or command fought back, a document had to be worked around,
or a "what not to report" exclusion made it drop something it believes is real. The agent
writes the note itself, at the end of its task, and nobody reads it until the next
`retro`. Why the channel exists, and how it differs from the follow-ups an agent
recommends in its report, is
[`.claude/agents/CLAUDE.md`](../../.claude/agents/CLAUDE.md#three-channels-beyond-the-findings)'s
to say.

Not a duplicate of the other places an observation can go. A finding goes in the report,
because it is what the task was for. A follow-up goes in the report, because it is about
the project and the calling session should decide now. A friction note is the narrow thing
left over: it is about how the work went rather than what it produced, it is nobody's
task, and it would be lost when the context ends.

## What a note contains

Evidence, not sentiment. Four things, as headings or in prose, in this order:

- **What you were doing** — the definition you ran under, the task, PR or branch, and the
  step you were on.
- **What happened** — the instruction that was wrong, quoted; the command that failed,
  with its output; the exclusion that stopped you, and in one line the thing it stopped.
- **What it cost** — turns, a wrong guess, a finding dropped. A note that cannot name a
  cost is not friction.
- **What would remove it** — the edit, to which file, as concretely as you can; or that
  you do not know.

Name files in backticks rather than linking them. `scripts/check_docs.py` walks this
directory too, and a relative link that does not resolve fails CI.

Above that, three more lines the header contract fixes: the title (`# <title>`), then
directly under it `**Agent:**` (who filed it), `**Summary:**` (what it cost, one sentence)
and `**Retro:**` (its outcome, starting `Unprocessed`, `Applied`, `Declined`, `Resolved`
or `Filed` — see below). All three are one line each, plain Markdown, file names in
backticks, never a link, for the same reason as the body. `check_docs.py` fails if any of
the three lines is missing, holds a link, or gives Retro a word outside that list.

## What is not a friction note

Saying what not to file matters more than saying what to file: without it every agent
files a grumble every run, and the signal dies.

- **Anything about the project's code or docs.** A bug, a stale sentence, a missing test
  is a finding if it is in your scope and a follow-up in your report if it is not. Never
  a note.
- **A cost the next agent will not pay.** The test is "would the next run of this
  definition hit the same thing?" A one-off — the network was down, the PR was unusually
  large — is not friction.
- **Something you were told where to find.** Hitting a gotcha the root `CLAUDE.md` names,
  after the definition told you to read it, is not the definition's fault.
- **The task being hard.** Difficulty is not friction; a wrong or missing instruction is.
- **A finding in disguise.** Do not use a note to report what your scope told you not to,
  in the hope someone acts on it. Say that the exclusion made you drop it, in one line —
  that is the evidence the retro needs to judge whether the exclusion is right — and stop.

A second note about the same friction is not a duplicate; it is evidence that it recurs.
File it, and name the earlier one.

## Naming, and what happens to a note

`YYYY-MM-DD-short-slug.md`, one file per note, so two agents running at once never write
the same file. A note whose `**Retro:**` line still starts `Unprocessed` is unprocessed,
and that is the normal state of a new one — the queue is the directory, and
`scripts/open_work.py` lists it, together with the notes git holds off `main` on a branch
or in another worktree. A note written by a subagent lands in the calling session's
checkout as an untracked file; that session stages it by name and commits it with whatever
PR it is working on, and the note reaches `main` when that PR merges.

The `retro` reads every unprocessed note and does one of four things: applies it (an
agent definition, a `CLAUDE.md`, a script), turns it into an issue (the note implied real
work, which the closing step may also do sooner), files it as a research question (the
note's *what would remove it* is "I do not know", and nobody here knows either — an issue
labelled `research`), declines it, with the reason, or finds work since already removed it
(`Resolved`). Whichever it was, the retro rewrites that one note's own `**Retro:**` line to
say so — never a table, so two edits to different notes cannot collide. The file stays:
marked rather than deleted. The rest of the note is never edited. It is the agent's
testimony; the `**Retro:**` line is the retro's verdict — and a later retro may correct one
that later work proved wrong, rewriting that line only and saying so in its handoff.

**The owner may direct that a note be acted on in the session that found it**, rather than
left for the next retro. That session then does one of the same four things and rewrites the
same one line, saying in it that it was the session and at whose direction. This is the
exception and not a second route an agent takes on its own judgement: the reason a note
normally waits is that the retro sees recurrence across runs, where a single session sees
one incident and will generalise from it too readily.

## The index is derived, not stored

The Agent/Summary/Retro row lives in the note itself, in the header above, for the reason
`docs/handoffs/README.md` gives. To see the index, run it rather than read it:

```
python scripts/record_index.py friction          # every note, oldest first
python scripts/record_index.py friction --open   # only the ones still Unprocessed
```
