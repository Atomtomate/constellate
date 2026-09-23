"""Who reviews a PR here, where their reports go, what shape a report keeps, and where a
branch's pass stands against its commits.

Shared by `check_prs.py`, which will not call a PR ready until every reviewer's report is
among its changed files and none of its commits has outrun them; `review_briefs.py`, which
tells each reviewer where to write one and what shape it keeps; `check_docs.py`, which holds
a report to that shape's cap; `hook_stop.py`, which refuses a turn end that leaves a pass
owed or stale; and `failure_ledger.py`, which reads the reports back. Each of those carried
its own copy of one of these facts once -- the roster in two scripts (#193), the "Review pass"
parse in one, the finding pattern in another -- and a fact stated twice is where the brief
and the gate drift apart.

Not a script -- it answers nothing and exits nowhere.
"""

from __future__ import annotations

import re
from pathlib import Path

import git_cmd

#: The four the standard pre-review pass runs on every PR (root `CLAUDE.md`). The order is
#: the one a brief lists them in and a report directory sorts them out of; nothing depends
#: on it, but a stable order keeps two runs' output comparable.
REVIEWERS = (
    "pr-tech-review", "pr-direction-review", "pr-parsimony-review", "pr-architecture-review",
)
#: The line a report opens with, naming the commit the reviewer read -- the brief hands it
#: the sha. A report carrying it was written to the shape below, so the cap binds it; the
#: reports written before the line existed are read but not measured.
REVIEWED_AT = re.compile(r"^Reviewed at `?([0-9a-f]{7,40})`?\.?\s*$")
#: A finding's heading, in the shapes the reports use: `### 1. ...`, `## 2. ...`, and the one
#: that numbers its findings `### F1 — ...`. `failure_ledger.py` reads findings by it too.
FINDING = re.compile(r"^#{2,4}\s+([A-Z]?\d+)(?:\.|\s+[—–-])\s+(.*?)\s*$")
#: A report is at most BASE + PER_FINDING * findings lines: the verdict line, the findings
#: with the fields the definition names, and the closing headings that are not "None". Measured
#: on 2026-09-17: the median report ran 150 lines and a report with no findings 140, most of
#: it a list of what was checked and found correct, which nobody reads.
REPORT_CAP_BASE = 25
REPORT_CAP_PER_FINDING = 15
#: A report git first added on or after this date opens `Reviewed at <sha>` and keeps to the
#: cap; one before it is read as written. `check_docs.py` enforces both, so the line is not
#: the report's to leave out (tech review of PR #238). The date is the day after the rule
#: reached `main`: set to the day the rule was written, it failed `main`'s docs job on the
#: sixteen reports PR #237 had merged that day, written before any brief asked for the line.
REPORT_CAP_FROM = "2026-09-20"

#: CommonMark: the hashes are followed by at least one space, so `#119 was merged early` is
#: an issue reference in prose, not a level-1 heading that would end the section early.
HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
REVIEW_PASS = re.compile(r"review pass", re.IGNORECASE)


def label(word: str) -> re.Pattern[str]:
    """The pattern for a `Label: reason` line a PR body states, however it is emphasised.

    A body is written to be read, so the same statement arrives as `Not run: ...`,
    `**Not run:** ...` and `**Not run** — ...`, and the reason is what follows either way.
    Hand-written, the grammar drifted the moment it was written twice: `reviews.NOT_RUN`
    tolerated emphasis before the word and not after it, so `**Not run:** a record PR` was
    read as a reason of `** a record PR` and `**Not run** - a record PR` as no statement at
    all (PR #293's parsimony and tech reviews, from different directions). One factory, so a
    second label cannot invent a third grammar.
    """
    return re.compile(rf"^[\s_*—–-]*{re.escape(word)}[\s_*`]*[:—–-][\s_*`]*(\S.*)", re.IGNORECASE)


#: The exception's statement -- "Not run: a docs-only record PR" -- a reason after the colon,
#: captured so a run can print the reason it is standing down on rather than only obeying it.
NOT_RUN = label("not run")

#: A path that is prose: a commit touching only these after the reports is the closing step's
#: record-keeping, not work the pass never saw. Anything else -- code, a generated contract,
#: a hook's settings, a generator under `docs/` -- is.
PROSE_SUFFIX = ".md"


def report_dir(branch: str) -> str:
    """Where `branch`'s reports go: `docs/reviews/<branch>`, a leading `claude/` dropped.

    `.claude/agents.local.md` states the rule and this states it in code, so the brief that
    sends a reviewer somewhere and the gate that looks for it there cannot disagree. One
    spelling, not two: the tolerance `check_prs.py` once had for `docs/reviews/claude/<slug>/`
    excused a spelling the record has never used (#193 review).
    """
    return f"docs/reviews/{branch.removeprefix('claude/')}"


def reviewed_at(text: str) -> str | None:
    """The sha a report says it read, from its first lines; None for a report without one."""
    for line in text.splitlines()[:5]:
        match = REVIEWED_AT.match(line.strip())
        if match:
            return match.group(1)
    return None


def report_cap(text: str) -> tuple[int | None, int, int]:
    """`(cap, lines, findings)` for a report; the cap is None when the report names no commit.

    The count of findings is by `FINDING`, the heading shape the ledger reads, so a finding
    the ledger would list is one the cap allows for and nothing else is.
    """
    lines = text.splitlines()
    findings = sum(1 for line in lines if FINDING.match(line))
    if reviewed_at(text) is None:
        return None, len(lines), findings
    return REPORT_CAP_BASE + REPORT_CAP_PER_FINDING * findings, len(lines), findings


def review_pass_section(body: str) -> str | None:
    """The text under the first "Review pass" heading of a PR body, or None when there is none.

    Ends at the next heading of the same or a higher level, so a subsection inside the
    review pass ("Dismissed", say) still counts as its content. Whatever the heading itself
    carries after "Review pass" is prepended, so a placeholder written into the heading is
    seen. An empty string means the heading is there and nothing is under it.
    """
    lines = body.splitlines()
    for index, line in enumerate(lines):
        match = HEADING.match(line)
        if not match or not REVIEW_PASS.search(match.group(2)):
            continue
        level = len(match.group(1))
        tail = REVIEW_PASS.split(match.group(2), maxsplit=1)[1].strip()
        section: list[str] = [tail] if tail else []
        for later in lines[index + 1 :]:
            inner = HEADING.match(later)
            if inner and len(inner.group(1)) <= level:
                break
            section.append(later)
        return "\n".join(section).strip()
    return None


def not_run_reason(pr: dict) -> str | None:
    """The reason a PR gives for not running the pass, or None when it claims none.

    The rule's own exemption, in the root ``CLAUDE.md``: a record-only PR -- docs, tooling,
    bookkeeping, no behaviour or decision content -- may be marked ready with a Review pass
    section that says the pass was not run and why. That statement stands in for the four
    reports, for the gate and for the hook alike.
    """
    section = review_pass_section(pr.get("body") or "")
    if not section:
        return None
    match = NOT_RUN.match(section)
    return match.group(1).strip() if match else None


def _touches_more_than_prose(root: Path, commit: str) -> bool:
    """Whether `commit` changes any file that is not Markdown; a merge is read against its
    first parent, so what it brought in from `main` counts as its change."""
    paths = git_cmd.lines(
        root, "diff-tree", "--no-commit-id", "--name-only", "-r", "-m", "--first-parent", commit
    )
    return any(not path.endswith(PROSE_SUFFIX) for path in paths if path)


def is_reviewer_report(name: str) -> bool:
    """Whether a file under `docs/reviews/` is one of the four reviewers' reports.

    The directory also holds the implementation agents' plans -- `impl-director.md` and the
    specialists' -- which carry no verdict and no findings. `REPORT_CAP_*` is derived from a
    finding count and was measured on reviewer reports, so applying it to a plan caps every
    plan at `REPORT_CAP_BASE` lines whatever it has to specify, and `Reviewed at <sha>` asks a
    plan to name a diff it never read. A first wave's report keeps its reviewer's name under a
    suffix (`.claude/agents.local.md`), so the match is on the prefix.
    """
    stem = Path(name).stem
    return any(stem == agent or stem.startswith(f"{agent}-") for agent in REVIEWERS)


def report_paths(branch: str) -> list[str]:
    """The four reports of `branch`'s pass, by exact name: the pass's ledger is these files and
    nothing else under the directory -- a `-first-wave` copy, or any other file there, is not a
    pass (tech review of PR #238)."""
    directory = report_dir(branch)
    return [f"{directory}/{agent}.md" for agent in REVIEWERS]


def missing_reports(pr: dict) -> list[str]:
    """The reviewers whose report is not among the PR's changed files.

    The pass's ledger read off the PR itself, which is all a script has when the branch is
    somebody else's worktree. `check_prs.py` asks it of a PR that claims to be ready and
    `close_report.py` of one that does not, and a second assembly of "has the pass happened"
    out of these same parts was where the two would have drifted (PR #293's architecture
    review).
    """
    changed = {entry.get("path") for entry in pr.get("files") or []}
    return [
        agent
        for agent, path in zip(REVIEWERS, report_paths(pr.get("headRefName") or ""))
        if path not in changed
    ]


def pass_folded(pr: dict) -> bool:
    """Whether this PR's diff carries the pass's ledger -- all four reports, or the exemption."""
    return bool(not_run_reason(pr)) or not missing_reports(pr)


def _porcelain_path(line: str) -> str:
    """The basename `git status --porcelain` names on one line, renames taken at their target.

    A porcelain line is two status characters, a space, then the path; a rename or copy is
    `R  old -> new`, and the new name is the one on disk.
    """
    path = line[3:].strip().strip('"')
    if " -> " in path:
        path = path.split(" -> ")[-1]
    return path.rstrip("/").split("/")[-1]


def reports_in_flight(root: Path, branch: str) -> bool:
    """Whether a report of `branch`'s pass sits in the tree uncommitted: the pass is running or
    being folded, and a hook that would otherwise call it owed or stale stands aside.

    Only a reviewer's report counts. The directory also collects the implementation agents'
    plans, and an uncommitted plan used to read as a pass in flight -- which stood the hook
    down for exactly the session that had done the work and run no pass (tech review of
    PR #285, finding 2).

    `--untracked-files=all` is load-bearing: without it git collapses a wholly untracked
    directory to one `?? docs/reviews/<branch>/` line, whose basename is empty, and the first
    pass on a branch -- the case where every report is new -- reads as no pass at all. Both
    `pr-tech-review` and `pr-architecture-review` caught that in the second wave of PR #285,
    where the first fix of this function had introduced it. `hook_stop.py` already passed the
    flag when asking the neighbouring question.
    """
    changed = git_cmd.lines(
        root, "status", "--porcelain", "--untracked-files=all", "--", report_dir(branch)
    )
    return any(is_reviewer_report(_porcelain_path(line)) for line in changed if line.strip())


def pass_state(root: Path, branch: str, head: str, base_ref: str | None) -> tuple[str, list[str]]:
    """Where `branch`'s review pass stands against its commits, and the commits at issue.

    The four reports (`report_paths`) are the pass's ledger, committed with the fold or after
    it (`.claude/agents.local.md`, "Review reports"), so the newest commit touching them is
    where the pass stands and the fold rides with it; a later commit that changes more than
    Markdown is work the pass never saw -- a merge from `main` included, since resolving a
    conflict is authorship (PR #225, 2026-09-17). The walk is first-parent: what a merge brought
    in was reviewed on its own PR, and is the merge's one change here. Three answers:

    - ``("stale", commits)`` -- reports exist and these commits came after them;
    - ``("none", commits)`` -- no reports, and these commits change more than Markdown;
    - ``("ok", [])`` -- nothing owed: only Markdown after the reports, or no reports and no code.

    `base_ref` bounds the branch's own commits (`trunk.ref`); without one the range is the
    whole history, which only a test repository has no trunk for. Each commit is one
    `sha  subject` line.
    """
    span = f"{base_ref}..{head}" if base_ref else head
    reports = git_cmd.lines(root, "log", "-1", "--format=%H", span, "--", *report_paths(branch))
    since = f"{reports[0]}..{head}" if reports else span
    candidates = git_cmd.lines(root, "log", "--first-parent", "--format=%h%x09%H%x09%s", since)
    commits = [
        f"{short}  {subject}"
        for short, full, subject in (line.split("\t", 2) for line in candidates if line)
        if _touches_more_than_prose(root, full)
    ]
    if commits:
        return ("stale" if reports else "none", commits)
    return ("ok", [])


def reports_added(root: Path) -> dict[str, str] | None:
    """When each file under `docs/reviews/` was first added, `path -> YYYY-MM-DD`, in one walk;
    None where `root` is no git worktree and nothing can be dated.

    The cap binds a report from `REPORT_CAP_FROM` on whether or not it names its commit, so a
    report that leaves the line out is a finding rather than an exemption. A file git has not
    seen is not here, and is new.
    """
    if git_cmd.first(root, "rev-parse", "--is-inside-work-tree") != "true":
        return None
    added: dict[str, str] = {}
    date = ""
    for line in git_cmd.lines(
        root, "log", "--diff-filter=A", "--name-only", "--format=%as", "--", "docs/reviews"
    ):
        if not line.strip():
            continue
        if line.startswith("docs/reviews/"):
            added[line.strip()] = date  # newest first, so the last date seen is the first add
        else:
            date = line.strip()
    return added
