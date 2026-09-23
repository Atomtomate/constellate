"""Check the memory directory: index lines, note files and [[wikilinks]] agree.

The maintenance pass used to establish by reading that every note has one line in
MEMORY.md, that every line names a file that exists, and that every wikilink resolves.
This answers those questions the same way every run. It reports; it never fixes. The
exit status is 1 when anything is inconsistent.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import report

DEFAULT_DIR = Path(
    r"C:\Users\Atomt\.claude\projects\C--Users-Atomt-Documents-favorites-tracker\memory"
)
INDEX_LINK = re.compile(r"\]\(([^)]+\.md)\)")
WIKILINK = re.compile(r"\[\[([^\]|#]+)")
FRONTMATTER_KEY = re.compile(r"^(name|description):\s*(.*)$")


def frontmatter(text: str) -> dict[str, str]:
    """The top-level `name` and `description` of the block between the first two `---`."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    keys: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = FRONTMATTER_KEY.match(line)
        if m:
            keys[m.group(1)] = m.group(2).strip().strip('"')
    return keys


def check(memory_dir: Path) -> list[str]:
    """One line per inconsistency; an empty list means the directory is in step."""
    findings: list[str] = []
    index = memory_dir / "MEMORY.md"
    if not index.is_file():
        return [f"index missing: {index}"]
    notes = {p.name: p for p in memory_dir.glob("*.md") if p.name != "MEMORY.md"}

    indexed: list[str] = []
    for lineno, line in enumerate(index.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        targets = INDEX_LINK.findall(line)
        if len(targets) != 1:
            findings.append(
                f"MEMORY.md:{lineno}: expected exactly one (file.md) link, found {len(targets)}"
            )
            continue
        indexed.append(targets[0])
        if targets[0] not in notes:
            findings.append(f"MEMORY.md:{lineno}: points at {targets[0]}, which does not exist")

    for name in sorted(notes):
        count = indexed.count(name)
        if count == 0:
            findings.append(f"{name}: no line in MEMORY.md")
        elif count > 1:
            findings.append(f"{name}: {count} lines in MEMORY.md, expected one")

    for name, path in sorted(notes.items()):
        text = path.read_text(encoding="utf-8")
        fm = frontmatter(text)
        if not fm:
            findings.append(f"{name}: no frontmatter")
        else:
            if fm.get("name") != path.stem:
                findings.append(f"{name}: frontmatter name {fm.get('name')!r} is not the filename")
            if not fm.get("description"):
                findings.append(f"{name}: frontmatter has no description")
        for target in WIKILINK.findall(text):
            if f"{target.strip()}.md" not in notes:
                findings.append(f"{name}: [[{target.strip()}]] does not resolve to a note")
    return findings


def main() -> int:
    """Parse arguments, run the check and print the findings."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("memory_dir", nargs="?", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()
    findings = check(args.memory_dir)
    notes = len(list(args.memory_dir.glob("*.md"))) - 1
    return report.verdict(
        "memory",
        findings,
        failed=f"{len(findings)} finding(s) across {notes} note(s)",
        consistent=f"{notes} note(s), every one indexed, every wikilink resolves",
    )


if __name__ == "__main__":
    sys.exit(main())
