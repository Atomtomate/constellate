"""Print the four reviewers' briefs for a branch, so a brief never re-scopes a reviewer.

A brief written by hand is where a reviewer gets pointed at prose its definition excludes, or
at a report path in another worktree — two friction notes on 2026-09-14 alone. What a brief
may carry is fixed here: the branch and PR, the worktree and its head, the PR's base (read
with gh; `--base` when gh cannot answer), one paragraph on what the branch is, the diff
measured, what the caller reports (the first wave's findings, by report path, for the second
-- a verification claim in it is the branch's own account, since one such claim was false and
would have cost a finding), the report path the overlay's rule derives, the report's shape and
cap (`reviews.py`), and the remedy order. The axis is the definition's; the brief never states
one, and a session that wants to say more says it in the "what" paragraph, which describes
the diff, not the reviewer.

The remedy order is the owner's, given mid-review on PR #152 on 2026-09-14 — "I want this to
be blocked by the python program … the least amount of agent instructions and the strictest
rule set on program bases". It says what a finding may *recommend*, never what to look for, so
it is a slot like the others rather than an axis. It is here because this is the one place
every brief passes through: a reviewer left without it recommends "document this", which is
the remedy that direction rejects, and the session that first hand-delivered it crashed before
it was written down anywhere (#169).

    python scripts/review_briefs.py --branch claude/x --pr 123 --worktree C:/wt/x \\
        --what what.md [--known known.md] [--base BRANCH] [--out DIR] [--since SHA]

Prints the four briefs to stdout, or writes DIR/<agent>.md with --out. `--since` briefs a
second wave over the commits after the head the first wave read. Exits 1 only when the PR's
base could not be read and none was given.
"""

from __future__ import annotations

import argparse
import gh_json
import report
import subprocess
import sys
from collections import Counter
from pathlib import Path

import git_cmd

import reviews

BRIEF = """\
Review branch `{branch}` (PR #{pr}) of the board-game-tracker repository. Your definition says \
what you look for; this brief says only where, and what is already known.

{where} Do not `cd` to the main checkout. Edit no file but your report, and commit nothing. \
Other reviewers may be running in this worktree; their reports under `{report_dir}/` are not \
part of the diff.

What the branch is, as the caller describes it:

{what}

What the branch is, measured:

{census}

What the caller reports (a fact about the repository is cheap to take; a claim about what the \
branch verified is the branch's own account, and you re-run one a finding would turn on):

{known}

Where a finding needs a remedy, recommend the strongest one that can carry it, in this order: \
code that makes the mistake impossible, then a test that fails when the invariant breaks, then \
a check under `scripts/` with a countable answer, then prose — and prose only when none of the \
three can express it, saying which and why.

Write your full report to `{report_dir}/{agent}.md` in this worktree (create the directory), \
plain Markdown naming files in backticks, never as links. Its shape, which \
`scripts/check_docs.py` enforces: the first line `Reviewed at {sha}` (if `git rev-parse HEAD` \
says otherwise when you start, write what you read); a `**Verdict:** ...` line; each finding \
under a `### N.` heading with the fields your definition names, at most {per_finding} lines; \
then only those of Follow-ups, Friction, What carried it and Memory whose answer is not None. \
Nothing else — no restatement of the diff, no list of what you checked and found correct, no \
closing paragraph. At most {cap_base} + {per_finding} × findings lines in all. Return at most \
fifteen lines: verdict, finding count, one line per finding, the report path.
"""

#: The two places a reviewer can be pointed at. A first wave reads the whole diff against the
#: PR's base; a second wave reads what changed since the head the first wave read, because the
#: reports of the first are on file and a re-read of the same diff is the cost this scales away
#: (two second waves in the period to 2026-09-17, each re-reading the branch).
WHERE_DIFF = """\
Where: the worktree `{worktree}`, already on that branch at `{sha}`. Run `git fetch origin` \
first and diff against `origin/{base}` (`git diff origin/{base}...HEAD`); the local `{base}` may \
be stale."""
WHERE_SINCE = """\
Where: the worktree `{worktree}`, on that branch at `{sha}`. This is a second wave: diff against \
`{since}`, the head the first wave read (`git diff {since}...HEAD`), and review what changed \
since it — including whether a change undid a first-wave finding; the first wave's reports are \
named below by path, and what they settled is not re-derived."""



def head_sha(worktree: str) -> str:
    """The worktree's HEAD, short, or `unknown` when git cannot say -- the reviewer then
    writes what it read, and the report names a commit either way."""
    try:
        proc = git_cmd.run(
            "rev-parse", "--short=12", "HEAD",
            cwd=worktree, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - environmental
        return "unknown"
    return proc.stdout.strip() or "unknown" if proc.returncode == 0 else "unknown"


def census(worktree: str, base: str, since: str | None = None) -> str:
    """Insertions per file extension, measured from the diff rather than described.

    A caller describing their own branch describes its *intent* — "docs only", "a small
    fix" — and a reviewer whose first decision is whether this diff is one its axis reviews
    has nothing to check that against. On PR #208 a brief called a diff carrying 2,840 lines
    of Python "docs and artboards only", and only one reviewer's mixed-diff rule kept the
    run from stopping at a single line; that is the friction note this answers.

    Measured against `origin/<base>`, fetched first -- the ref the brief tells the reviewer
    to diff against. Against the local `<base>` it once described a 17-file change as 71
    files, the local branch being two merges stale (#226). For a second wave, against
    `since`, the commit the first wave read, so the measure is of what that wave never saw.

    Deliberately crude — extensions and counts, no judgement about what they mean, because
    the judgement is the reviewer's.
    """
    ref = since or f"origin/{base}"
    try:
        if not since:
            git_cmd.run(
                "fetch", "--quiet", "origin", base, cwd=worktree, timeout=60, check=False
            )
        proc = git_cmd.run(
            "diff", "--numstat", f"{ref}...HEAD",
            cwd=worktree, text=True, timeout=60, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - environmental
        return f"could not be measured ({exc}) — judge the diff yourself before starting."
    if proc.returncode or not proc.stdout.strip():
        return f"could not be measured against `{ref}` — judge the diff yourself."
    added: Counter[str] = Counter()
    removed = 0
    files = 0
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3 or parts[0] == "-":
            continue
        files += 1
        added[Path(parts[2]).suffix or "(no extension)"] += int(parts[0])
        removed += int(parts[1])
    ranked = ", ".join(f"{ext} {n:,}" for ext, n in added.most_common(8))
    # Both sides. Insertions alone described a fold that deleted 186 lines as
    # "666 insertions", the wrong shape for a reviewer weighing volume.
    return (
        f"{files} file(s), +{sum(added.values()):,} / -{removed:,} against `{ref}` — {ranked}. "
        "Your definition decides what kind of diff that is. The paragraph above is the "
        "caller's intent; this line is the measurement, and where they disagree the "
        "measurement is the one that was counted."
    )


def brief(
    agent: str,
    branch: str,
    pr: int,
    worktree: str,
    what: str,
    known: str,
    base: str,
    sha: str,
    since: str | None = None,
) -> str:
    """One reviewer's brief, every slot filled from the arguments and nothing else.

    `base` is the branch the PR is based on -- the trunk unless it is stacked, in which case
    a diff against the trunk would carry the base PR's work and every reviewer would read it
    as this branch's (`docs/friction/2026-09-15-review-brief-hardcodes-origin-main.md`).
    `sha` is the head the brief was written at: the report opens with it, so a tree that
    moved under a reviewer is visible rather than inferred, and `check_docs.py` knows which
    reports the cap binds. `since` makes it a second wave's brief, over the commits after
    the head the first wave read.
    """
    if since:
        where = WHERE_SINCE.format(worktree=worktree, sha=sha, since=since)
        measured = census(worktree, base, since)
    else:
        where = WHERE_DIFF.format(worktree=worktree, sha=sha, base=base)
        measured = census(worktree, base)
    return BRIEF.format(
        agent=agent,
        branch=branch,
        pr=pr,
        sha=sha,
        where=where,
        report_dir=reviews.report_dir(branch),
        what=what.strip(),
        census=measured,
        known=known.strip() or "Nothing beyond the paragraph above.",
        cap_base=reviews.REPORT_CAP_BASE,
        per_finding=reviews.REPORT_CAP_PER_FINDING,
    )


def main(argv: list[str] | None = None) -> int:
    """Print or write the four briefs; the PR's base is asked of gh unless --base says."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--branch", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--what", required=True, type=Path, help="file: what the branch is")
    parser.add_argument("--known", type=Path, help="file: what is already known")
    parser.add_argument("--base", help="the branch the PR is based on (default: ask gh)")
    parser.add_argument("--out", type=Path, help="directory to write <agent>.md into")
    parser.add_argument("--since", help="a second wave: the head the first wave read")
    args = parser.parse_args(argv)
    base = args.base or gh_json.pr_base(None, gh_json.REPO, str(args.pr))
    if not base:
        return report.abort("briefs", f"gh could not say what PR #{args.pr} is based on; give --base")
    what = args.what.read_text(encoding="utf-8")
    known = args.known.read_text(encoding="utf-8") if args.known else ""
    sha = head_sha(args.worktree)
    for agent in reviews.REVIEWERS:
        text = brief(
            agent, args.branch, args.pr, args.worktree, what, known, base, sha, since=args.since
        )
        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out / f"{agent}.md").write_text(text, encoding="utf-8", newline="\n")
            print(args.out / f"{agent}.md")
        else:
            print(f"===== {agent} =====\n{text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
