"""Print the handoff and friction indexes from each file's own header.

    python scripts/record_index.py [handoffs|friction|all] [--open]

The header each file carries is the record and the table below is never stored (#111);
`record.py` owns that contract and this prints it. Printed newest last, sorted by date
then filename -- the shape the old tables kept. `--open` keeps only handoffs whose State
starts with "Open" and friction notes whose Retro starts with "Unprocessed", the same
rows `scripts/open_work.py` treats as still active.

Stdlib only: no `gh`, no git, no venv. This reads the files already on disk.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import record
import report


def _escape(value: str) -> str:
    """A cell value with its `|`s escaped, so an extra column is never rendered by accident."""
    return value.replace("|", "\\|")


def handoffs_table(items: list[record.Handoff]) -> str:
    """The handoffs index, in the column shape the old README table used."""
    rows = [
        f"| [{h.date}]({h.filename}) | {_escape(h.summary)} | {_escape(h.state)} |" for h in items
    ]
    return "\n".join(["| Date | Task | State |", "|------|------|-------|", *rows])


def friction_table(items: list[record.Friction]) -> str:
    """The friction index, in the column shape the old README table used."""
    rows = [
        f"| [{f.date}]({f.filename}) | {_escape(f.agent)} | {_escape(f.summary)} | "
        f"{_escape(f.retro)} |"
        for f in items
    ]
    return "\n".join(
        ["| Date | Agent | Friction | Outcome |", "|------|-------|----------|---------|", *rows]
    )


def main() -> int:
    """Parse arguments and print the requested table(s) to stdout."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "subject", nargs="?", choices=["handoffs", "friction", "all"], default="all"
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="only Open handoffs and Unprocessed friction notes",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent

    tables: list[str] = []
    try:
        if args.subject in ("handoffs", "all"):
            handoff_dir = root / "docs" / "handoffs"
            tables.append(handoffs_table(record.handoffs(handoff_dir, open_only=args.open)))
        if args.subject in ("friction", "all"):
            friction_dir = root / "docs" / "friction"
            tables.append(friction_table(record.friction(friction_dir, open_only=args.open)))
    except record.HeaderError as exc:
        return report.abort("record_index", str(exc))

    print("\n\n".join(tables))
    return 0


if __name__ == "__main__":
    sys.exit(main())
