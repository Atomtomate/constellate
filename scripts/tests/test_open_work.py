"""Tests for `scripts/open_work.py`'s two record-reading rules.

Stdlib-only (`unittest`), matching `scripts/README.md`'s rule -- no venv, nothing
installed. Run with `python -m unittest discover scripts/tests`.

`open_work.py` had no test module before this diff rewrote its handoff- and
friction-reading rules to go through `record` instead of a README table (#111):
a handoff is folded when its `State` starts `Folded`, and a friction note is in the
retro's queue when its `Retro` starts `Unprocessed`. Nothing would have failed if either
predicate were inverted or misspelled, which is exactly the shape of bug a table's
absence of a row could not produce. Tests run `main()` end to end and capture stdout,
since that is the whole of what a person or the closing step reads.
"""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import open_work  # noqa: E402


def _write(path: Path, text: str) -> None:
    """Create `path`'s parent directories and write `text` to it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class _Capture(io.StringIO):
    """A `StringIO` that tolerates `main()`'s `sys.stdout.reconfigure(...)` call."""

    def reconfigure(self, **_kwargs) -> None:
        pass


def _run(root: Path, *extra: str) -> str:
    """Run `open_work.main()` against `root`, plus any options, and return what it printed."""
    argv = sys.argv
    sys.argv = ["open_work.py", "--root", str(root), *extra]
    out = _Capture()
    try:
        with redirect_stdout(out):
            open_work.main()
    finally:
        sys.argv = argv
    return out.getvalue()


def _scaffold(root: Path) -> None:
    """The other files `main()` reads unconditionally, minimal but present."""
    _write(root / "docs" / "08-open-questions.md", "## Smaller, for later\n")
    _write(root / "docs" / "07-roadmap.md", "")


class FleetLagTest(unittest.TestCase):
    """The pointer line appears only where `.claude/agents` is a submodule checkout."""

    def test_no_submodule_no_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            self.assertIsNone(open_work.fleet_lag(root))
            self.assertNotIn("Agent fleet", _run(root))

    def test_ahead_reads_as_pending_never_as_holds(self):
        self.assertIn("holds", open_work.fleet_lag_line("abc", 0, 0))
        ahead = open_work.fleet_lag_line("abc", 0, 2)
        self.assertIn("ahead", ahead)
        self.assertIn("pending", ahead)
        self.assertNotIn("holds", ahead)
        self.assertIn("behind", open_work.fleet_lag_line("abc", 3, 0))
        self.assertIn("behind", open_work.fleet_lag_line("abc", 3, 1))
        self.assertIn("ahead by 1", open_work.fleet_lag_line("abc", 3, 1))


class HandoffFoldedRuleTest(unittest.TestCase):
    """A handoff is skipped exactly when its State starts `Folded`, nothing looser."""

    def test_open_handoff_lists_its_remaining_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            _write(
                root / "docs" / "handoffs" / "2026-09-01-open.md",
                "# Open\n**Summary:** a\n**State:** Open -- PR #1\n\n"
                "## What remains open\n\n- Do the thing.\n",
            )
            out = _run(root)
            self.assertIn("2026-09-01-open.md: 1 item(s)", out)
            self.assertIn("Do the thing.", out)

    def test_folded_handoff_is_skipped_not_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            _write(
                root / "docs" / "handoffs" / "2026-09-01-done.md",
                "# Done\n**Summary:** a\n**State:** Folded 2026-09-02 -- merged\n\n"
                "## What remains open\n\n- Should never print.\n",
            )
            out = _run(root)
            self.assertIn("2026-09-01-done.md: folded", out)
            self.assertNotIn("Should never print", out)

    def test_a_state_that_is_neither_open_nor_folded_is_not_silently_folded(self):
        # The regression this test pins: a looser check ("not Open" => folded) would
        # skip this handoff's real open items instead of listing them.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            _write(
                root / "docs" / "handoffs" / "2026-09-01-other.md",
                "# Other\n**Summary:** a\n**State:** Merged as PR #93\n\n"
                "## What remains open\n\n- Still here.\n",
            )
            out = _run(root)
            self.assertIn("2026-09-01-other.md: 1 item(s)", out)
            self.assertIn("Still here.", out)

    def test_malformed_handoff_is_reported_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            _write(root / "docs" / "handoffs" / "2026-09-01-bad.md", "# Bad\n\nNo header.\n")
            _write(
                root / "docs" / "handoffs" / "2026-09-02-good.md",
                "# Good\n**Summary:** a\n**State:** Open\n\n## What remains open\n",
            )
            out = _run(root)  # must not raise
            self.assertIn("2026-09-01-bad.md", out)
            self.assertIn("header malformed", out)
            self.assertIn("2026-09-02-good.md: 0 item(s)", out)  # the rest still printed


class FrictionUnprocessedRuleTest(unittest.TestCase):
    """A note is in the queue exactly when its Retro starts `Unprocessed`."""

    def test_unprocessed_note_is_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            _write(
                root / "docs" / "friction" / "2026-09-01-pending.md",
                "# Pending\n**Agent:** x\n**Summary:** a\n**Retro:** Unprocessed -- for the next retro\n",
            )
            out = _run(root)
            self.assertIn("2026-09-01-pending.md", out)

    def test_applied_note_is_not_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            _write(
                root / "docs" / "friction" / "2026-09-01-done.md",
                "# Done\n**Agent:** x\n**Summary:** a\n**Retro:** Applied 2026-09-02\n",
            )
            out = _run(root)
            self.assertNotIn("2026-09-01-done.md", out)
            self.assertIn("every one processed", out)

    def test_misnamed_note_is_listed_with_its_own_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            _write(root / "docs" / "friction" / "not-dated.md", "# Whatever\n")
            out = _run(root)
            self.assertIn("not-dated.md", out)
            self.assertIn("not named YYYY-MM-DD-slug.md", out)

    def test_malformed_note_is_reported_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            _write(root / "docs" / "friction" / "2026-09-01-bad.md", "# Bad\n\nNo header.\n")
            out = _run(root)  # must not raise
            self.assertIn("2026-09-01-bad.md", out)
            self.assertIn("header malformed", out)


class OpenPrRecordFilesTest(unittest.TestCase):
    """What an open PR carries of the record: handoffs, friction notes and review reports."""

    def test_review_reports_are_listed_beside_the_other_record_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            record = (
                "docs/reviews/x/pr-tech-review.md",
                "docs/handoffs/2026-09-01-x.md",
                "docs/friction/2026-09-01-x.md",
            )
            other = ("web/src/App.tsx", "scripts/open_work.py")
            snapshot = root / "prs.json"
            snapshot.write_text(
                json.dumps(
                    [
                        {
                            "number": 5,
                            "title": "x",
                            "headRefName": "claude/x",
                            "closingIssuesReferences": [],
                            "files": [{"path": p} for p in record + other],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            out = _run(root, "--prs", str(snapshot))
            for path in record:
                self.assertIn(f"- {path}", out)
            for path in other:
                self.assertNotIn(path, out)


def _pr(number, *, draft=False, files=(), deleted=()):
    """A PR as `gh pr list --json files` returns it, for the overlap cases.

    `deleted` names paths the PR removes, which `gh` reports as a `changeType` of `DELETED`
    -- the half of the overlap that has no mechanical resolution.
    """
    return {
        "number": number,
        "title": "a change",
        "isDraft": draft,
        "headRefName": "claude/x",
        "files": [
            {"path": path, "changeType": "DELETED" if path in deleted else "MODIFIED"}
            for path in files
        ],
    }


class TwoOpenPRsHeadingForTheSameFile(unittest.TestCase):
    """#140: PR #118's three conflicts in one day, as a question the listing can answer.

    `_pr` is local to these cases rather than shared with `test_check_prs.py`: what this
    needs of a PR is its number and its files, and nothing of the readiness rule.
    """

    def test_a_shared_file_is_a_notice_naming_both(self):
        notices = open_work.overlaps(
            [_pr(1, files=["docs/handoffs/README.md"]), _pr(2, files=["docs/handoffs/README.md"])]
        )
        self.assertEqual(len(notices), 1)
        self.assertIn("#1 and #2", notices[0])
        self.assertIn("docs/handoffs/README.md", notices[0])

    def test_disjoint_prs_say_nothing(self):
        self.assertEqual(open_work.overlaps([_pr(1, files=["a.md"]), _pr(2, files=["b.md"])]), [])

    def test_a_deletion_on_one_side_gets_its_own_notice(self):
        notices = open_work.overlaps(
            [
                _pr(1, files=["docs/handoffs/x.md"], deleted=["docs/handoffs/x.md"]),
                _pr(2, files=["docs/handoffs/x.md"]),
            ]
        )
        self.assertEqual(len(notices), 2)
        self.assertIn("#1 deletes docs/handoffs/x.md, which #2 changes", notices[1])
        self.assertIn("modify/delete", notices[1])

    def test_both_sides_deleting_is_only_the_overlap(self):
        # Two branches deleting the same file merge cleanly; it is the asymmetry that stalls.
        both = ["docs/handoffs/x.md"]
        notices = open_work.overlaps(
            [_pr(1, files=both, deleted=both), _pr(2, files=both, deleted=both)]
        )
        self.assertEqual(len(notices), 1)

    def test_drafts_count(self):
        # A draft merges later like any other PR; the collision is with the file.
        notices = open_work.overlaps([_pr(1, draft=True, files=["a.md"]), _pr(2, files=["a.md"])])
        self.assertEqual(len(notices), 1)

    def test_three_prs_on_one_file_are_three_pairs(self):
        notices = open_work.overlaps([_pr(n, files=["a.md"]) for n in (1, 2, 3)])
        self.assertEqual(len(notices), 3)

    def test_a_long_shared_list_is_summarised(self):
        paths = [f"docs/{n}.md" for n in range(9)]
        notices = open_work.overlaps([_pr(1, files=paths), _pr(2, files=paths)])
        self.assertIn("and 5 more", notices[0])
        self.assertIn("(9 file(s))", notices[0])

    def test_a_missing_change_type_is_not_a_deletion(self):
        # `gh` carries `changeType`, but the check must not read its absence as one.
        bare = [{"path": "a.md"}]
        one, two = _pr(1, files=["a.md"]), _pr(2, files=["a.md"])
        one["files"] = two["files"] = bare
        self.assertEqual(len(open_work.overlaps([one, two])), 1)


if __name__ == "__main__":
    unittest.main()
