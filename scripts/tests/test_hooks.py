"""The stop hook blocks on a record file no commit holds, and on nothing else in a dirty tree."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gitenv import git_env  # noqa: E402
import hook_stop  # noqa: E402
import reviews  # noqa: E402

_GIT_ENV = git_env()


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, env=_GIT_ENV)


def _repo(root: Path) -> None:
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    for d in ("docs/handoffs", "docs/friction", "docs/digests", "web"):
        (root / d).mkdir(parents=True)
    (root / "docs/handoffs/2026-09-01-old.md").write_text("# Old\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "the record")


class UntrackedRecordFilesTest(unittest.TestCase):
    def test_a_note_in_no_commit_is_found_and_a_dirty_tree_elsewhere_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            (root / "docs/friction/2026-09-02-note.md").write_text("# Note\n", encoding="utf-8")
            (root / "web/app.ts").write_text("x\n", encoding="utf-8")  # dirty, not a record file
            (root / "docs/handoffs/2026-09-01-old.md").write_text("# Old, edited\n", encoding="utf-8")
            self.assertEqual(
                hook_stop.untracked_record_files(root), ["docs/friction/2026-09-02-note.md"]
            )
            _git(root, "add", "docs/friction/2026-09-02-note.md")
            self.assertEqual(hook_stop.untracked_record_files(root), [])
            (root / "docs/digests/2026-09-18.md").write_text("# Digest\n", encoding="utf-8")
            self.assertEqual(hook_stop.untracked_record_files(root), ["docs/digests/2026-09-18.md"])


def _commit(root: Path, path: str, text: str, message: str) -> None:
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    (root / path).write_text(text, encoding="utf-8")
    _git(root, "add", path)
    _git(root, "commit", "-q", "-m", message)


class ReportsInFlightTest(unittest.TestCase):
    """The question `pass_reason` asks before deciding a review pass is owed."""

    def _branch(self, root: Path) -> Path:
        _repo(root)
        _git(root, "checkout", "-q", "-b", "claude/x")
        directory = root / "docs" / "reviews" / "x"
        directory.mkdir(parents=True)
        return directory

    def test_a_first_pass_counts_while_its_whole_directory_is_untracked(self):
        """git collapses a wholly untracked directory to one line ending in `/`, and a
        branch's first pass is exactly that case -- every report new, nothing tracked beside
        them. Reading a basename off the collapsed line saw no report at all, so the hook
        stopped asking for the pass at the one turn it exists to refuse."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = self._branch(root)
            self.assertFalse(reviews.reports_in_flight(root, "claude/x"))
            (directory / "pr-tech-review.md").write_text("Reviewed at abc1234\n", encoding="utf-8")
            self.assertTrue(reviews.reports_in_flight(root, "claude/x"))

    def test_an_implementation_plan_alone_is_not_a_pass_in_flight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = self._branch(root)
            (directory / "impl-director.md").write_text("# plan\n", encoding="utf-8")
            self.assertFalse(reviews.reports_in_flight(root, "claude/x"))
            (directory / "pr-parsimony-review-first-wave.md").write_text("r\n", encoding="utf-8")
            self.assertTrue(reviews.reports_in_flight(root, "claude/x"))


class ReportsInFlightTest(unittest.TestCase):
    """The question `pass_reason` asks before deciding a review pass is owed."""

    def _branch(self, root: Path) -> Path:
        _repo(root)
        _git(root, "checkout", "-q", "-b", "claude/x")
        directory = root / "docs" / "reviews" / "x"
        directory.mkdir(parents=True)
        return directory

    def test_a_first_pass_counts_while_its_whole_directory_is_untracked(self):
        """git collapses a wholly untracked directory to one line ending in `/`, and a
        branch's first pass is exactly that case -- every report new, nothing tracked beside
        them. Reading a basename off the collapsed line saw no report at all, so the hook
        stopped asking for the pass at the one turn it exists to refuse."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = self._branch(root)
            self.assertFalse(reviews.reports_in_flight(root, "claude/x"))
            (directory / "pr-tech-review.md").write_text("Reviewed at abc1234\n", encoding="utf-8")
            self.assertTrue(reviews.reports_in_flight(root, "claude/x"))

    def test_an_implementation_plan_alone_is_not_a_pass_in_flight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = self._branch(root)
            (directory / "impl-director.md").write_text("# plan\n", encoding="utf-8")
            self.assertFalse(reviews.reports_in_flight(root, "claude/x"))
            (directory / "pr-parsimony-review-first-wave.md").write_text("r\n", encoding="utf-8")
            self.assertTrue(reviews.reports_in_flight(root, "claude/x"))


class PassReasonTest(unittest.TestCase):
    """The pass half: owed in an unattended run or on an open PR, stale after a code commit."""

    def _branch(self, root: Path) -> None:
        _repo(root)
        _git(root, "branch", "-M", "main")
        _git(root, "checkout", "-q", "-b", "claude/x")
        _commit(root, "web/a.ts", "x\n", "code")

    def test_the_trunk_and_a_detached_head_owe_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo(root)
            self.assertIsNone(hook_stop.pass_reason(root))

    def test_unattended_blocks_with_code_and_no_pass_and_attended_needs_a_pr(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._branch(root)
            with mock.patch.object(hook_stop, "open_pr", return_value=None):
                self.assertIsNone(hook_stop.pass_reason(root))
            _git(root, "config", "constellate.mode", "unattended")
            why = hook_stop.pass_reason(root)
            self.assertIn("Unattended run", why)
            self.assertIn("1 commit(s) and no review pass", why)

    def test_an_open_pr_without_a_pass_blocks_unless_the_body_says_not_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._branch(root)
            pr = {"number": 9, "isDraft": True, "body": "## Review pass\n\npending\n"}
            with mock.patch.object(hook_stop, "open_pr", return_value=pr):
                self.assertIn("PR #9 is open", hook_stop.pass_reason(root))
            pr["body"] = "## Review pass\n\nNot run: a record-only PR.\n"
            with mock.patch.object(hook_stop, "open_pr", return_value=pr):
                self.assertIsNone(hook_stop.pass_reason(root))

    def test_a_code_commit_after_the_reports_is_stale_and_markdown_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._branch(root)
            for agent in ("pr-tech-review",):
                _commit(root, f"docs/reviews/x/{agent}.md", "Reviewed at abc1234\n", "reports")
            with mock.patch.object(hook_stop, "open_pr", return_value=None):
                self.assertIsNone(hook_stop.pass_reason(root))
                _commit(root, "docs/07-roadmap.md", "- done\n", "the record")
                self.assertIsNone(hook_stop.pass_reason(root))
                _commit(root, "web/b.ts", "y\n", "a fix nobody reviewed")
                why = hook_stop.pass_reason(root)
            self.assertIn("behind the branch", why)
            self.assertIn("a fix nobody reviewed", why)

    def test_a_merge_from_main_that_brings_code_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._branch(root)
            _commit(root, "docs/reviews/x/pr-tech-review.md", "Reviewed at abc1234\n", "reports")
            _git(root, "checkout", "-q", "main")
            _commit(root, "web/c.ts", "z\n", "someone else's lane")
            _git(root, "checkout", "-q", "claude/x")
            _git(root, "merge", "-q", "--no-edit", "main")
            with mock.patch.object(hook_stop, "open_pr", return_value=None):
                why = hook_stop.pass_reason(root)
            self.assertIn("behind the branch", why)
            self.assertIn("Merge branch 'main'", why)


if __name__ == "__main__":
    unittest.main()
