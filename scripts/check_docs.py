"""Check the written record's cross-references.

Four questions a maintenance pass would otherwise answer by reading:

- does every relative Markdown link resolve to a file, and its #anchor to a heading?
- does every `ADR-NNNN` mention name an ADR file that exists?
- does each ADR's Status line agree with the section of docs/adr/README.md listing it?
- does every file in docs/handoffs/ and docs/friction/ (README excluded) carry the header
  its contract fixes, with no link in a value and a friction note's Retro in its
  vocabulary; does neither README hold a table row; does a handoff whose State still
  claims to be open name a branch main has already merged?
- is every review report that names the commit it read within its cap, every handoff dated
  from the cap's start within its own, and every digest within its header and cap (`reviews.py`
  and `record.py` hold the numbers)?

Reports; never fixes. The exit status is 1 when anything is inconsistent.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import git_cmd

import record
import report
import reviews
import trunk

SKIP_DIRS = {".git", ".venv", "node_modules", "worktrees"}
FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`]*`")
LINK = re.compile(r'!?\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
ADR_MENTION = re.compile(r"ADR-(\d{4})")
ADR_STATUS = re.compile(r"^-\s+\*\*Status:\*\*\s*(\w+)", re.M)
README_SECTION = re.compile(r"^##\s+(Accepted|Proposed|Superseded|Parked)\s*$")
ADR_ROW = re.compile(r"^\|\s*\[(\d{4})\]\(")
TABLE_ROW = re.compile(r"^\|\s*\[")
BRANCH_IN_STATE = re.compile(r"branch `([^`]+)`")
OPEN_WORD = re.compile(r"\bopen\b", re.I)
STATUSES = {"Accepted", "Proposed", "Superseded", "Parked"}


def rel(root: Path, path: Path) -> str:
    """A path relative to the root for printing, or absolute if it lies outside."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def submodule_paths(root: Path) -> set[Path]:
    """Absolute paths of the repo's git submodules, read from `.gitmodules`.

    A submodule is independently versioned and is not checked out in every context (CI
    deliberately clones without it), so its files are neither ours to validate nor
    guaranteed present. Both `markdown_files` and `check_links` treat these paths as a
    boundary: we do not walk into them, and we do not assert that a link into one resolves.
    """
    gm = root / ".gitmodules"
    if not gm.is_file():
        return set()
    return {
        (root / m.group(1).strip()).resolve()
        for line in gm.read_text(encoding="utf-8").splitlines()
        if (m := re.match(r"\s*path\s*=\s*(.+)", line))
    }


def under(path: Path, dirs: set[Path]) -> bool:
    """Is `path` one of `dirs` or inside one of them?"""
    return any(path == d or d in path.parents for d in dirs)


def markdown_files(root: Path) -> list[Path]:
    """Every .md under root except vendored, virtualenv, nested-worktree and submodule dirs."""
    subs = submodule_paths(root)
    return sorted(
        p
        for p in root.rglob("*.md")
        if not (set(p.relative_to(root).parts[:-1]) & SKIP_DIRS) and not under(p.resolve(), subs)
    )


def prose_lines(text: str, blank_inline_code: bool = True) -> list[str]:
    """Lines with fenced blocks blanked and, by default, inline code too, so code is never a link."""
    out: list[str] = []
    fenced = False
    for line in text.splitlines():
        if FENCE.match(line):
            fenced = not fenced
            out.append("")
        elif fenced:
            out.append("")
        else:
            out.append(INLINE_CODE.sub("", line) if blank_inline_code else line)
    return out


def slug(heading: str) -> str:
    """GitHub's heading anchor: link text kept, code marks dropped, punctuation removed."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    text = text.replace("`", "").lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return text.strip().replace(" ", "-")


def anchors(path: Path) -> set[str]:
    """The anchors a file's headings define; inline code stays, because GitHub keeps its text."""
    found: set[str] = set()
    for line in prose_lines(path.read_text(encoding="utf-8"), blank_inline_code=False):
        m = HEADING.match(line)
        if m:
            found.add(slug(m.group(1)))
    return found


def check_links(root: Path, files: list[Path]) -> list[str]:
    """Every relative link resolves to a path, and every #anchor into a .md to a heading."""
    findings: list[str] = []
    subs = submodule_paths(root)
    anchor_cache: dict[Path, set[str]] = {}
    for md in files:
        for lineno, line in enumerate(prose_lines(md.read_text(encoding="utf-8")), 1):
            for target in LINK.findall(line):
                target = target.strip("<>")
                if "://" in target or target.startswith("mailto:"):
                    continue
                path_part, _, anchor = target.partition("#")
                dest = md if not path_part else (md.parent / path_part).resolve()
                if under(dest, subs):
                    # A link into a submodule: external, and absent in CI. Not ours to police.
                    continue
                if not dest.exists():
                    findings.append(f"{rel(root, md)}:{lineno}: link target {path_part} does not exist")
                    continue
                if anchor and dest.suffix == ".md":
                    if dest not in anchor_cache:
                        anchor_cache[dest] = anchors(dest)
                    if anchor not in anchor_cache[dest]:
                        findings.append(
                            f"{rel(root, md)}:{lineno}: anchor #{anchor} is not a heading in "
                            f"{rel(root, dest)}"
                        )
    return findings


def check_adrs(root: Path, files: list[Path]) -> list[str]:
    """ADR mentions name files; each ADR's Status matches the README section it sits in."""
    findings: list[str] = []
    adr_dir = root / "docs" / "adr"
    readme = adr_dir / "README.md"
    if not readme.is_file():
        return [f"{rel(root, readme)} missing"]

    listed: dict[str, str] = {}
    section = None
    for line in readme.read_text(encoding="utf-8").splitlines():
        m = README_SECTION.match(line)
        if m:
            section = m.group(1)
            continue
        m = ADR_ROW.match(line)
        if m and section:
            listed[m.group(1)] = section

    on_disk: dict[str, Path] = {}
    for path in sorted(adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md")):
        number = path.name[:4]
        if number == "0000":
            continue
        on_disk[number] = path
        m = ADR_STATUS.search(path.read_text(encoding="utf-8"))
        status = m.group(1) if m else None
        if status not in STATUSES:
            findings.append(f"{rel(root, path)}: unrecognised Status line ({status!r})")
        elif number not in listed:
            findings.append(f"{rel(root, path)}: not listed in docs/adr/README.md")
        elif listed[number] != status:
            findings.append(
                f"{rel(root, path)}: Status is {status} but README lists it under {listed[number]}"
            )
    for number in sorted(set(listed) - set(on_disk)):
        findings.append(f"docs/adr/README.md lists {number}, which has no file")

    for md in files:
        text = "\n".join(prose_lines(md.read_text(encoding="utf-8")))
        for number in sorted(set(ADR_MENTION.findall(text))):
            if number != "0000" and number not in on_disk:
                findings.append(f"{rel(root, md)}: mentions ADR-{number}, which has no file")
    return findings


def _rev(root: Path, name: str) -> str | None:
    """The commit a branch name points at, or None if git has never heard of it.

    A CI checkout fetches every branch as ``origin/<name>`` and creates no local ones, so
    the bare name resolves in a developer's clone and nowhere else.
    """
    for ref in (name, f"origin/{name}"):
        found = git_cmd.first(root, "rev-parse", "--verify", "--quiet", ref)
        if found:
            return found
    return None


def branch_merged(root: Path, branch: str) -> bool | None:
    """True if main contains the branch's tip, False if not, None if git has no such ref.

    An earlier version also trusted a merge commit whose subject named the branch, so a
    branch that moved on after its PR merged still read as merged. That is unsound here:
    names get reused -- ``password-auth-followup`` carried PR #13 and then PR #32 -- and
    the fallback could fire only once the tip had moved past the merge, which is exactly
    when there is no telling which incarnation a handoff meant. A tip that is not in main
    is not merged, and a handoff calling it open is not making a stale claim.
    """
    main_ref = trunk.ref(root)  # origin/main before main; trunk.py says why
    tip, main = _rev(root, branch), _rev(root, main_ref) if main_ref else None
    if tip is None or main is None:
        return None
    if tip == main:
        return False  # the branch has no commits of its own yet, so nothing was merged
    ahead = trunk.ahead(root, tip, main_ref)
    return None if ahead is None else ahead == 0


def stale_open_claim(root: Path, where: str, text: str) -> str | None:
    """A 'State: open … branch `x`' claim whose branch main already contains, or git lacks."""
    if not OPEN_WORD.search(text):
        return None
    m = BRANCH_IN_STATE.search(text)
    if not m:
        return None
    merged = branch_merged(root, m.group(1))
    if merged is True:
        return f"{where}: says open on branch {m.group(1)}, which is merged into main"
    if merged is None:
        return f"{where}: says open on branch {m.group(1)}, which git does not know"
    return None


def _no_links(root: Path, path: Path, **values: str) -> list[str]:
    """A header value may hold no links (a `](` substring); name which field, if any does."""
    return [
        f"{rel(root, path)}: **{key}:** holds a link, which a header value may not"
        for key, value in values.items()
        if "](" in value
    ]


def check_headers(root: Path) -> list[str]:
    """Every handoff and friction note carries its header; no README holds a table row.

    The header replaced a hand-maintained table (#111): `record.py` owns the shape
    of a valid one and the vocabulary its values must use, so this only turns its
    `HeaderError` into a finding, and checks the two things no amount of correct parsing
    would catch on its own -- a link inside a value, and a Retro outside its vocabulary --
    rather than re-deriving any of it. A handoff's own State is the one claim still worth
    checking against git -- an unfolded one naming a branch main has already merged is as
    stale here as it was in the table it replaced.
    """
    findings: list[str] = []
    for directory in (root / "docs" / "handoffs", root / "docs" / "friction", root / "docs" / "digests"):
        readme = directory / "README.md"
        if not readme.is_file():
            findings.append(f"{rel(root, readme)} missing")
        elif any(TABLE_ROW.match(line) for line in readme.read_text(encoding="utf-8").splitlines()):
            findings.append(
                f"{rel(root, readme)}: still holds a table row; the index is derived, not stored"
            )

    for path in record.entries(root / "docs" / "handoffs"):
        try:
            handoff = record.parse_handoff(path)
        except record.HeaderError as exc:
            findings.append(f"{rel(root, path)}: {exc.message}")
            continue
        findings.extend(_no_links(root, path, Summary=handoff.summary, State=handoff.state))
        if not handoff.is_open:
            continue  # a folded/closed State cannot make a stale claim of still being open
        finding = stale_open_claim(root, rel(root, path), f"**State:** {handoff.state}")
        if finding:
            findings.append(finding)

    for path in record.digest_entries(root / "docs" / "digests"):
        try:
            digest = record.parse_digest(path)
        except record.HeaderError as exc:
            findings.append(f"{rel(root, path)}: {exc.message}")
            continue
        findings.extend(_no_links(root, path, Covers=digest.covers, Supersedes=digest.supersedes))

    for path in record.entries(root / "docs" / "friction"):
        try:
            note = record.parse_friction(path)
        except record.HeaderError as exc:
            findings.append(f"{rel(root, path)}: {exc.message}")
            continue
        findings.extend(
            _no_links(root, path, Agent=note.agent, Summary=note.summary, Retro=note.retro)
        )
        if not note.retro.startswith(record.RETRO_WORDS):
            findings.append(
                f"{rel(root, path)}: **Retro:** {note.retro!r} starts with none of "
                f"{record.RETRO_WORDS}"
            )

    return findings


def check_question_ids(root: Path) -> list[str]:
    """Does any `Q-<letter>` in `docs/08` name two questions?

    The file's own second line -- answered questions move to the bottom rather than being
    deleted -- is what makes the letters permanent handles: five handoffs and `ADR-0014`
    cite `Q-F`, and an ADR reading "Q-F is answered" is wrong the moment a second Q-F opens
    above it. That happened, which is why this is a check and not a sentence: a convention
    whose whole value is that the handles never move cannot be held by prose asking the
    writer to grep first.

    Both halves of the file count -- a letter is spent once, whether its question is open or
    answered -- and both spellings do: a heading for an open one, bold for an answered one.
    """
    questions = root / "docs" / "08-open-questions.md"
    if not questions.is_file():
        return []
    first: dict[str, int] = {}
    findings = []
    for number, line in enumerate(questions.read_text(encoding="utf-8").splitlines(), 1):
        # The letter must end there: `Q-E2` is its own question, not a second `Q-E`.
        found = re.match(r"\s*(?:#+\s*|\*\*)Q-([A-Z])(?![0-9A-Za-z])", line)
        if not found:
            continue
        letter = found.group(1)
        if letter in first:
            findings.append(
                f"{rel(root, questions)}:{number}: Q-{letter} is already the question at "
                f"line {first[letter]} — the letters are permanent handles, so take the "
                "next free one"
            )
        else:
            first[letter] = number
    return findings


def check_investigations_parked(root: Path) -> list[str]:
    """Every investigation that states a status must state that it is parked.

    `docs/CLAUDE.md` makes the whole folder parked, but a reader arrives at one file, not at
    the folder, and four product docs now address a single file inside it by name. One of them
    opened `Status: in progress` while every sibling said parked, which is exactly the reading
    a product doc must not be given. A file with no status line at all is exempt: the capture
    kit is written for someone outside the project and has no header.
    """
    findings = []
    folder = root / "docs" / "investigations"
    for path in sorted(folder.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        status = next((line for line in text.splitlines() if "**Status:**" in line), None)
        if status is None:
            continue
        # The whole file, not a header window, and the word rather than the substring:
        # "unparked" contains "parked", a status can sit below a superseded note, and a
        # status line does not have to be a list item. Four of five crafted inputs passed
        # the first version of this check.
        said = status.lower()
        parked = re.search(r"\bparked\b", said) and not re.search(
            r"\b(?:not|no longer|never) parked\b", said
        )
        if not parked:
            findings.append(
                f"{rel(root, path)}: states a status that does not say it is parked "
                f"({status.strip()[:60]!r})"
            )
    return findings


def check_caps(root: Path) -> list[str]:
    """A report over its cap, or a handoff over its own: the record's one guard on volume.

    A report's cap binds when it opens `Reviewed at <sha>`, the line the brief asks for since
    2026-09-17; a report git first added from `reviews.REPORT_CAP_FROM` without that line is
    a finding of its own, so the cap is not the report's to opt out of, and the reports before
    it are read and not measured. Both apply to the four reviewers' reports only
    (`reviews.is_reviewer_report`): the implementation agents' plans share the directory and
    have neither a verdict nor findings to measure. A handoff's binds by its filename date from
    `record.HANDOFF_CAP_FROM`. The session cuts a report over
    the cap to its verdict, its findings and the headings that are not "None" -- what goes is
    padding by the definition's own terms, not testimony.
    """
    findings: list[str] = []
    added = reviews.reports_added(root)
    for path in sorted((root / "docs" / "reviews").rglob("*.md")):
        if not reviews.is_reviewer_report(path.name):
            continue  # An implementation plan shares the directory; the cap is not its shape.
        cap, lines, count = reviews.report_cap(path.read_text(encoding="utf-8"))
        name = path.relative_to(root).as_posix()
        if cap is None and added is not None and added.get(name, "9999") >= reviews.REPORT_CAP_FROM:
            findings.append(
                f"{rel(root, path)}: a report added from {reviews.REPORT_CAP_FROM} opens "
                "`Reviewed at <sha>`, the head its brief named, and this one does not"
            )
        if cap is not None and lines > cap:
            findings.append(
                f"{rel(root, path)}: {lines} lines for {count} finding(s); the cap is {cap} -- "
                "a report is its verdict, its findings and the headings that are not None"
            )
    for path in record.digest_entries(root / "docs" / "digests"):
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > record.DIGEST_CAP:
            findings.append(
                f"{rel(root, path)}: {lines} lines; a digest is at most {record.DIGEST_CAP} -- "
                "the one record whose value is its compression"
            )
    for path in record.entries(root / "docs" / "handoffs"):
        if record.DATED_FILE.match(path.name).group(1) < record.HANDOFF_CAP_FROM:
            continue
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > record.HANDOFF_CAP:
            findings.append(
                f"{rel(root, path)}: {lines} lines; a handoff is at most {record.HANDOFF_CAP} "
                "-- a table that will not fit goes in a file the handoff names"
            )
    return findings


def main() -> int:
    """Parse arguments, run every check and print the findings."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    root = args.root.resolve()
    files = markdown_files(root)
    findings = (
        check_links(root, files)
        + check_adrs(root, files)
        + check_headers(root)
        + check_question_ids(root)
        + check_caps(root)
        + check_investigations_parked(root)
    )
    return report.verdict(
        "docs",
        findings,
        failed=f"{len(findings)} finding(s) across {len(files)} Markdown file(s)",
        consistent=(
            f"{len(files)} Markdown file(s); links and anchors resolve, ADR statuses match "
            "the index, every handoff, friction note and digest carries its header, every "
            "capped report, handoff and digest is within its cap, no question id is spent "
            "twice, every investigation that states a status says it is parked"
        ),
    )


if __name__ == "__main__":
    sys.exit(main())
