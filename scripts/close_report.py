"""The block a session ends with: every open PR, and what each one waits on.

The closing step keeps the record and the boards in step with what a task did
(``.claude/agents/CLAUDE.md``, "Finishing a task"), and then the session writes the owner a
summary whose shape nothing fixes -- so it is invented per session, runs long, and names
none of the PRs the work leaves standing
(``docs/friction/2026-09-21-close-never-names-the-prs-it-leaves-open.md``).

Every other check here answers for the tree it is run in. This one answers for what is left
open across the repository, in fixed columns, so the close can neither forget it nor grow it
into prose:

    #280  draft  ci-billing-local-tests-b75fe9  blocked: no CI while Actions is stopped (#282)
    #285  draft  phone-shell-67                 pass owed

What a PR waits on is derived from what ``gh`` already carries -- the draft flag, the base,
the "merge after" its body states (``pr_body.py``, which also asks the other repository what
became of a cross-repo dependency), and whether the four reports are among its changed files
(``reviews.py``). A draft whose pass is folded and that states nothing is finished work
waiting on a person, and says so rather than reading as work in progress.

A listing, not a gate: which PR merges, and when, is the owner's. ``check_prs.py`` remains
the gate, and reads only the PRs that are *not* drafts -- which is why every draft here was
invisible to it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import gh_json
import pr_body
import report
import reviews
import trunk

PREFIX = "close_report.py"
#: The kinds whose next move is the owner's: nothing a session can do clears them.
OWNERS_MOVE = ("ready", "blocked", "waiting on you")


def waits_on(pr: dict, open_numbers: set[int], resolved: dict[str, str | None]) -> str:
    """What this PR is waiting for, as one short phrase.

    Ordered by what the reader must act on first: a stated block, then a dependency on other
    work, then the pass, then the owner. Only the first applies -- a row says one thing, or
    it is prose again.

    ``resolved`` is `pr_body.cross_repo_states`' answer for the cross-repo references, so a
    dependency that has merged stops being reported: unresolved, the phrase would outlive the
    thing it names, and this script's own PR would have read "waits for Atomtomate/agents#15"
    for the rest of its life (PR #293's tech review).
    """
    if not pr.get("isDraft"):
        return "ready — yours to merge"
    if reason := pr_body.blocked_reason(pr.get("body") or ""):
        return f"blocked: {reason}"
    here, elsewhere = pr_body.merge_after(pr.get("body") or "")
    still_open = sorted(number for number in here if number in open_numbers)
    if still_open:
        return "waits for " + ", ".join(f"#{number}" for number in still_open) + " to merge"
    unmerged = [ref for ref in elsewhere if resolved.get(ref) != "MERGED"]
    if unmerged:
        asked = all(resolved.get(ref) for ref in unmerged)
        return "waits for " + ", ".join(unmerged) + (" to merge" if asked else ", unconfirmed")
    base = pr.get("baseRefName")
    if base and base != trunk.NAME:
        return f"waits for its base `{base}` to merge"
    if reviews.pass_folded(pr):
        return "waiting on you: pass folded, still a draft"
    return "pass owed"


def block(prs: list[dict], resolved: dict[str, str | None] | None = None, width: int = 100
          ) -> list[str]:
    """The whole block, ready to paste: one aligned line per PR, then the line that counts them.

    Both columns are sized to what is present rather than to a constant, so the common case --
    a few short names, three-digit numbers -- does not pay for the widest this repository has
    ever had, and a row does not go crooked the day a number grows a digit.
    """
    if not prs:
        return ["  (no open PRs)"]
    open_numbers = {pr["number"] for pr in prs}
    ordered = sorted(prs, key=lambda p: p["number"])
    # `claude/` opens every branch name here and distinguishes none of them, exactly as it
    # does in `reviews.report_dir`, which drops it for the same reason.
    waiting = [(f"#{pr['number']}",
                report.clip((pr.get("headRefName") or "?").removeprefix("claude/"), 34),
                "draft" if pr.get("isDraft") else "ready",
                waits_on(pr, open_numbers, resolved or {})) for pr in ordered]
    numbers = max(len(number) for number, _, _, _ in waiting)
    branches = max(len(branch) for _, branch, _, _ in waiting)
    lines = []
    for number, branch, flag, phrase in waiting:
        head = f"  {number.ljust(numbers)}  {flag}  {branch.ljust(branches)}  "
        lines.append(head + report.clip(phrase, max(width - len(head), 20)))
    yours = sum(1 for _, _, _, phrase in waiting if phrase.startswith(OWNERS_MOVE))
    return lines + [f"  {len(prs)} open, {yours} waiting on you"]


def main() -> int:
    """Print the close block; 0 unless gh would not say what is open."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # Not `gh_json.add_source_arguments`: that pairs a saved file with `--fetch`, and this
    # script has nothing to do without the PRs -- no file means fetch, and a flag that only
    # ever restates the default would be one more thing to remember at a close.
    parser.add_argument(
        "--prs", type=Path, help="saved output of: gh " + " ".join(gh_json.PRS_ARGS)
    )
    parser.add_argument("--gh", help="the gh executable (default: PATH, then the Windows install)")
    args = parser.parse_args()
    prs = gh_json.load_or_none(args.prs, args.gh, gh_json.PRS_ARGS)
    if prs is None:
        return report.abort(PREFIX, "gh would not list the open PRs, so this close reports none")
    # Only the drafts: a ready PR's dependency is `check_prs.py`'s finding, not a row here.
    resolved = pr_body.cross_repo_states([pr for pr in prs if pr.get("isDraft")], args.gh)
    print("== Open PRs ==")
    for line in block(prs, resolved):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
