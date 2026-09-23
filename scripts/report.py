"""The tail every check under scripts/ ends with: the findings, one verdict line, an exit status.

`scripts/README.md`'s second rule -- report, never fix -- gives the checks one last step in
common: each finding on its own line under the script's prefix, then a count of them when
there were any or a "consistent" line saying what the run vouches for when there were none,
and an exit status of 1 or 0 to match -- with, above them, the notices a run wants seen and
will not fail on. Written once, so the checks cannot drift in how they end and the closing
step's output has one shape. Not a script itself.
"""

from __future__ import annotations

from collections.abc import Sequence


def verdict(
    prefix: str,
    findings: list[str],
    *,
    failed: str | None,
    consistent: str,
    notices: Sequence[str] = (),
) -> int:
    """Print the findings under `prefix`, then the line the outcome calls for; 1 or 0 to match.

    `failed` is the line that follows the findings when there were any -- the caller counts
    them, since what it counts (findings, violations) and against what (notes, modules) is
    its own to say -- and `consistent` is what a clean run vouches for, printed after
    "consistent --". Neither carries the prefix; it is put on here.

    `failed` is `None` where the findings are already their own count: a listing with a gate
    on it prints its detail as it goes, a row at a time, and what it has left to say at the
    end is "6 of 9 worktree(s) not clean" -- the count line itself. A second one under it
    would restate it (#177). Required rather than defaulted, so every caller says which
    shape it is instead of falling into one.

    `notices` are printed first and counted in neither: what the run saw and will not fail
    on -- a rule's own exemption being taken, two PRs heading for the same file. A check
    that stayed silent about those would be the reading it replaced, and one that failed on
    them would make the exit status mean something the rule does not.
    """
    for notice in notices:
        print(f"{prefix}: {notice}")
    for finding in findings:
        print(f"{prefix}: {finding}")
    if findings:
        if failed is not None:
            print(f"{prefix}: {failed}")
        return 1
    print(f"{prefix}: consistent — {consistent}")
    return 0


def clip(text: str, limit: int = 80) -> str:
    """`text` at most `limit` characters, ending in an ellipsis when it was cut.

    Here because a line that is printed is this module's business, and because the same four
    lines were written twice the moment a second script had to print a reason someone else
    wrote (PR #293's parsimony review).
    """
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def abort(prefix: str, message: str) -> int:
    """Print why the run could not happen, under `prefix`; always 1.

    Not a finding: a missing argument, a path that is not there, a record the run needed and
    could not read. It ends before there is anything to vouch for, so there is no count and
    no `consistent` line -- a listing aborts this way as readily as a check does, which is
    why "exits 1" was never the same question as "gates on a finding".

    Its real work is making that difference structural. With both ways out of a script named
    here, which one a script takes is read off its code rather than off a README cell, and a
    bare `return 1` in a `main` is itself the drift -- `scripts/tests/test_report.py` fails
    on one (#177).
    """
    print(f"{prefix}: {message}")
    return 1
