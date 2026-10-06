# A long quoted heredoc fails to parse in the Bash tool, and nothing in the call runs
**Agent:** the session-docs lane of the scaffold's first fix round (a workflow subagent), and the coordinating session itself; filed by the session from the lane's returned friction text
**Summary:** two turns and one aborted chain of commits-plus-push-plus-PR, because a quoted heredoc past a few kilobytes of prose with backticks and apostrophes is a parse error for the whole call
**Retro:** Unprocessed

## What you were doing

The lane: fixing plan-critic findings in the five `CLAUDE.md` files of the scaffold branch
`claude/scaffold`, passing a multi-kilobyte Python replacement script to the Bash tool through
a quoted heredoc. The session: committing the third fix round, pushing, opening PR #9 and
writing the reviewer briefs in one chained Bash call, with the PR body in a `cat > file
<<'EOF'` heredoc of about four kilobytes.

## What happened

The lane, in its own words: "A long Python script passed to the Bash tool through a quoted
heredoc failed to parse in Git Bash ('unexpected EOF while looking for matching quote')
although the delimiter was quoted and alone on its line; writing the script with the Write
tool and running it with Bash worked first time — the auto-mode preference for heredocs over
Write does not hold for multi-kilobyte scripts containing backticks and apostrophes."

The session: `/usr/bin/bash: -c: line 73: unexpected EOF while looking for matching `''`.
Bash parses the whole `-c` string before running any of it, so the four commits chained ahead
of the heredoc had not happened either; `git log` had to be checked before anything was
assumed to have landed.

## What it cost

One turn each time to notice and re-issue the work through the Write tool, and for the
session the risk of believing the commits existed. The same trap bit twice in one day in two
different agents, which is the evidence it recurs.

## What would remove it

The auto-mode instruction that prefers Bash heredocs over Write for file changes is the
harness's, not this repository's, so no file here can fix the cause. What this repository can
say is in the root `CLAUDE.md`'s "Environment gotchas": one bullet that a quoted heredoc is
for a paragraph, and a PR body, a handoff, a friction note or a script of more than a
kilobyte or two goes through the Write tool and then `--body-file` or `python <file>`.
