"""Tests for `scripts/record.py`, the record's header contract.

Stdlib-only (`unittest`), matching `scripts/README.md`'s rule -- no venv, nothing
installed. Run with `python -m unittest discover scripts/tests`.

Each case writes one or two `.md` files into a temp directory shaped like
`docs/handoffs/` or `docs/friction/` and calls the module's own functions -- never a
subprocess -- so a failure points at the parsing or the sorting, not at argument handling.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import record  # noqa: E402


def _write(directory: Path, name: str, text: str) -> Path:
    """Write `text` to `directory/name` and return the path."""
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


class ParseHandoffTest(unittest.TestCase):
    """`parse_handoff` reads the title, Summary and State the contract fixes at lines 1-3."""

    def test_reads_summary_and_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(
                Path(tmp),
                "2026-09-01-example.md",
                "# 2026-09-01 -- Example task\n"
                "**Summary:** Did the thing.\n"
                "**State:** Open -- PR #1\n"
                "\n"
                "Body text.\n",
            )
            handoff = record.parse_handoff(path)
            self.assertEqual(handoff.date, "2026-09-01")
            self.assertEqual(handoff.summary, "Did the thing.")
            self.assertEqual(handoff.state, "Open -- PR #1")

    def test_missing_summary_line_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(
                Path(tmp),
                "2026-09-01-example.md",
                "# 2026-09-01 -- Example task\n\nNo header here.\n",
            )
            with self.assertRaises(record.HeaderError):
                record.parse_handoff(path)

    def test_missing_state_line_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(
                Path(tmp),
                "2026-09-01-example.md",
                "# 2026-09-01 -- Example task\n**Summary:** Did the thing.\n\nBody.\n",
            )
            with self.assertRaises(record.HeaderError):
                record.parse_handoff(path)

    def test_missing_title_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(
                Path(tmp),
                "2026-09-01-example.md",
                "**Summary:** Did the thing.\n**State:** Open\n",
            )
            with self.assertRaises(record.HeaderError):
                record.parse_handoff(path)

    def test_bad_filename_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(
                Path(tmp),
                "not-a-dated-file.md",
                "# Title\n**Summary:** x\n**State:** Open\n",
            )
            with self.assertRaises(record.HeaderError):
                record.parse_handoff(path)


class ParseFrictionTest(unittest.TestCase):
    """`parse_friction` reads the title, Agent, Summary and Retro the contract fixes."""

    def test_reads_agent_summary_and_retro(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(
                Path(tmp),
                "2026-09-01-note.md",
                "# A tool fought back\n"
                "**Agent:** `pr-tech-review`\n"
                "**Summary:** Cost three turns.\n"
                "**Retro:** Unprocessed -- for the next retro\n",
            )
            note = record.parse_friction(path)
            self.assertEqual(note.agent, "`pr-tech-review`")
            self.assertEqual(note.summary, "Cost three turns.")
            self.assertEqual(note.retro, "Unprocessed -- for the next retro")

    def test_missing_agent_line_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(
                Path(tmp),
                "2026-09-01-note.md",
                "# A tool fought back\n## What I was doing\n",
            )
            with self.assertRaises(record.HeaderError):
                record.parse_friction(path)


class SortingAndFilteringTest(unittest.TestCase):
    """`handoffs`/`friction` sort oldest first and `open_only` keeps only the active rows."""

    def test_handoffs_are_sorted_oldest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "2026-09-12-later.md", "# Later\n**Summary:** b\n**State:** Open\n")
            _write(root, "2026-09-01-earlier.md", "# Earlier\n**Summary:** a\n**State:** Open\n")
            entries = record.handoffs(root)
            self.assertEqual([e.filename for e in entries], ["2026-09-01-earlier.md", "2026-09-12-later.md"])

    def test_same_date_breaks_tie_by_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "2026-09-01-zeta.md", "# Zeta\n**Summary:** z\n**State:** Open\n")
            _write(root, "2026-09-01-alpha.md", "# Alpha\n**Summary:** a\n**State:** Open\n")
            entries = record.handoffs(root)
            self.assertEqual([e.filename for e in entries], ["2026-09-01-alpha.md", "2026-09-01-zeta.md"])

    def test_open_only_keeps_open_handoffs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "2026-09-01-open.md", "# Open one\n**Summary:** a\n**State:** Open -- PR #1\n")
            _write(root, "2026-09-02-closed.md", "# Closed one\n**Summary:** b\n**State:** Folded 2026-09-03\n")
            entries = record.handoffs(root, open_only=True)
            self.assertEqual([e.filename for e in entries], ["2026-09-01-open.md"])

    def test_open_only_keeps_unprocessed_friction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root,
                "2026-09-01-pending.md",
                "# Pending\n**Agent:** x\n**Summary:** a\n**Retro:** Unprocessed -- for the next retro\n",
            )
            _write(
                root,
                "2026-09-02-done.md",
                "# Done\n**Agent:** x\n**Summary:** b\n**Retro:** Applied 2026-09-03\n",
            )
            entries = record.friction(root, open_only=True)
            self.assertEqual([e.filename for e in entries], ["2026-09-01-pending.md"])

    def test_readme_is_never_treated_as_an_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "README.md", "# Handoffs\n\nProse, no table.\n")
            _write(root, "2026-09-01-only.md", "# Only\n**Summary:** a\n**State:** Open\n")
            entries = record.handoffs(root)
            self.assertEqual([e.filename for e in entries], ["2026-09-01-only.md"])


class PredicatesTest(unittest.TestCase):
    """`Handoff.is_open`/`is_folded` and `Friction.is_unprocessed` are the vocabulary's one home."""

    def test_handoff_is_open(self):
        h = record.Handoff("2026-09-01", "x.md", "s", "Open -- PR #1")
        self.assertTrue(h.is_open)
        self.assertFalse(h.is_folded)

    def test_handoff_is_folded(self):
        h = record.Handoff("2026-09-01", "x.md", "s", "Folded 2026-09-02 -- merged")
        self.assertTrue(h.is_folded)
        self.assertFalse(h.is_open)

    def test_handoff_neither_open_nor_folded(self):
        # An unrecognised State word is neither -- silent under-reporting stays visible
        # here rather than one predicate wrongly claiming it, which is why check_docs.py
        # does not (yet) enforce a State vocabulary the way it enforces Retro's.
        h = record.Handoff("2026-09-01", "x.md", "s", "Merged as PR #93")
        self.assertFalse(h.is_open)
        self.assertFalse(h.is_folded)

    def test_friction_is_unprocessed(self):
        f = record.Friction("2026-09-01", "x.md", "a", "s", "Unprocessed -- for the next retro")
        self.assertTrue(f.is_unprocessed)

    def test_friction_processed_is_not_unprocessed(self):
        f = record.Friction("2026-09-01", "x.md", "a", "s", "Applied 2026-09-02")
        self.assertFalse(f.is_unprocessed)


class ScanTest(unittest.TestCase):
    """`scan_handoffs`/`scan_friction`: the tolerant entry point `open_work.py` needs."""

    def test_scan_handoffs_separates_good_from_bad(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "2026-09-01-good.md", "# Good\n**Summary:** a\n**State:** Open\n")
            _write(root, "2026-09-02-bad.md", "# Bad\n\nNo header.\n")
            good, bad = record.scan_handoffs(root)
            self.assertEqual([h.filename for h in good], ["2026-09-01-good.md"])
            self.assertEqual(len(bad), 1)
            self.assertEqual(bad[0].path, "2026-09-02-bad.md")

    def test_scan_never_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "2026-09-01-bad.md", "# Bad\n\nNo header.\n")
            good, bad = record.scan_friction(root)  # must not raise
            self.assertEqual(good, [])
            self.assertEqual(len(bad), 1)

    def test_handoffs_still_raises_the_strict_way(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "2026-09-01-bad.md", "# Bad\n\nNo header.\n")
            with self.assertRaises(record.HeaderError):
                record.handoffs(root)


class HeaderErrorTest(unittest.TestCase):
    """`HeaderError` carries the file's name apart from the message (check_docs.py's `rel`)."""

    def test_path_and_message_are_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "2026-09-01-bad.md", "# Bad\n\nNo header.\n")
            try:
                record.parse_handoff(root / "2026-09-01-bad.md")
                self.fail("expected HeaderError")
            except record.HeaderError as exc:
                self.assertEqual(exc.path, "2026-09-01-bad.md")
                self.assertNotIn("2026-09-01-bad.md", exc.message)


if __name__ == "__main__":
    unittest.main()
