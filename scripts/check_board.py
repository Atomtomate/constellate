"""Check the GitHub boards against the issues, the milestones and the roadmap.

Two boards (`gh_json.PROJECT`, `gh_json.AGENTS_PROJECT`): one holds product work, the other work
on the agent setup and the CLAUDE.md files, and an issue belongs there when it carries the
`agents` label.

- every open issue is on the board its label puts it on, and on no other
- a product issue carries a roadmap milestone; an `agents` issue carries none
- a board item whose issue is closed sits in Done, and no Done item is still open
- the GitHub milestones are exactly the roadmap's (`## M… —` headings in docs/07)
- a roadmap milestone whose heading says **done** has no open issues on GitHub

Input is the JSON `gh` produces, from files or fetched with --fetch (see gh_json.py).
Reports; never fixes. The exit status is 1 when anything is inconsistent.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import gh_json
import report

ROADMAP_MILESTONE = re.compile(r"^#{2,3}\s+(M[0-9.]+)\s+—(.*)$")
AGENTS_LABEL = "agents"
PRODUCT, AGENTS = "product board", "Agents board"


def roadmap_milestones(roadmap: Path) -> dict[str, bool]:
    """Milestone name → whether its heading marks it done."""
    found: dict[str, bool] = {}
    for line in roadmap.read_text(encoding="utf-8").splitlines():
        m = ROADMAP_MILESTONE.match(line)
        if m:
            found[m.group(1)] = "**done**" in m.group(2).lower()
    return found


def board_status(board: dict, name: str, findings: list[str]) -> dict[int, str]:
    """Issue number → status for one board's items; an item that is not an issue is a finding."""
    status: dict[int, str] = {}
    for item in board.get("items", []):
        content = item.get("content") or {}
        number = content.get("number")
        if number is None:
            findings.append(f"{name} item {item.get('id')} ({item.get('title')!r}) is not an issue")
            continue
        status[number] = item.get("status") or ""
    return status


def check(issues: list, product: dict, agents: dict, milestones: list, roadmap: Path) -> list[str]:
    """One line per inconsistency."""
    findings: list[str] = []
    by_number = {i["number"]: i for i in issues}
    boards = {
        PRODUCT: board_status(product, PRODUCT, findings),
        AGENTS: board_status(agents, AGENTS, findings),
    }

    for number, issue in sorted(by_number.items()):
        labels = {label["name"] for label in issue.get("labels") or []}
        home = AGENTS if AGENTS_LABEL in labels else PRODUCT
        other = PRODUCT if home == AGENTS else AGENTS
        title = issue["title"]
        if issue["state"].upper() == "OPEN":
            if number not in boards[home]:
                findings.append(f"#{number} is open but not on the {home}: {title}")
            if number in boards[other]:
                findings.append(f"#{number} is on the {other} as well as the {home}: {title}")
            if home == PRODUCT and not issue.get("milestone"):
                findings.append(f"#{number} is open and has no milestone: {title}")
            if home == AGENTS and issue.get("milestone"):
                findings.append(f"#{number} carries the agents label and a milestone: {title}")
            if boards[home].get(number) == "Done":
                findings.append(f"#{number} is open but its board item is in Done")
        else:
            for name, status in boards.items():
                if number in status and status[number] != "Done":
                    where = status[number] or "no status"
                    findings.append(f"#{number} is closed but its {name} item is in {where}")
    for name, status in boards.items():
        for number in sorted(set(status) - set(by_number)):
            findings.append(f"{name} item for #{number} refers to an issue gh did not list")

    wanted = roadmap_milestones(roadmap)
    have = {m["title"]: m for m in milestones}
    for name in sorted(set(wanted) - set(have)):
        findings.append(f"roadmap milestone {name} has no GitHub milestone")
    for name in sorted(set(have) - set(wanted)):
        findings.append(f"GitHub milestone {name} is not in the roadmap")
    for name, done in sorted(wanted.items()):
        m = have.get(name)
        if done and m and m.get("open_issues"):
            findings.append(
                f"roadmap marks {name} done but its GitHub milestone has "
                f"{m['open_issues']} open issue(s)"
            )
    return findings


def main() -> int:
    """Parse arguments, load the four JSON sources, run the check and print the findings."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    gh_json.add_source_arguments(parser, "issues", "board", "agents-board", "milestones")
    parser.add_argument(
        "--roadmap",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "docs" / "07-roadmap.md",
    )
    args = parser.parse_args()
    given = (args.issues, args.board, args.agents_board, args.milestones)
    if not args.fetch and None in given:
        parser.error("give --issues, --board, --agents-board and --milestones files, or --fetch")
    issues = gh_json.load(args.issues, args.gh, gh_json.ISSUES_ARGS)
    product = gh_json.load(args.board, args.gh, gh_json.BOARD_ARGS)
    agents = gh_json.load(args.agents_board, args.gh, gh_json.AGENTS_BOARD_ARGS)
    milestones = gh_json.load(args.milestones, args.gh, gh_json.MILESTONES_ARGS)

    findings = check(issues, product, agents, milestones, args.roadmap)
    open_count = sum(1 for i in issues if i["state"].upper() == "OPEN")
    items = len(product.get("items", [])) + len(agents.get("items", []))
    return report.verdict(
        "board",
        findings,
        failed=f"{len(findings)} finding(s); {open_count} open issue(s), {items} board item(s)",
        consistent=(
            f"{open_count} open issue(s), each on the board its label puts it on; "
            f"{len(milestones)} milestone(s) mirror the roadmap"
        ),
    )


if __name__ == "__main__":
    sys.exit(main())
