"""List the open work the record names, next to the open issues, for matching.

Sources, in the order the closing step and the retro read them: each unfolded handoff's
"What remains open" bullets, the friction notes in docs/friction/ whose `**Retro:**`
header line still starts "Unprocessed" (the retro's queue, and the closing step's where a
note implies work) and the ones git holds off main — on a branch or in another worktree,
where no fetch and no listing of this checkout shows them — the "Smaller, for later"
bullets of docs/08, and the bullets of the next roadmap milestones that are not marked
done. Matching a bullet to an issue is judgment and stays with whoever runs this; it puts
both on one screen so that judgment is made once, over the whole list, instead of
rediscovered per file.

Prints; exits 0. With --issues or --fetch it prints the open issue titles as well, and with
--prs or --fetch the open pull requests, naming any handoff, friction note or review report
each carries: a record file still in flight is not on main yet, so the pass must neither
duplicate it nor fold it, and an issue with a PR open on it belongs in In Progress.

The same PR listing answers one more question about work in flight: which two open PRs are
heading for the same file, and whether either deletes it (#140, `overlaps`). It is a listing
and not a check -- the merge order is the owner's -- so it lives here rather than in
`check_prs.py`, which gates.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import gh_json
import git_cmd
import record
import trunk

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
BULLET = re.compile(r"^-\s+(.*)$")
CONTINUATION = re.compile(r"^\s{2,}(\S.*)$")
ROADMAP_MILESTONE = re.compile(r"^#{2,3}\s+(M[0-9.]+)\s+—(.*)$")
# The directories whose files are the record the closing step maintains and the retro reads,
# as gh reports paths. A review report under docs/reviews/ is a pass's ledger (the overlay's
# "Review reports"), in flight until its PR merges exactly as a handoff is. Agent definitions
# used to live under .claude/agents/; since ADR-0019 they are a submodule of the fleet repo,
# so a product PR never carries one and the path is not a record dir here.
RECORD_DIRS = ("docs/handoffs/", "docs/friction/", "docs/reviews/", "docs/digests/")


def bullets_under(text: str, heading: str) -> list[str]:
    """The `- ` bullets between the named heading and the next heading, one string per bullet."""
    out: list[str] = []
    inside = False
    for line in text.splitlines():
        m = HEADING.match(line)
        if m:
            if inside:
                break
            inside = m.group(2).strip() == heading
            continue
        if not inside:
            continue
        b = BULLET.match(line)
        c = CONTINUATION.match(line)
        if b:
            out.append(b.group(1))
        elif out and c:
            out[-1] += " " + c.group(1)
    return out


def short(bullet: str, width: int = 150) -> str:
    """One line per bullet, emphasis dropped, cut at width."""
    text = bullet.replace("**", "").strip()
    return text if len(text) <= width else text[: width - 1] + "…"


def friction_off_main(root: Path) -> dict[str, list[str]]:
    """Friction notes git holds that main does not, each with where it sits.

    A branch not yet merged, a detached checkout in another worktree, or a file untracked in
    one: none of them visible to a fetch or to a listing of this checkout. The first note
    filed (2026-09-08) sat committed on an unpushed branch in a worktree of its own, and the
    pass it was written for reported the directory empty.
    """

    def git(*args: str, cwd: Path = root) -> list[str]:
        return git_cmd.lines(cwd, *args)

    def notes(ref: str, cwd: Path = root) -> list[str]:
        listed = git("ls-tree", "-r", "--name-only", ref, "--", "docs/friction/", cwd=cwd)
        return [p for p in listed if not p.endswith("README.md")]

    base = trunk.ref(root)
    if base is None:
        return {}  # no main here at all (not a repository): nothing to be off
    on_main = set(notes(base))
    where: dict[str, list[str]] = {}
    for ref in git("for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes"):
        if ref == base:
            continue
        for path in notes(ref):
            if path not in on_main:
                where.setdefault(path, []).append(ref)
    for line in git("worktree", "list", "--porcelain"):
        if not line.startswith("worktree "):
            continue
        tree = Path(line[len("worktree ") :])
        # A detached HEAD is on no ref above, so it is the one checkout worth reading directly.
        if not git("symbolic-ref", "-q", "HEAD", cwd=tree):
            for path in notes("HEAD", cwd=tree):
                if path not in on_main:
                    where.setdefault(path, []).append(f"detached in {tree}")
        untracked = git(
            "ls-files", "--others", "--exclude-standard", "--", "docs/friction", cwd=tree
        )
        for path in untracked:
            where.setdefault(path, []).append(f"untracked in {tree}")
    return where


def roadmap_sections(text: str) -> list[tuple[str, bool, list[str]]]:
    """(milestone, done, bullets not themselves marked done) for each roadmap milestone."""
    sections: list[tuple[str, bool, list[str]]] = []
    current: list[str] | None = None
    for line in text.splitlines():
        m = ROADMAP_MILESTONE.match(line)
        if m:
            current = []
            sections.append((m.group(1), "**done**" in m.group(2).lower(), current))
            continue
        if HEADING.match(line):
            if line.startswith("## "):
                current = None
            continue
        if current is None:
            continue
        b = BULLET.match(line)
        c = CONTINUATION.match(line)
        if b:
            current.append(b.group(1))
        elif current and c:
            current[-1] += " " + c.group(1)
    return [
        (name, done, [b for b in bullets if "**done**" not in b]) for name, done, bullets in sections
    ]


def _changed(pr: dict) -> dict[str, str]:
    """The PR's changed paths, each against its change type ("" when `gh` gave none)."""
    return {
        entry["path"]: entry.get("changeType") or ""
        for entry in pr.get("files") or []
        if entry.get("path")
    }


def overlaps(prs: list[dict]) -> list[str]:
    """One line per pair of open PRs that change a file in common; deletions get their own.

    PR #118 conflicted three times in one day, each time because another session's record PR
    had merged into ``main`` first, and in the third round ``main`` had deleted two files
    under headers #118 had added -- a modify/delete conflict with no mechanical resolution
    (`docs/friction/2026-09-14-structural-pr-races-concurrent-merges.md`). Nothing told the
    owner to merge the rewriting PR first, and nothing told the next session to wait. This is
    the scriptable half: ``gh pr list --json files`` already carries every open PR's file
    list, so the answer is a comparison over what this script has already loaded.

    It lists rather than judges, which is why it is here and not in `check_prs.py`: the run
    order and the merge are the owner's, and a shared file is often just two sessions
    appending to one index. #140 put it in `check_prs.py`; `pr-architecture-review` argued
    that a non-gating listing about work in flight belongs in the listing script, and the
    owner agreed (2026-09-14).

    Drafts count. A draft merges later like any other PR, and the collision is with the file,
    not with the readiness.
    """
    notices: list[str] = []
    for index, pr in enumerate(prs):
        mine = _changed(pr)
        for other in prs[index + 1 :]:
            theirs = _changed(other)
            shared = sorted(mine.keys() & theirs.keys())
            if not shared:
                continue
            here, there = f"#{pr['number']}", f"#{other['number']}"
            listed = ", ".join(shared[:4])
            more = f", and {len(shared) - 4} more" if len(shared) > 4 else ""
            notices.append(
                f"{here} and {there} both change {listed}{more} "
                f"({len(shared)} file(s)) — decide which merges first"
            )
            for path in shared:
                gone, kept = mine[path] == "DELETED", theirs[path] == "DELETED"
                if gone != kept:
                    deleter, keeper = (here, there) if gone else (there, here)
                    notices.append(
                        f"{deleter} deletes {path}, which {keeper} changes — a "
                        "modify/delete conflict, with no mechanical resolution"
                    )
    return notices


def fleet_lag(root: Path, fetch: bool = False) -> str | None:
    """How far `.claude/agents` is behind the fleet's main, as one line; None when the
    submodule is not a checkout git can ask.

    A retro's change to a definition reaches this repository only through a pointer bump,
    and nothing told a session when one was owed: every reviewer of PR #225 ran the
    definitions the retro of the day before had replaced (#229). A pointer behind is open
    work -- the bump PR -- so it is listed here, where the closing step and the session-start
    hook already look. Under `fetch` the fleet's `origin/main` is refreshed first.
    """
    sub = root / ".claude" / "agents"
    if not (sub / ".git").exists():
        return None
    if fetch:
        git_cmd.lines(sub, "fetch", "--quiet", "origin", trunk.NAME)
    head = git_cmd.first(sub, "rev-parse", "--short", "HEAD")
    behind = git_cmd.first(sub, "rev-list", "--count", f"HEAD..origin/{trunk.NAME}")
    ahead = git_cmd.first(sub, "rev-list", "--count", f"origin/{trunk.NAME}..HEAD")
    if head is None or behind is None or ahead is None:
        return None
    return fleet_lag_line(head, int(behind), int(ahead))


def fleet_lag_line(head: str, behind: int, ahead: int) -> str:
    """The pointer's standing against the fleet's main, in one line.

    Ahead is the retro's own shape -- the product PR carrying a pointer at a fleet branch's
    head, waiting on that branch's PR -- and reads as pending, never as done: a close that
    read it as "holds" would report a fleet PR merged that had not.
    """
    where = f"`.claude/agents` at {head}"
    if behind == 0 and ahead == 0:
        return f"{where} holds the fleet's origin/{trunk.NAME}"
    if behind == 0:
        return (
            f"{where} is ahead of the fleet's origin/{trunk.NAME} by {ahead} unmerged "
            "commit(s): a fleet PR is pending, and the product PR that carries this pointer "
            "waits on it"
        )
    owed = "a pointer bump is owed"
    if ahead:
        owed = f"and ahead by {ahead} unmerged: the fleet branch needs its main merged in"
    return (
        f"{where} is {behind} commit(s) behind the fleet's origin/{trunk.NAME} -- every agent "
        f"run here uses definitions a fleet PR has since replaced; {owed}"
    )


def main() -> int:
    """Print the candidate open work, then the open issues if they were given."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    gh_json.add_source_arguments(parser, "issues", "prs")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument(
        "--milestones-ahead",
        type=int,
        default=2,
        help="how many not-done roadmap milestones to list bullets for (default 2)",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    if args.fetch:
        trunk.refresh(root)  # the off-main listing below reads origin/main as it finds it

    lag = fleet_lag(root, fetch=args.fetch)
    if lag:
        print("== Agent fleet: the submodule pointer against the fleet's main ==")
        print(f"    {lag}")

    digests = record.digest_entries(root / "docs" / "digests")
    if digests:
        print("== docs/digests: the newest digest, the retro's first list ==")
        print(f"    {digests[-1].relative_to(root).as_posix()}")

    handoff_dir = root / "docs" / "handoffs"
    handoffs, bad_handoffs = record.scan_handoffs(handoff_dir)
    print("== Handoffs: What remains open (folded handoffs skipped) ==")
    for h in handoffs:
        if h.is_folded:
            print(f"  {h.filename}: folded")
            continue
        items = bullets_under((handoff_dir / h.filename).read_text(encoding="utf-8"), "What remains open")
        print(f"  {h.filename}: {len(items)} item(s)")
        for item in items:
            print(f"    - {short(item)}")
    for exc in bad_handoffs:
        # Malformed, not absent: check_docs.py is where this fails the build. A lister that
        # died here would also lose the friction queue and the roadmap bullets below it.
        print(f"  {exc.path}: header malformed ({exc.message})")

    print("== docs/friction: notes whose Retro is still Unprocessed (the retro's queue) ==")
    friction_dir = root / "docs" / "friction"
    notes, bad_notes = record.scan_friction(friction_dir)
    misnamed = sorted(
        p.name
        for p in friction_dir.glob("*.md")
        if p.name != "README.md" and not record.DATED_FILE.match(p.name)
    )
    shown = 0
    for note in sorted(notes, key=lambda n: n.filename):
        if note.is_unprocessed:
            print(f"    - {note.filename}")
            shown += 1
    for name in misnamed:
        print(f"    - {name}  (not named YYYY-MM-DD-slug.md)")
        shown += 1
    for exc in bad_notes:
        print(f"    - {exc.path}  (header malformed: {exc.message})")
        shown += 1
    if not shown:
        total = len(notes) + len(misnamed) + len(bad_notes)
        print(f"    (none; {total} note(s), every one processed)")

    print("== docs/friction: notes git holds that main does not (on a branch, or in a worktree) ==")
    off_main = friction_off_main(root)
    for path, places in sorted(off_main.items()):
        print(f"    - {Path(path).name}  ({'; '.join(places)})")
    if not off_main:
        print("    (none)")

    print("== docs/08: Smaller, for later (decisions stay in the doc; work becomes an issue) ==")
    questions = (root / "docs" / "08-open-questions.md").read_text(encoding="utf-8")
    for item in bullets_under(questions, "Smaller, for later"):
        print(f"    - {short(item)}")

    print(f"== docs/07: bullets of the next {args.milestones_ahead} milestone(s) not marked done ==")
    roadmap = (root / "docs" / "07-roadmap.md").read_text(encoding="utf-8")
    shown = 0
    for name, done, bullets in roadmap_sections(roadmap):
        if done:
            continue
        print(f"  {name}: {len(bullets)} bullet(s) not marked done")
        for b in bullets:
            print(f"    - {short(b)}")
        shown += 1
        if shown >= args.milestones_ahead:
            break

    if args.issues or args.fetch:
        issues = gh_json.load(args.issues, args.gh, gh_json.ISSUES_ARGS)
        print("== Open issues ==")
        for issue in sorted(issues, key=lambda i: i["number"]):
            if issue["state"].upper() == "OPEN":
                milestone = (issue.get("milestone") or {}).get("title") or "no milestone"
                if "agents" in {label["name"] for label in issue.get("labels") or []}:
                    milestone = "agents"
                print(f"  #{issue['number']} [{milestone}] {issue['title']}")

    if args.prs or args.fetch:
        prs = gh_json.load(args.prs, args.gh, gh_json.PRS_ARGS)
        print("== Open PRs (a record file listed here is in flight, not yet on main) ==")
        for pr in sorted(prs, key=lambda p: p["number"]):
            closes = ", ".join(f"#{i['number']}" for i in pr.get("closingIssuesReferences", []))
            print(f"  #{pr['number']} [{pr['headRefName']}] {pr['title']}")
            if closes:
                print(f"    closes {closes} (In Progress on the board while this PR is open)")
            for path in sorted(f["path"] for f in pr.get("files", [])):
                if path.startswith(RECORD_DIRS):
                    print(f"    - {path}")
        if not prs:
            print("    (none)")
        collisions = overlaps(prs)
        if collisions:
            print("== Open PRs heading for the same file ==")
            for line in collisions:
                print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
