"""What `main` is in this checkout: which ref stands for it, and whether it holds a commit.

Four checks ask git about main -- `check_docs.py` (is a handoff's branch merged?),
`check_prs.py` (did a merged PR's work land?), `open_work.py` (which friction notes are off
main?), `worktree_status.py` (does main hold this worktree's HEAD?) -- and each wants the
remote-tracking ref first: a worktree's local `main` lags whatever merged since it last
moved, and a CI checkout has only `origin/main`, so this is also what makes a local answer
match the build's. One decision, made here, rather than a copy of it in each -- and one
place that refreshes the ref, for the scripts whose `--fetch` means "go to the network for
what this run needs". `check_docs.py` has no fetch at all and reads the ref as it finds it;
`worktree_status.py` does the same when it is listing, and refreshes only under `--remove`,
where a stale answer to "has this merged" would delete a branch that had not.

Three of those four then ask "does main hold this commit"; `ahead` is the one answer they
share, and its own docstring says why (#151). `open_work.py` is the exception: it asks
which *files* main carries rather than which commits, and uses `ref` alone. Not a script
itself.
"""

from __future__ import annotations

from pathlib import Path

import git_cmd

NAME = "main"


def ref(root: Path) -> str | None:
    """`origin/main` if this checkout has it, else `main`; None when git resolves neither."""
    for candidate in (f"origin/{NAME}", NAME):
        if git_cmd.first(root, "rev-parse", "--verify", "--quiet", candidate):
            return candidate
    return None


def refresh(root: Path) -> None:
    """Fetch `origin/main`, so the ref `ref` prefers is the remote's tip and not a stale copy.

    A stale copy is how a reader of the ref goes wrong: `check_docs.py` and `open_work.py` go
    lenient or noisy, `check_prs.py` reports a merge that shipped as one that did not. A fetch
    that fails -- offline, or no remote -- leaves the copy as it was, quietly; the reader's own
    finding is where staleness is named.
    """
    git_cmd.run("fetch", "--quiet", "origin", NAME, cwd=root)


def ahead(root: Path, commit: str, main_ref: str) -> int | None:
    """How many commits `commit` has that `main_ref` does not; 0 means `main_ref` holds it.

    The one answer to "does main hold this", which three checks had asked three ways:
    `check_prs.py` about a merged PR's merge commit, `check_docs.py` about a handoff's
    branch tip, `worktree_status.py` about a worktree's HEAD. Two ran
    `merge-base --is-ancestor` behind a presence check of their own, the third counted
    `<ref>..HEAD` because it wanted the distance to print as well (#143). Counting serves
    all three: a count of zero is exactly what `--is-ancestor` reports, and it costs no
    second call for the two that want the number.

    None when git cannot say -- a `commit` this checkout does not hold, which `rev-list`
    refuses rather than guesses. That is one state for all three callers: an object that is
    absent cannot be placed against main. It is not a theoretical case -- a PR's merge
    commit can sit on a base branch since deleted, and a clone that has not fetched has not
    seen the tip that merged.

    The caller passes `main_ref` rather than this reading it, so a caller asking about many
    commits -- `worktree_status.py`, once per worktree -- resolves it once. `ref()` makes it.

    An empty `commit` is None, not an answer: `<ref>..` is git's own spelling of
    `<ref>..HEAD`, so the one input a caller is most likely to pass by accident would be
    answered confidently about the wrong commit.
    """
    if not commit:
        return None
    counted = git_cmd.first(root, "rev-list", "--count", f"{main_ref}..{commit}")
    return int(counted) if counted else None
