"""Shared loading of the `gh` JSON the scripts here consume.

Every command this tooling sends to `gh` is written once, here: `check_board.py`,
`check_prs.py`, `open_work.py` and `worktree_status.py --remove --fetch` take their JSON
from it, by a file for a test's snapshot or fetched for a real run. Not a script itself.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

WINDOWS_GH = r"C:\Program Files\GitHub CLI\gh.exe"
REPO = "Atomtomate/constellate"
OWNER = "Atomtomate"
PROJECT = "7"

AGENTS_PROJECT = "8"  # the agent setup and the CLAUDE.md files; issues labelled `agents`

ISSUES_ARGS = [
    "issue", "list", "--repo", REPO, "--state", "all", "--limit", "200",
    "--json", "number,title,state,milestone,url,labels",
]
BOARD_ARGS = [
    "project", "item-list", PROJECT, "--owner", OWNER, "--format", "json", "--limit", "200",
]
AGENTS_BOARD_ARGS = [
    "project", "item-list", AGENTS_PROJECT, "--owner", OWNER, "--format", "json",
    "--limit", "200",
]
MILESTONES_ARGS = ["api", f"repos/{REPO}/milestones?state=all"]
PRS_ARGS = [
    "pr", "list", "--repo", REPO, "--state", "open", "--limit", "200",
    "--json", "number,title,headRefName,baseRefName,isDraft,body,url,files,closingIssuesReferences",
]
#: 200 is the evidence window, not just a page size: `worktree_status.py` reclaims a
#: worktree only if its branch is in here, so a worktree whose PR merged more than 200
#: merges ago is kept rather than swept. Conservative in the right direction, and the
#: reason a raise would be a behaviour change rather than a tuning one (#219).
MERGED_ARGS = [
    "pr", "list", "--repo", REPO, "--state", "merged", "--limit", "200",
    "--json", "number,title,baseRefName,headRefName,headRefOid,mergeCommit,url",
]
# Each source a script may take as a saved file, by the option name that carries it.
SOURCES = {
    "issues": ISSUES_ARGS, "board": BOARD_ARGS, "agents-board": AGENTS_BOARD_ARGS,
    "milestones": MILESTONES_ARGS, "prs": PRS_ARGS, "merged": MERGED_ARGS,
}


def gh_path(explicit: str | None) -> str:
    """The gh executable: as given, else on PATH, else its Windows install path."""
    if explicit:
        return explicit
    return shutil.which("gh") or WINDOWS_GH


def fetch(gh: str, args: list[str]):
    """Run gh with the given arguments and parse its stdout as JSON."""
    result = subprocess.run([gh, *args], capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise SystemExit(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def pr_state(gh: str | None, repo: str, number: str) -> str | None:
    """What gh says one PR's state is -- OPEN, CLOSED, MERGED -- or None if it will not say.

    The one question this tooling asks of a repository other than `REPO`: has the PR a body
    says to merge after actually merged (`check_prs.py`, #190). Here rather than there
    because the gh grammar is this module's, like every `*_ARGS` above it; and tolerant
    because the answer is about someone else's repository, where no access, no network and
    no such repository are ordinary rather than fatal.
    """
    answer = fetch_or_none(gh_path(gh), ["pr", "view", number, "--repo", repo, "--json", "state"])
    return (answer or {}).get("state")


def pr_base(gh: str | None, repo: str, number: str) -> str | None:
    """The branch one PR is based on, or None if gh will not say.

    `review_briefs.py` diffs a branch against its base, and a stacked PR's base is not the
    trunk: a brief that assumed it pointed four reviewers at the base PR's work
    (`docs/friction/2026-09-15-review-brief-hardcodes-origin-main.md`). Tolerant for the
    same reason as `pr_state`: offline, the caller can be told the base instead.
    """
    answer = fetch_or_none(gh_path(gh), ["pr", "view", number, "--repo", repo, "--json", "baseRefName"])
    return (answer or {}).get("baseRefName")


def open_pr(gh: str | None, head: str) -> dict | None:
    """The open PR whose head branch is `head` -- number, draft flag, body -- or None when there
    is none or gh will not say.

    `hook_stop.py` asks this at every turn end, so it is tolerant the way `pr_state` is: no gh,
    no network and no PR are each one fact fewer, never a crash; and it is here, `--repo`
    pinned, because the gh grammar is this module's (architecture review of PR #238).
    """
    prs = fetch_or_none(
        gh_path(gh),
        ["pr", "list", "--repo", REPO, "--head", head, "--state", "open", "--limit", "1",
         "--json", "number,isDraft,body"],
    )
    return prs[0] if prs else None


def fetch_or_none(gh: str, args: list[str]):
    """`fetch`, but None when gh cannot answer, for a question a check can live without.

    `fetch` ends the run on a failure because a check that cannot read its own repository
    has nothing to report. A question about another repository is not that: no access, no
    network or a repository that does not exist leaves the caller with one fact fewer, which
    it is the caller's business to report rather than this module's to die on. `OSError`
    is one of those: with no `gh` anywhere, `gh_path` still returns the Windows install path
    and the process will not start, which reached the caller as a traceback rather than as
    None. `hook_stop.py` is the one caller already wrapped against that; `check_prs.py`,
    `review_briefs.py`, `worktree_status.py` and `close_report.py` were not (PR #293's tech
    review, correcting this comment's first draft).
    """
    try:
        return fetch(gh, args)
    except (SystemExit, OSError, json.JSONDecodeError):
        return None


def load(path: Path | None, gh: str | None, fetch_args: list[str]):
    """JSON from the file if one was given, otherwise fetched with gh."""
    if path is not None:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    return fetch(gh_path(gh), fetch_args)


def load_or_none(path: Path | None, gh: str | None, fetch_args: list[str]):
    """`load`, but None when gh will not answer -- for a check that can do without it.

    The same file-or-fetch choice `load` makes, with `fetch_or_none`'s tolerance on the
    fetch half, so a caller that can live without the answer does not have to rebuild that
    choice or reach for `gh_path` itself (#223 review). A saved file still raises if it is
    unreadable: that is the caller's own argument, not the network.
    """
    if path is not None:
        return load(path, gh, fetch_args)
    return fetch_or_none(gh_path(gh), fetch_args)


def add_source_arguments(parser, *names: str) -> None:
    """A --<name> file option per source the script reads, plus --fetch and --gh.

    A script names only the sources it consumes, so its --help advertises nothing it ignores.
    """
    for name in names:
        parser.add_argument(
            f"--{name}", type=Path, help="saved output of: gh " + " ".join(SOURCES[name])
        )
    parser.add_argument(
        "--fetch", action="store_true", help="fetch with gh whatever was not given as a file"
    )
    parser.add_argument("--gh", help="the gh executable (default: PATH, then the Windows install)")
