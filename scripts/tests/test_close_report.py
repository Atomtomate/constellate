"""Tests for `scripts/close_report.py`: what a PR is reported as waiting on.

Stdlib-only (`unittest`), matching `scripts/README.md`'s rule -- no venv, nothing installed.
Run with `python -m unittest discover scripts/tests`.

The whole value of this script is one phrase per PR, so the tests are about which phrase: a
draft whose pass is folded reads as waiting on the owner (the PR #280 case the script was
written for), a draft missing a report reads as owing its pass, and a stated `Blocked:`
outranks both. Every case is a dict shaped like `gh pr list --json`'s, since that is the only
input it has. The grammar those bodies are read with is `test_pr_body.py`'s.
"""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import close_report  # noqa: E402
import reviews  # noqa: E402


class _Capture(io.StringIO):
    """A `StringIO` that tolerates `main()`'s `sys.stdout.reconfigure(...)` call."""

    def reconfigure(self, **_kwargs) -> None:
        pass


def pr(number: int, *, draft: bool = True, branch: str = "claude/lane", body: str = "",
       base: str = "main", reports: int = 0) -> dict:
    """A PR as `gh` reports one, with `reports` of the four reviewers' reports in its diff."""
    paths = reviews.report_paths(branch)[:reports]
    return {
        "number": number, "title": f"PR {number}", "headRefName": branch, "baseRefName": base,
        "isDraft": draft, "body": body, "files": [{"path": path} for path in paths],
    }


def waits_on(one: dict, open_numbers=None, resolved=None) -> str:
    """`close_report.waits_on` with the two lookups defaulted to "only this PR, nothing asked"."""
    return close_report.waits_on(one, open_numbers or {one["number"]}, resolved or {})


class WaitsOn(unittest.TestCase):
    """One phrase per PR, and which one wins when several could apply."""

    def test_a_ready_pr_is_the_owners_move(self):
        self.assertEqual(waits_on(pr(1, draft=False)), "ready — yours to merge")

    def test_a_draft_with_every_report_waits_on_the_owner(self):
        phrase = waits_on(pr(1, reports=4))
        self.assertEqual(phrase, "waiting on you: pass folded, still a draft")
        self.assertTrue(phrase.startswith(close_report.OWNERS_MOVE))

    def test_the_pass_not_run_exemption_counts_as_folded(self):
        body = "## Review pass\n\nNot run: a record-only PR.\n"
        self.assertEqual(waits_on(pr(1, body=body)), "waiting on you: pass folded, still a draft")

    def test_three_reports_of_four_is_a_pass_still_owed(self):
        self.assertEqual(waits_on(pr(1, reports=3)), "pass owed")

    def test_a_stated_block_outranks_the_pass(self):
        blocked = pr(1, reports=4, body="**Blocked:** no CI while Actions is stopped (#282)")
        self.assertEqual(waits_on(blocked), "blocked: no CI while Actions is stopped (#282)")

    def test_a_dependency_on_an_open_pr_is_what_it_waits_for(self):
        self.assertEqual(waits_on(pr(2, reports=4, body="merge after #1"), {1, 2}),
                         "waits for #1 to merge")

    def test_a_dependency_already_merged_is_not_reported(self):
        self.assertEqual(waits_on(pr(2, reports=4, body="merge after #1")),
                         "waiting on you: pass folded, still a draft")

    def test_a_cross_repo_dependency_gh_says_is_open_is_named(self):
        fleet = pr(2, reports=4, body="merge after **Atomtomate/agents#11**")
        self.assertEqual(waits_on(fleet, resolved={"Atomtomate/agents#11": "OPEN"}),
                         "waits for Atomtomate/agents#11 to merge")

    def test_a_cross_repo_dependency_that_merged_stops_being_reported(self):
        fleet = pr(2, reports=4, body="merge after Atomtomate/agents#11")
        self.assertEqual(waits_on(fleet, resolved={"Atomtomate/agents#11": "MERGED"}),
                         "waiting on you: pass folded, still a draft")

    def test_a_cross_repo_dependency_nobody_could_ask_about_says_so(self):
        fleet = pr(2, reports=4, body="merge after Atomtomate/agents#11")
        self.assertEqual(waits_on(fleet, resolved={"Atomtomate/agents#11": None}),
                         "waits for Atomtomate/agents#11, unconfirmed")

    def test_a_stacked_base_is_what_it_waits_for(self):
        self.assertEqual(waits_on(pr(2, reports=4, base="claude/other")),
                         "waits for its base `claude/other` to merge")


class Block(unittest.TestCase):
    """The pasted shape: aligned columns, `claude/` dropped, one count line."""

    def test_columns_align_and_the_prefix_is_dropped(self):
        lines = close_report.block([pr(1, branch="claude/short"), pr(2, branch="claude/a-longer")])
        self.assertEqual(lines[0], "  #1  draft  short     pass owed")
        self.assertEqual(lines[1], "  #2  draft  a-longer  pass owed")

    def test_a_wider_number_does_not_bend_the_rows(self):
        lines = close_report.block([pr(9, branch="claude/a"), pr(1000, branch="claude/a")])
        self.assertEqual(lines[0].index("draft"), lines[1].index("draft"))

    def test_the_count_line_counts_only_the_owners_move(self):
        lines = close_report.block([pr(1, reports=4), pr(2, branch="claude/b")])
        self.assertEqual(lines[-1], "  2 open, 1 waiting on you")

    def test_nothing_open_says_so(self):
        self.assertEqual(close_report.block([]), ["  (no open PRs)"])

    def test_a_long_reason_is_clipped_to_the_width(self):
        long = pr(1, reports=4, body="Blocked: " + "x" * 200)
        line = close_report.block([long], width=60)[0]
        self.assertLessEqual(len(line), 60)
        self.assertTrue(line.endswith("…"))


class Main(unittest.TestCase):
    """End to end on a saved snapshot, which is what a test may have instead of `gh`."""

    def test_prints_the_block_from_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prs.json"
            path.write_text(json.dumps([pr(280, reports=4, branch="claude/ci-billing")]),
                            encoding="utf-8")
            out = _Capture()
            argv = sys.argv
            sys.argv = ["close_report.py", "--prs", str(path)]
            try:
                with redirect_stdout(out):
                    code = close_report.main()
            finally:
                sys.argv = argv
        self.assertEqual(code, 0)
        self.assertIn("#280", out.getvalue())
        self.assertIn("waiting on you", out.getvalue())

    def test_a_gh_that_will_not_answer_aborts_rather_than_reporting_nothing(self):
        out = _Capture()
        argv = sys.argv
        sys.argv = ["close_report.py", "--gh", "no-such-gh-executable"]
        try:
            with redirect_stdout(out):
                code = close_report.main()
        finally:
            sys.argv = argv
        self.assertEqual(code, 1)
        self.assertIn("would not list", out.getvalue())


if __name__ == "__main__":
    unittest.main()
