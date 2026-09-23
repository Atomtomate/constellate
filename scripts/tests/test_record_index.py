"""Tests for `scripts/record_index.py`, which renders the header contract as a table.

The parsing those rows come from is `record.py`'s and is tested in `test_record.py`;
what is left here is the rendering -- the column shape the old README tables used, and
the escaping that keeps a value with a pipe in it from growing a column.

Stdlib-only (`unittest`). Run with `python -m unittest discover scripts/tests`.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import record  # noqa: E402
import record_index  # noqa: E402


class TableFormattingTest(unittest.TestCase):
    """The printed table matches the old README's column shape."""

    def test_handoffs_table_header_and_row(self):
        entries = [record.Handoff("2026-09-01", "2026-09-01-x.md", "Did a thing.", "Open -- PR #1")]
        table = record_index.handoffs_table(entries)
        self.assertEqual(
            table,
            "| Date | Task | State |\n"
            "|------|------|-------|\n"
            "| [2026-09-01](2026-09-01-x.md) | Did a thing. | Open -- PR #1 |",
        )

    def test_friction_table_header_and_row(self):
        entries = [record.Friction("2026-09-01", "2026-09-01-x.md", "agent", "cost", "Applied")]
        table = record_index.friction_table(entries)
        self.assertEqual(
            table,
            "| Date | Agent | Friction | Outcome |\n"
            "|------|-------|----------|---------|\n"
            "| [2026-09-01](2026-09-01-x.md) | agent | cost | Applied |",
        )

    def test_a_pipe_in_a_value_is_escaped_not_a_new_column(self):
        entries = [record.Handoff("2026-09-01", "x.md", "prints [handoffs|friction|all]", "Open")]
        table = record_index.handoffs_table(entries)
        row = table.splitlines()[-1]
        # Split on the cell separator " | ", not on every "|": an escaped pipe has no
        # surrounding spaces, so it must not create a fourth cell in a three-column table.
        self.assertEqual(len(row.strip("|").split(" | ")), 3)
        self.assertIn("handoffs\\|friction\\|all", row)


if __name__ == "__main__":
    unittest.main()
