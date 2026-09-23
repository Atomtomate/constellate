"""Block a stop that would leave a record file uncommitted, the docs check red, or the
review pass owed or stale.

Runs from the `Stop` hook in `.claude/settings.json`, after every reply. It cannot tell whether
the task is over, so it blocks only on what is wrong at any point of one: a handoff, friction
note or digest that exists in the tree and in no commit (the note a subagent left, the handoff
written and forgotten, the manager's one output); a `check_docs.py` finding; and, since 2026-09-17, a review pass the branch has
outrun -- commits after the reports that change more than Markdown -- or one that is owed: an
open PR on the branch with no pass, or, in an unattended run, any code and no pass at all --
a report in the tree uncommitted being a pass in flight, which owes nothing yet. In
nine of thirty sessions the pass started only when the owner asked for it, and one unattended
build ended its turn at 23:08 with the pass unrun and eight hours of budget left; the rule was
prose ("before asking the user to review"), and prose does not fire at a turn's end. This does.

A session declares an unattended run the way `mode.py` says; anything else is attended. A dirty tree as such is
not a finding here -- mid-task it is the normal state -- and `worktree_status.py --current`
stays the closing step's gate for it.

Claude Code sends the event on stdin as JSON and reads a decision back on stdout. A block carries
its reason into the session, which continues and sees it once; `stop_hook_active` marks that
continuation, and the hook then stands aside, so a session is never trapped.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import gh_json
import git_cmd
import mode
import reviews
import trunk

ROOT = Path(__file__).resolve().parent.parent
#: Where a subagent's or a session's own record file appears first, as an untracked file.
RECORD_DIRS = ("docs/handoffs", "docs/friction", "docs/digests")


def untracked_record_files(root: Path) -> list[str]:
    """Record files present in the tree and in no commit, repo-relative, sorted."""
    listed = git_cmd.lines(root, "status", "--porcelain", "--untracked-files=all", "--", *RECORD_DIRS)
    return sorted(line[3:] for line in listed if line.startswith("??"))


def docs_findings(root: Path) -> list[str]:
    """`check_docs.py`'s last lines when it fails; nothing when it passes."""
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "check_docs.py")],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode == 0:
        return []
    return [line for line in (result.stdout + result.stderr).splitlines() if line.strip()][-8:]


def branch(root: Path) -> str | None:
    """The checked-out branch, or None on the trunk or a detached head, where no pass is owed."""
    name = git_cmd.first(root, "rev-parse", "--abbrev-ref", "HEAD")
    return None if name in (None, "HEAD", trunk.NAME) else name


def open_pr(root: Path, name: str, gh: str | None = None) -> dict | None:
    """The open PR on `name`, or None -- also when gh is absent or cannot answer."""
    del root  # gh asks GitHub, not the checkout; the argument keeps the call site honest
    try:
        return gh_json.open_pr(gh, name)
    except Exception:  # noqa: BLE001 -- a PR unknown is a nudge withheld, never a crash
        return None


def pass_reason(root: Path, gh: str | None = None) -> str | None:
    """Why the pass stands in the way of this stop, or None when it does not.

    A report of the pass in the tree and in no commit is a pass in flight -- reviewers writing,
    or the session folding -- and nothing is owed until it is committed: the first run of this
    hook blocked every turn end of the pass it was waiting for (PR #238).
    """
    name = branch(root)
    if name is None or reviews.reports_in_flight(root, name):
        return None
    state, commits = reviews.pass_state(root, name, "HEAD", trunk.ref(root))
    if state == "stale":
        return (
            f"The review pass on `{name}` is behind the branch: {len(commits)} commit(s) since "
            f"its reports change more than Markdown -- {'; '.join(commits)}. A second wave sees "
            "them (`python scripts/review_briefs.py ... --known <first wave's findings>`), and "
            "the PR stays a draft until it has; the reports are committed after the fold, not "
            "before it."
        )
    if state != "none":
        return None
    if mode.read(root) == mode.UNATTENDED:
        return (
            f"Unattended run: `{name}` has {len(commits)} commit(s) and no review pass. The "
            "turn does not end with the pass unrun -- run all four reviewers now, fold, write "
            "the handoff, open the PR; a decision only the owner can take is filed as an issue, "
            "not waited on."
        )
    pr = open_pr(root, name, gh)
    if pr and not reviews.not_run_reason(pr):
        return (
            f"PR #{pr['number']} is open on `{name}` and its review pass has not run. Run all "
            "four reviewers before the turn ends; the PR stays a draft until the pass is "
            "folded, or its Review pass section says \"Not run: <why>\" for a record-only PR."
        )
    return None


def reason(root: Path) -> str | None:
    """Why the stop should not happen yet, as one message; None when nothing is wrong."""
    parts = []
    untracked = untracked_record_files(root)
    if untracked:
        parts.append(
            "Record files in the tree and in no commit — stage each by name and commit, or "
            "delete it: " + ", ".join(untracked)
        )
    docs = docs_findings(root)
    if docs:
        parts.append("check_docs.py fails:\n" + "\n".join(docs))
    owed = pass_reason(root)
    if owed:
        parts.append(owed)
    return "\n".join(parts) or None


def main() -> int:
    """Read the event, stand aside on a continuation, otherwise block with the reason."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        event = {} if sys.stdin.isatty() else json.load(sys.stdin)
    except (json.JSONDecodeError, OSError, ValueError):
        event = {}
    if event.get("stop_hook_active"):
        return 0
    try:
        why = reason(ROOT)
    except Exception as exc:  # noqa: BLE001 — a hook that crashes must not take the session down
        print(json.dumps({"systemMessage": f"hook_stop.py did not run: {exc}"}))
        return 0
    if why:
        print(json.dumps({"decision": "block", "reason": why}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
