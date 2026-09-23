"""Print the retro's inputs since a named handoff: the failure ledger the record already holds.

`retro.md` lists where it reads before it judges: the predictions the last retro wrote; every
commit titled "Act on ... review"; the handoff sections named "Review pass", "Not verified",
"Traps", "Known, not fixed" or "Dismissed", and the symmetric "What carried it"; every friction
note with the verdict on its `**Retro:**` line; the review reports under docs/reviews/. Each was
a hand-read across a dozen files. This compiles them into one listing since a named handoff (by
default the newest `*-retro*.md` in docs/handoffs/; a digest's filename cuts at a manager run
instead), so the retro reasons over the record
instead of gathering it. It prints, judges nothing, and exits 0; a cut it cannot find is the one
error, exit 1.

"Since" is git's answer, not the calendar's. The cut is the commit that first added the named
handoff, and a record file is since it when a commit reachable from HEAD but not from the cut
added it (`git log <cut>..HEAD -m --diff-filter=A`, a merge commit's own resolution included).
So a handoff dated the retro's own day but
written before it is not read twice, work merged after the retro is read whatever its date, and
a file added and since deleted is named as such rather than silently gone -- a revert's removed
handoff is a trace too. Commits are the same range, by subject.

Two measures ride along, since 2026-09-17, so the retro's questions about volume are answered
by a number rather than a reading: every handoff's and report's length (a report's beside the
commit it names and the cap that binds it), and, for every PR that merged since the cut (each
first-parent commit on main), the lines it added by kind -- production code, tests, the
generated contract, assets, comments, prose.

Not compiled here, because they need `gh` or judgment: `open_work.py --fetch` (the queue and the
open PRs), the owner's corrections on issues and PR comments, what `ops` filed, the `research`
issues, the board, and `worktree_status.py`. `retro.md` names each.

    python scripts/failure_ledger.py                            # since the newest retro handoff
    python scripts/failure_ledger.py --since 2026-09-08-retro-v1.md
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import git_cmd
import record
import report
import reviews
import trunk

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")
BOLD_LABEL = re.compile(r"^\*\*([^*]+?)\*\*")
#: The handoff sections the retro reads, as the phrase a heading or a bold label must contain:
#: "The review pass", "What the review pass found", "Traps worth not rediscovering",
#: "**Dismissed, with reasons:**" all count. The list is `retro.md`'s; the spellings are the
#: record's.
SECTIONS = (
    "review pass", "not verified", "traps", "known, not fixed", "dismissed", "what carried it",
)
PREDICTIONS = "predictions"
DECISIONS = "needs a decision"
RECORD_DIRS = ("docs/handoffs", "docs/friction", "docs/reviews", "docs/digests")
#: Looser than `retro.md`'s "Act on the … review pass" on purpose: the record's subjects vary
#: ("Act on the tech review", "Act on the four reviews of the draft-PR rule").
ACT_ON = re.compile(r"^act on\b.*\breview", re.IGNORECASE)
#: A review report's verdict: `**Verdict: changes requested.** ...` on one line, the same with
#: only the label in bold (`**Verdict:** changes requested.`), or a heading the reports have
#: used for the same thing, with the verdict as its first paragraph. A report stating it some
#: other way prints "(none stated)", and the retro opens the file.
VERDICT_LINE = re.compile(
    r"^\*\*Verdict:?\s+(.+?)\*\*|^\*\*Verdict:?\*\*\s*(\S.*?)\s*$", re.IGNORECASE
)
VERDICT_HEADINGS = ("verdict", "overall", "state of the change")
#: A finding's heading is `reviews.FINDING` -- the cap counts findings by the same pattern.
FINDING = reviews.FINDING
#: What kind of line a merged PR added, by path and then by content -- the census the
#: 2026-09-17 retro read by hand (49 lines of code under 900 of prose on one PR; 56% prose
#: over 29). Crude on purpose: a docstring opened outside the hunk reads as code.
TEST_PATH = re.compile(r"(^|/)tests?/|\.test\.")
GENERATED = ("openapi.json", "schema.d.ts")
ASSET_SUFFIXES = (".html", ".json", ".svg", ".png", ".woff2", ".yml", ".yaml", ".toml", ".lock")
KINDS = ("prod", "test", "gen", "asset", "cmnt", "prose")


def cut_commit(root: Path, path: str) -> str | None:
    """The commit that first added the record file at repo-relative `path`, or None if git never saw it."""
    added = git_cmd.lines(root, "log", "--diff-filter=A", "--format=%H", "--", path)
    return added[-1] if added else None


def added_since(root: Path, cut: str) -> list[str]:
    """Record files a commit after the cut added, as repo-relative paths, sorted.

    `-c`, because a record file can be born inside a merge commit — a note written while
    resolving the conflict, which is exactly the trace a retro wants — and a plain
    `log --diff-filter=A` never diffs a merge. The combined diff lists a path as added only
    when it is new against every parent, so what a merge merely carried across from one side
    is never listed and nothing has to be subtracted afterwards. (`-m` with the cut's tree
    subtracted was the first form; it hid a file present at the cut, deleted and added back
    after it — the shape a revert and a re-land leave.)
    """
    lines = git_cmd.lines(
        root, "log", f"{cut}..HEAD", "-c", "--diff-filter=A", "--name-only", "--format=",
        "--", *RECORD_DIRS,
    )
    return sorted({line for line in lines if line})


def act_on_commits(root: Path, cut: str) -> list[str]:
    """`hash  date  subject` for each commit after the cut titled "Act on ... review"."""
    out = []
    for line in git_cmd.lines(root, "log", f"{cut}..HEAD", "--format=%h%x09%cs%x09%s"):
        short, date, subject = line.split("\t", 2)
        if ACT_ON.match(subject):
            out.append(f"{short}  {date}  {subject}")
    return out


def merged_since(root: Path, cut: str, tip: str = "HEAD") -> list[tuple[str, str, str]]:
    """`(short, full, subject)` per first-parent commit after the cut up to `tip`: one per PR
    that merged, whether as a squash or a merge commit. The caller passes the trunk's ref
    where it has one, so a retro branch's own merge of `main` is not read as a PR."""
    lines = git_cmd.lines(root, "log", "--first-parent", "--format=%h%x09%H%x09%s", f"{cut}..{tip}")
    return [tuple(line.split("\t", 2)) for line in lines if line.count("\t") >= 2]


def _path_kind(path: str) -> str:
    if path.endswith(".md"):
        return "prose"
    if path.endswith(GENERATED):
        return "gen"
    if path.endswith(ASSET_SUFFIXES):
        return "asset"
    return "test" if TEST_PATH.search(path) else "prod"


def added_by_kind(root: Path, commit: str) -> Counter:
    """Lines `commit` added over its first parent, by kind: prose (Markdown), gen (the
    contract and its client types), asset, test, prod, and cmnt -- a comment, docstring or
    blank line inside a code file, which the prose share does not count and the reader of
    a 13%-comment diff still pays for."""
    counts: Counter = Counter()
    kind = "prod"
    suffix = ""
    in_docstring = False
    for line in git_cmd.lines(root, "diff", "-U0", "--no-color", f"{commit}^1", commit):
        if line.startswith("+++ "):
            path = line[4:].removeprefix("b/")
            kind, suffix = _path_kind(path), Path(path).suffix
            in_docstring = False
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if kind not in ("prod", "test"):
            counts[kind] += 1
            continue
        text = line[1:].strip()
        if suffix == ".py":
            if in_docstring:
                counts["cmnt"] += 1
                in_docstring = ('"""' not in text) and ("'''" not in text)
                continue
            if text.startswith(('"""', "'''")):
                counts["cmnt"] += 1
                quote = text[:3]
                in_docstring = text.count(quote) < 2
                continue
            comment = not text or text.startswith("#")
        elif suffix in (".ts", ".tsx", ".js", ".css"):
            comment = not text or text.startswith(("//", "/*", "*"))
        else:
            comment = not text
        counts["cmnt" if comment else kind] += 1
    return counts


def sections(text: str, phrases: tuple[str, ...] = SECTIONS) -> list[tuple[str, list[str]]]:
    """The (label, body) of every section whose heading or bold label names one of `phrases`.

    A heading's section runs to the next heading of its level or higher, so a "Dismissed"
    subsection under "Review pass" is printed once, inside its parent. A bold label
    (`**Not verified:** ...`) is the older spelling of the same thing, and its section is
    its paragraph. Fenced code is never a heading, whatever it starts with, and neither is
    the title on line 1: a handoff titled "the review pass on it" is about one, not one, and
    reading it as a section would swallow the whole file.
    """
    lines = text.splitlines()
    found: list[tuple[str, list[str]]] = []
    fenced = False
    index = 1
    while index < len(lines):
        line = lines[index]
        if FENCE.match(line):
            fenced = not fenced
        elif not fenced:
            heading = HEADING.match(line)
            if heading and _names(heading.group(2), phrases):
                level = len(heading.group(1))
                end = _section_end(lines, index + 1, level)
                found.append((heading.group(2), _trimmed(lines[index + 1 : end])))
                index = end
                continue
            label = BOLD_LABEL.match(line)
            if label and _names(label.group(1), phrases):
                end = index + 1
                # A heading ends the paragraph even without a blank line before it; a heading
                # swallowed here would take its whole section with it, silently.
                while end < len(lines) and lines[end].strip() and not HEADING.match(lines[end]):
                    end += 1
                found.append((label.group(1).rstrip(":"), lines[index:end]))
                index = end
                continue
        index += 1
    return found


def _names(text: str, phrases: tuple[str, ...]) -> bool:
    """Whether a heading or label contains one of the phrases, however it is dressed."""
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def _section_end(lines: list[str], start: int, level: int) -> int:
    """The index of the next heading at `level` or above, fences respected, or the end."""
    fenced = False
    for index in range(start, len(lines)):
        if FENCE.match(lines[index]):
            fenced = not fenced
        elif not fenced:
            heading = HEADING.match(lines[index])
            if heading and len(heading.group(1)) <= level:
                return index
    return len(lines)


def _trimmed(lines: list[str]) -> list[str]:
    """The lines without leading or trailing blank ones."""
    start, end = 0, len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def predictions(text: str) -> list[str] | None:
    """The body under a heading that is exactly "Predictions", or None when there is none.

    Exactly, because a retro handoff also carries "Predictions checked (...)" -- the last
    retro's, already judged -- and only the new ones are the next retro's to check. A heading
    and a numbered list is the whole contract: `retro.md` asks for one prediction per change,
    and the list is what the retro writes anyway (#74's open question, settled that way).
    """
    return exact_section(text, PREDICTIONS)


def decisions(text: str) -> list[str] | None:
    """The body under a heading that is exactly "Needs a decision", or None.

    The last retro's open decisions are the next retro's input as much as its predictions
    are: an item there without a dated answer is on the next list (`retro.md`, Read first),
    and nothing else reads the section -- `open_work.py` reads "What remains open", which a
    retro handoff does not carry.
    """
    return exact_section(text, DECISIONS)


def exact_section(text: str, label: str) -> list[str] | None:
    """The body under the heading named exactly `label` (case-insensitive), or None."""
    for found, body in sections(text, (label,)):
        if found.strip().lower() == label:
            return body
    return None


def report_summary(text: str) -> tuple[str | None, list[str]]:
    """A review report's verdict, if it states one, and its numbered finding headings."""
    verdict = None
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = VERDICT_LINE.match(line)
        if match:
            verdict = match.group(1) or match.group(2)
            break
        heading = HEADING.match(line)
        if heading and heading.group(2).strip().lower() in VERDICT_HEADINGS:
            paragraph = _trimmed(lines[index + 1 : _section_end(lines, index + 1, len(heading.group(1)))])
            first = []
            for later in paragraph:
                if not later.strip():
                    break
                first.append(later.strip())
            verdict = " ".join(first) or None
            break
    findings = [f"{m.group(1)}. {m.group(2)}" for m in map(FINDING.match, lines) if m]
    return verdict, findings


def newest_retro(handoff_dir: Path) -> str | None:
    """The newest retro handoff by name (the date leads it), among the entries the contract
    counts, or None when there is none."""
    retros = [p.name for p in record.entries(handoff_dir) if "-retro" in p.name]
    return retros[-1] if retros else None


def _entries(paths: list[str], directory: str) -> list[str]:
    """The paths under `directory` that are record entries by `record`'s filename rule.

    The rule is that module's, not this one's: a README added in the range is not a handoff,
    and printing it as a malformed one would hand the retro noise as a trace.
    """
    return [
        path
        for path in paths
        if path.startswith(f"{directory}/") and record.DATED_FILE.match(Path(path).name)
    ]


def _print_block(lines: list[str]) -> None:
    for line in lines:
        print(f"      {line}" if line.strip() else "")


def main() -> int:
    """Print the ledger since the cut handoff; 1 only when the cut cannot be found."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--since",
        help="the handoff or digest to read since (a docs/handoffs/ or docs/digests/ filename; "
        "default: newest retro handoff)",
    )
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    root = args.root.resolve()
    handoff_dir = root / "docs" / "handoffs"

    since = Path(args.since).name if args.since else newest_retro(handoff_dir)
    if since is None:
        return report.abort(
            "ledger", "no *-retro*.md handoff in docs/handoffs/ to read since; give --since"
        )
    if (handoff_dir / since).is_file():
        since_path = f"docs/handoffs/{since}"
    elif (root / "docs" / "digests" / since).is_file():
        since_path = f"docs/digests/{since}"  # a manager run's cut: the digest boundary is not a handoff
    else:
        return report.abort("ledger", f"no such handoff or digest: {since}")
    cut = cut_commit(root, since_path)
    if cut is None:
        return report.abort("ledger", f"git has no commit adding {since_path}; is it committed?")
    described = git_cmd.lines(root, "log", "-1", "--format=%h (%cs)", cut)
    head = git_cmd.lines(root, "rev-parse", "--short", "HEAD")
    print(
        f"== Ledger since {since_path}, added in {described[0] if described else cut}; "
        f"HEAD {head[0] if head else '?'} =="
    )

    # The last retro's Predictions and Needs a decision come from its handoff even when the cut
    # is a digest, which carries neither: the manager's boundary does not move the retro's.
    retro = since if since_path.startswith("docs/handoffs/") else newest_retro(handoff_dir)
    print(f"== Predictions of {retro} (the last retro's, to check before anything else) ==")
    cut_text = (handoff_dir / retro).read_text(encoding="utf-8") if retro else ""
    predicted = predictions(cut_text)
    if predicted is None:
        print("      (no heading named exactly 'Predictions' in it)")
    else:
        _print_block(predicted)

    print(f"== Needs a decision of {retro} (an item without a dated answer is this retro's to open) ==")
    decided = decisions(cut_text)
    if decided is None:
        print("      (no heading named exactly 'Needs a decision' in it)")
    else:
        _print_block(decided)

    added = added_since(root, cut)
    present = [path for path in added if (root / path).is_file()]
    gone = [path for path in added if not (root / path).is_file()]
    handoffs = _entries(present, "docs/handoffs")
    friction = _entries(present, "docs/friction")
    # The four reviewers' reports only: the directory also holds the implementation agents'
    # plans, which have no verdict and no findings and printed here as reports without one.
    reports = [
        p for p in present if p.startswith("docs/reviews/") and reviews.is_reviewer_report(p)
    ]

    digests = [
        p for p in present if p.startswith("docs/digests/") and record.DIGEST_FILE.match(Path(p).name)
    ]
    print(f"== Digests since ({len(digests)}): the manager's list, which the retro takes first ==")
    for path in digests:
        text = (root / path).read_text(encoding="utf-8")
        print(f"  {path}  ({len(text.splitlines())} lines)")
        _print_block(exact_section(text, "Recommendations") or ["(no Recommendations section)"])

    print(f"== Handoffs since ({len(handoffs)}): the sections the retro reads ==")
    for path in handoffs:
        file = root / path
        try:
            summary = record.parse_handoff(file).summary
        except record.HeaderError as exc:
            summary = f"(header malformed: {exc.message})"
        text = file.read_text(encoding="utf-8")
        print(f"  {path}  ({len(text.splitlines())} lines)")
        print(f"    Summary: {summary}")
        found = sections(text)
        if not found:
            print("    (none of the sections the retro reads)")
        for label, body in found:
            print(f"    -- {label} ({len(body)} line(s))")
            _print_block(body)

    print(f"== Friction notes since ({len(friction)}), with the verdict on each ==")
    for path in friction:
        print(f"  {path}")
        try:
            note = record.parse_friction(root / path)
        except record.HeaderError as exc:
            print(f"    (header malformed: {exc.message})")
            continue
        print(f"    Agent: {note.agent}")
        print(f"    Summary: {note.summary}")
        print(f"    Retro: {note.retro}")

    print(f"== Review reports since ({len(reports)}): verdict, findings, length ==")
    for path in reports:
        text = (root / path).read_text(encoding="utf-8")
        verdict, findings = report_summary(text)
        cap, lines, _ = reviews.report_cap(text)
        sha = reviews.reviewed_at(text)
        measure = f"reviewed at {sha}, cap {cap}" if sha else "names no commit, uncapped"
        print(f"  {path}  ({lines} lines, {len(findings)} finding(s), {measure})")
        print(f"    Verdict: {verdict or '(none stated)'}")
        for finding in findings:
            print(f"    {finding}")

    acted = act_on_commits(root, cut)
    print(f'== Commits since titled "Act on ... review" ({len(acted)}) ==')
    for line in acted:
        print(f"  {line}")

    tip = trunk.ref(root) or "HEAD"
    landed = merged_since(root, cut, tip)
    print(f"== Merged into {tip} since ({len(landed)}): lines added, by kind ==")
    print(f"  {'sha':8} {'prod':>5} {'test':>5} {'gen':>5} {'asset':>5} {'cmnt':>5} {'prose':>6} {'prose%':>6}  subject")
    total: Counter = Counter()
    for short, full, subject in landed:
        counts = added_by_kind(root, full)
        total.update(counts)
        added = sum(counts.values())
        share = f"{100 * counts['prose'] / added:5.0f}%" if added else "     -"
        cells = " ".join(f"{counts[kind]:5}" for kind in KINDS[:-1])
        print(f"  {short:8} {cells} {counts['prose']:6} {share}  {subject[:60]}")
    if landed:
        added = sum(total.values())
        cells = " ".join(f"{total[kind]:5}" for kind in KINDS[:-1])
        share = f"{100 * total['prose'] / added:5.0f}%" if added else "     -"
        print(f"  {'ALL':8} {cells} {total['prose']:6} {share}")

    if gone:
        # As of this checkout's HEAD: a file main re-added after this branch left it is
        # still gone here.
        print(f"== Record files added since and gone again, as of HEAD ({len(gone)}) ==")
        for path in gone:
            print(f"  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
