"""Tests for `scripts/check_docs.py`'s `check_headers`.

Stdlib-only (`unittest`), matching `scripts/README.md`'s rule -- no venv, nothing
installed. Run with `python -m unittest discover scripts/tests`.

`check_headers` replaced the old `check_handoffs`'s table/file cross-check (#111): every
handoff and friction note now carries its own header, via `record.parse_handoff` and
`parse_friction`, and neither README may hold a table row. The one piece of the old check
still worth keeping is the git-backed one -- a handoff whose State claims to be open on a
branch `main` has already merged into is a stale claim whether that claim lives in a table
row or, now, in the file's own header. Those two cases build a real git repo in a temp
directory, since `stale_open_claim` shells out to `git`; the rest just write files.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gitenv import git_env  # noqa: E402
import check_docs  # noqa: E402
import record  # noqa: E402
import reviews  # noqa: E402


def _write(path: Path, text: str) -> None:
    """Create `path`'s parent directories and write `text` to it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _scaffold(root: Path) -> None:
    """The minimum both README files need so only what a test adds is under test."""
    _write(root / "docs" / "handoffs" / "README.md", "# Handoffs\n\nProse, no table.\n")
    _write(root / "docs" / "friction" / "README.md", "# Friction notes\n\nProse, no table.\n")
    _write(root / "docs" / "digests" / "README.md", "# Digests\n\nProse, no table.\n")


_GIT_ENV = git_env()


def _git(root: Path, *args: str) -> None:
    """Run a git command in `root`, failing the test loudly if it errors.

    A commit needs an author; a CI runner carries no global `user.name`/`user.email`, only
    a developer's machine does, so every call gets one through the environment rather than
    relying on whichever call sites remembered `-c user.name=...`.
    """
    subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True, env=_GIT_ENV
    )


class CheckQuestionIdsTest(unittest.TestCase):
    """A `Q-<letter>` is spent once, whether its question is open or answered.

    `docs/08`'s own rule keeps answered questions in the file, which is what makes the
    letters permanent handles: six handoffs and `ADR-0014` cite `Q-F`, so an ADR reading
    "Q-F is answered" goes wrong the moment a second Q-F opens above it. That happened on
    the branch that added this check.
    """

    def ids(self, *lines: str) -> list[str]:
        """Run the check over a scratch `docs/08` made of `lines`."""
        root = Path(tempfile.mkdtemp())
        _write(root / "docs" / "08-open-questions.md", "\n".join(lines))
        return check_docs.check_question_ids(root)

    def test_a_letter_used_twice_is_a_finding(self):
        found = self.ids("### Q-D — first", "", "### Q-D — second")
        self.assertEqual(len(found), 1)
        self.assertIn("Q-D", found[0])

    def test_an_answered_question_still_holds_its_letter(self):
        # The two halves of the file are one namespace: a heading above, bold below.
        found = self.ids("### Q-F — reopened?", "", "---", "", "**Q-F — answered** → yes")
        self.assertEqual(len(found), 1)

    def test_a_suffixed_id_is_its_own_question(self):
        # `Q-E2` exists beside `Q-E` in the real file and is not a collision.
        self.assertEqual(self.ids("**Q-E — one**", "", "**Q-E2 — another**"), [])

    def test_distinct_letters_pass(self):
        self.assertEqual(self.ids("### Q-A — a", "", "### Q-B — b"), [])

class CheckCapsTest(unittest.TestCase):
    """A report is capped only when it names the commit it read; a handoff by its date."""

    def test_a_report_naming_its_commit_is_held_to_the_cap_and_an_older_one_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            padding = "line\n" * 60
            _write(root / "docs" / "reviews" / "x" / "pr-tech-review.md", "# old shape\n" + padding)
            self.assertEqual(check_docs.check_caps(root), [])
            capped = "Reviewed at abc1234\n**Verdict:** one.\n\n### 1. a\n" + padding
            _write(root / "docs" / "reviews" / "x" / "pr-direction-review.md", capped)
            findings = check_docs.check_caps(root)
            self.assertEqual(len(findings), 1)
            self.assertIn("pr-direction-review.md", findings[0])
            self.assertIn(f"the cap is {reviews.REPORT_CAP_BASE + reviews.REPORT_CAP_PER_FINDING}", findings[0])

    def test_an_implementation_plan_is_not_held_to_the_reviewers_cap(self):
        """`docs/reviews/` holds the implementation agents' plans too, and a plan has no
        verdict and no findings -- the cap would bind every one of them at its base."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            plan = "# impl-director -- a lane\n" + "line\n" * 200
            _write(root / "docs" / "reviews" / "x" / "impl-director.md", plan)
            _write(root / "docs" / "reviews" / "x" / "impl-frontend.md", plan)
            self.assertEqual(check_docs.check_caps(root), [])

    def test_a_handoff_is_capped_from_the_start_date_and_not_before(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            header = "# t\n**Summary:** s\n**State:** Open\n"
            body = header + "x\n" * record.HANDOFF_CAP
            _write(root / "docs" / "handoffs" / "2026-09-01-before.md", body)
            self.assertEqual(check_docs.check_caps(root), [])
            _write(root / "docs" / "handoffs" / f"{record.HANDOFF_CAP_FROM}-after.md", body)
            findings = check_docs.check_caps(root)
            self.assertEqual(len(findings), 1)
            self.assertIn("-after.md", findings[0])
            self.assertIn(f"at most {record.HANDOFF_CAP}", findings[0])


class DigestTest(unittest.TestCase):
    """A digest is held to its header and its cap like every other record kind."""

    def test_a_digest_over_the_cap_or_without_its_header_is_a_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            good = "# D\n**Covers:** a to b\n**Supersedes:** nothing\n\n" + "line\n" * 10
            _write(root / "docs" / "digests" / "2026-09-18.md", good)
            self.assertEqual(check_docs.check_headers(root), [])
            self.assertEqual(check_docs.check_caps(root), [])
            _write(root / "docs" / "digests" / "2026-09-25.md", "# D\n**Covers:** a to b\n\n" + "line\n" * 130)
            headers = check_docs.check_headers(root)
            self.assertEqual(len(headers), 1)
            self.assertIn("**Supersedes:**", headers[0])
            caps = check_docs.check_caps(root)
            self.assertEqual(len(caps), 1)
            self.assertIn(f"at most {record.DIGEST_CAP}", caps[0])


class CheckHeadersTest(unittest.TestCase):
    """Header presence and the no-table-row rule, without needing a git repo."""

    def test_passes_when_every_file_has_a_valid_header_and_no_readme_has_a_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            _write(
                root / "docs" / "handoffs" / "2026-09-01-example.md",
                "# 2026-09-01 -- Example\n**Summary:** Did the thing.\n**State:** Folded 2026-09-02\n",
            )
            _write(
                root / "docs" / "friction" / "2026-09-01-note.md",
                "# A tool fought back\n**Agent:** x\n**Summary:** Cost a turn.\n**Retro:** Applied\n",
            )
            self.assertEqual(check_docs.check_headers(root), [])

    def test_flags_a_handoff_missing_its_summary_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            _write(root / "docs" / "handoffs" / "2026-09-01-example.md", "# 2026-09-01 -- Example\n\nNo header.\n")
            findings = check_docs.check_headers(root)
            self.assertEqual(len(findings), 1)
            # rel() joins with the OS separator, so match the filename alone.
            self.assertIn("2026-09-01-example.md", findings[0])

    def test_flags_a_friction_note_missing_its_agent_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            _write(root / "docs" / "friction" / "2026-09-01-note.md", "## What I was doing\n\nNo title, no header.\n")
            findings = check_docs.check_headers(root)
            self.assertEqual(len(findings), 1)
            self.assertIn("2026-09-01-note.md", findings[0])

    def test_flags_a_table_row_left_in_a_readme(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            handoffs_readme = root / "docs" / "handoffs" / "README.md"
            handoffs_readme.write_text(
                "# Handoffs\n\n| Date | Task | State |\n|------|------|-------|\n"
                "| [2026-09-01](2026-09-01-example.md) | A task | Open |\n",
                encoding="utf-8",
            )
            _write(
                root / "docs" / "handoffs" / "2026-09-01-example.md",
                "# 2026-09-01 -- Example\n**Summary:** A task.\n**State:** Open\n",
            )
            findings = check_docs.check_headers(root)
            self.assertEqual(len(findings), 1)
            self.assertIn("README.md", findings[0])
            self.assertIn("table row", findings[0])

    def test_flags_a_link_inside_a_header_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            _write(
                root / "docs" / "handoffs" / "2026-09-01-example.md",
                "# 2026-09-01 -- Example\n**Summary:** See [the other one](2026-09-02-x.md).\n"
                "**State:** Open\n",
            )
            findings = check_docs.check_headers(root)
            self.assertEqual(len(findings), 1)
            self.assertIn("Summary", findings[0])
            self.assertIn("link", findings[0])

    def test_flags_a_retro_value_outside_the_vocabulary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            _write(
                root / "docs" / "friction" / "2026-09-01-note.md",
                "# A tool fought back\n**Agent:** x\n**Summary:** Cost a turn.\n"
                "**Retro:** Not yet processed\n",
            )
            findings = check_docs.check_headers(root)
            self.assertEqual(len(findings), 1)
            self.assertIn("Retro", findings[0])

    def test_recognised_retro_words_all_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            for i, word in enumerate(record.RETRO_WORDS):
                _write(
                    root / "docs" / "friction" / f"2026-09-{i + 1:02d}-note.md",
                    f"# Note {i}\n**Agent:** x\n**Summary:** y\n**Retro:** {word} -- detail\n",
                )
            self.assertEqual(check_docs.check_headers(root), [])

    def test_ignores_readme_itself_as_an_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _scaffold(root)
            # A bare README with no dated entries at all is not a missing header.
            self.assertEqual(check_docs.check_headers(root), [])


class CheckHeadersBranchStalenessTest(unittest.TestCase):
    """The one git-backed claim `check_headers` still verifies: an open State's branch."""

    def _repo_with_merged_branch(self, root: Path) -> None:
        """A `main` with one commit, and a `done-work` branch already merged into it."""
        _git(root, "init", "-q", "-b", "main")
        _git(root, "commit", "--allow-empty", "-q", "-m", "root")
        _git(root, "checkout", "-q", "-b", "done-work")
        _git(root, "commit", "--allow-empty", "-q", "-m", "work")
        _git(root, "checkout", "-q", "main")
        _git(root, "merge", "-q", "--no-ff", "-m", "merge", "done-work")

    def test_flags_an_open_handoff_naming_a_branch_main_already_merged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo_with_merged_branch(root)
            _scaffold(root)
            _write(
                root / "docs" / "handoffs" / "2026-09-01-example.md",
                "# 2026-09-01 -- Example\n**Summary:** A task.\n**State:** Open -- branch `done-work`\n",
            )
            findings = check_docs.check_headers(root)
            self.assertEqual(len(findings), 1)
            self.assertIn("done-work", findings[0])
            self.assertIn("merged", findings[0])

    def test_does_not_flag_a_folded_handoff_naming_the_same_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo_with_merged_branch(root)
            _scaffold(root)
            _write(
                root / "docs" / "handoffs" / "2026-09-01-example.md",
                "# 2026-09-01 -- Example\n**Summary:** A task.\n**State:** Folded 2026-09-02 -- branch `done-work`\n",
            )
            self.assertEqual(check_docs.check_headers(root), [])


class BranchMergedTest(unittest.TestCase):
    """`branch_merged`'s three answers, which only its True was covered for.

    `stale_open_claim` reaches this through `check_headers`, and every case there was a
    branch main already held -- so mutating the merged test to `return ahead is not None`
    left the whole suite green. False is the answer a handoff relies on to stay open.
    """

    def _repo(self, root: Path) -> None:
        _git(root, "init", "-q", "-b", "main")
        _git(root, "commit", "--allow-empty", "-q", "-m", "root")
        _git(root, "checkout", "-q", "-b", "done-work")
        _git(root, "commit", "--allow-empty", "-q", "-m", "work")
        _git(root, "checkout", "-q", "main")
        _git(root, "merge", "-q", "--no-ff", "-m", "merge", "done-work")
        _git(root, "checkout", "-q", "-b", "still-open")
        _git(root, "commit", "--allow-empty", "-q", "-m", "not merged yet")
        _git(root, "checkout", "-q", "main")
        _git(root, "branch", "just-branched", "main")

    def test_a_merged_branch_is_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            self.assertIs(check_docs.branch_merged(root, "done-work"), True)

    def test_a_branch_main_does_not_hold_is_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            self.assertIs(check_docs.branch_merged(root, "still-open"), False)

    def test_a_branch_with_no_commits_of_its_own_is_false(self):
        # Sitting exactly on main is not "merged" -- nothing was. `trunk.ahead` alone
        # would call this 0 and say True, which is why the oid comparison stays.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            self.assertIs(check_docs.branch_merged(root, "just-branched"), False)

    def test_a_branch_git_has_never_heard_of_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            self.assertIsNone(check_docs.branch_merged(root, "no-such-branch"))


class CheckInvestigationsParkedTest(unittest.TestCase):
    """Nothing in `docs/investigations/` may influence a design decision until it is unparked.

    Four product docs address one file in that folder by name, so a reader arrives at the
    file and never sees the folder's rule. The first version of this check read ten lines,
    required a list dash, and matched "parked" as a substring; four of the five cases below
    passed it.
    """

    def status(self, *files: tuple[str, str]) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "docs" / "investigations"
            folder.mkdir(parents=True)
            for name, text in files:
                (folder / name).write_text(text, encoding="utf-8")
            return check_docs.check_investigations_parked(root)

    def test_a_status_saying_parked_passes(self):
        self.assertEqual(self.status(("a.md", "# A\n\n- **Status:** parked research.\n")), [])

    def test_a_status_not_saying_parked_is_a_finding(self):
        found = self.status(("a.md", "# A\n\n- **Status:** in progress, started today\n"))
        self.assertEqual(len(found), 1)
        self.assertIn("a.md", found[0])

    def test_unparked_is_not_parked(self):
        # "parked" is a substring of "unparked", which is the opposite claim.
        self.assertEqual(len(self.status(("a.md", "- **Status:** unparked 2026-09-01\n"))), 1)

    def test_a_negated_status_is_not_parked(self):
        for said in ("not parked", "no longer parked", "never parked"):
            with self.subTest(said=said):
                self.assertEqual(len(self.status(("a.md", f"- **Status:** {said}.\n"))), 1)

    def test_a_status_without_the_list_dash_is_still_read(self):
        self.assertEqual(len(self.status(("a.md", "**Status:** in progress\n"))), 1)

    def test_a_status_below_the_first_ten_lines_is_still_read(self):
        body = "# A\n" + "\n".join(f"line {n}" for n in range(20))
        self.assertEqual(len(self.status(("a.md", body + "\n- **Status:** in progress\n"))), 1)

    def test_a_file_with_no_status_line_is_exempt(self):
        # The capture kit is written for someone outside the project and has no header.
        self.assertEqual(self.status(("kit.md", "# Capturing your games\n\nDo this.\n")), [])

    def test_it_reaches_a_nested_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "docs" / "investigations" / "tta-events" / "ws"
            nested.mkdir(parents=True)
            (nested / "README.md").write_text("- **Status:** in progress\n", encoding="utf-8")
            self.assertEqual(len(check_docs.check_investigations_parked(root)), 1)


if __name__ == "__main__":
    unittest.main()
