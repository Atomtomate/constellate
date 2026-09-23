"""The briefs carry the slots and nothing about the axis; the report path follows the overlay."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import review_briefs  # noqa: E402
import reviews  # noqa: E402


class ReportDirTest(unittest.TestCase):
    def test_claude_prefix_is_dropped_and_other_prefixes_kept(self):
        self.assertEqual(reviews.report_dir("claude/web-invites-55"), "docs/reviews/web-invites-55")
        self.assertEqual(reviews.report_dir("retro/2026-09-14"), "docs/reviews/retro/2026-09-14")


def _brief(agent="pr-tech-review", what="P.", known="", base="main", sha="abc1234def56"):
    return review_briefs.brief(agent, "claude/x", 7, "C:/wt/x", what, known, base, sha)


class BriefTest(unittest.TestCase):
    def test_every_slot_is_filled_and_no_axis_is_named(self):
        text = _brief(what="One paragraph.\n", known="CI green.\n")
        self.assertIn("`claude/x` (PR #7)", text)
        self.assertIn("`C:/wt/x`", text)
        self.assertIn("One paragraph.", text)
        self.assertIn("CI green.", text)
        self.assertIn("`docs/reviews/x/pr-tech-review.md`", text)
        # the slots are the diff's; nothing in the frame names what the reviewer looks for
        for axis in ("correctness", "direction", "parsimony", "layering", "ownership"):
            self.assertNotIn(axis, text)

    def test_known_defaults_when_empty(self):
        self.assertIn("Nothing beyond the paragraph above.", _brief(agent="pr-direction-review"))

    def test_the_diff_is_against_the_base_given(self):
        stacked = _brief(base="claude/base-1")
        self.assertIn("`git diff origin/claude/base-1...HEAD`", stacked)
        self.assertNotIn("origin/main", stacked)

    def test_the_head_and_the_report_shape_reach_every_brief(self):
        """The sha names the commit the report opens with; the cap is `reviews.py`'s number,
        so the brief and `check_docs.py` cannot disagree about it."""
        for agent in reviews.REVIEWERS:
            with self.subTest(agent=agent):
                text = _brief(agent=agent)
                self.assertIn("at `abc1234def56`", text)
                self.assertIn("`Reviewed at abc1234def56`", text)
                self.assertIn(
                    f"At most {reviews.REPORT_CAP_BASE} + {reviews.REPORT_CAP_PER_FINDING} × "
                    "findings lines", text,
                )
                self.assertIn("whose answer is not None", text)

    def test_a_verification_claim_is_the_branchs_account_not_a_fact(self):
        text = _brief(known="Each mutation fails exactly one test.")
        self.assertIn("the branch's own account", text)
        self.assertNotIn("not re-derived", text)

    def test_a_second_wave_diffs_since_the_head_the_first_wave_read(self):
        text = review_briefs.brief(
            "pr-tech-review", "claude/x", 7, "C:/wt/x", "P.", "", "main", "def5678", since="abc1234"
        )
        self.assertIn("`git diff abc1234...HEAD`", text)
        self.assertNotIn("origin/main...HEAD", text)
        self.assertIn("`docs/reviews/x/pr-tech-review.md`", text)  # the exact names come back


class MainTest(unittest.TestCase):
    """The CLI reads the base off the PR, takes --base instead, and aborts with neither.

    Wired through `main` on purpose: the first version tested `brief()` alone, and dropping
    the argument from the call in `main` left every test green while every brief named the
    wrong base (the tech review of PR #214).
    """

    def _run(self, *extra: str, base_from_gh: str | None) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as tmp:
            what = Path(tmp) / "what.md"
            what.write_text("P.\n", encoding="utf-8")
            out = Path(tmp) / "briefs"
            argv = [
                "--branch", "claude/x", "--pr", "7", "--worktree", "C:/wt/x",
                "--what", str(what), "--out", str(out), *extra,
            ]
            with mock.patch.object(review_briefs.gh_json, "pr_base", return_value=base_from_gh):
                code = review_briefs.main(argv)  # the abort case prints its one line; that is fine
            written = out / "pr-tech-review.md"
            return code, written.read_text(encoding="utf-8") if written.is_file() else ""

    def test_base_comes_from_the_pr(self):
        code, text = self._run(base_from_gh="claude/base-1")
        self.assertEqual(code, 0)
        self.assertIn("`git diff origin/claude/base-1...HEAD`", text)

    def test_base_flag_overrides_gh(self):
        code, text = self._run("--base", "claude/base-2", base_from_gh="claude/base-1")
        self.assertEqual(code, 0)
        self.assertIn("`git diff origin/claude/base-2...HEAD`", text)

    def test_no_base_from_anywhere_aborts(self):
        code, text = self._run(base_from_gh=None)
        self.assertEqual(code, 1)
        self.assertEqual(text, "")


class RemedyOrderTest(unittest.TestCase):
    """Every brief carries the owner's remedy order, strongest first (#169).

    Spelled out here rather than imported from the module, so emptying the paragraph fails
    this instead of passing it. The order is the rule -- prose last, and only with a reason
    -- so the assertion is on the positions, not on four separate substrings.
    """

    REMEDIES = (
        "code that makes the mistake impossible",
        "a test that fails when the invariant breaks",
        "a check under `scripts/` with a countable answer",
        "then prose",
    )

    def test_every_reviewers_brief_carries_it_in_order(self):
        for agent in reviews.REVIEWERS:
            with self.subTest(agent=agent):
                text = _brief(agent=agent)
                found = [text.find(remedy) for remedy in self.REMEDIES]
                self.assertNotIn(-1, found, f"{agent}'s brief has lost part of the remedy order")
                self.assertEqual(found, sorted(found), f"{agent}'s brief has it out of order")

    def test_prose_is_the_last_resort_and_has_to_say_why(self):
        self.assertIn("only when none of the three can express it, saying which and why", _brief())


if __name__ == "__main__":
    unittest.main()
