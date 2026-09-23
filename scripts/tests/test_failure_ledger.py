"""Tests for `scripts/failure_ledger.py`, the retro's inputs compiled since a named handoff.

Stdlib-only (`unittest`), matching `scripts/README.md`'s rule; run with
`python -m unittest discover scripts/tests`. The parsers are tested on strings; the "since"
rule is tested against a throwaway git repository, because which files a range of commits
added is the one thing a fixture on disk cannot say -- and the range is where a reading
would go wrong quietly (a handoff dated the retro's own day, a file added and deleted).
"""

import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gitenv import git_env  # noqa: E402
import failure_ledger  # noqa: E402

# A commit needs an author, and a CI runner carries no global identity -- the same reason
# `test_check_docs.py` sets these for its repository fixture.
_GIT_ENV = git_env()


def _git(root: Path, *args: str) -> str:
    """Run git in `root`, failing loudly, and return what it printed."""
    done = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True, env=_GIT_ENV
    )
    return done.stdout.strip()


def _write(path: Path, text: str) -> None:
    """Create `path`'s parent directories and write `text` to it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class _Capture(io.StringIO):
    """A `StringIO` that tolerates `main()`'s `sys.stdout.reconfigure(...)` call."""

    def reconfigure(self, **_kwargs) -> None:
        pass


def _run(root: Path, *extra: str) -> tuple[int, str]:
    """Run `failure_ledger.main()` against `root` and return its exit status and output."""
    argv = sys.argv
    sys.argv = ["failure_ledger.py", "--root", str(root), *extra]
    out = _Capture()
    try:
        with redirect_stdout(out):
            code = failure_ledger.main()
    finally:
        sys.argv = argv
    return code, out.getvalue()


HANDOFF_HEADER = "# {title}\n**Summary:** {summary}\n**State:** Open\n\n"
NOTE = "# A note\n**Agent:** `x`\n**Summary:** cost a turn\n**Retro:** Unprocessed — next retro\n"


class AddedByKindTest(unittest.TestCase):
    """The census reads a merge's lines by path and then by content, over its first parent."""

    def test_a_merged_branch_is_counted_by_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git(root, "init", "-q", "-b", "main")
            _write(root / "README.md", "# r\n")
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "root")
            _git(root, "checkout", "-q", "-b", "claude/x")
            _write(root / "api" / "a.py", '"""Doc.\n\nMore.\n"""\n\n# why\nx = 1\ny = 2\n')
            _write(root / "api" / "tests" / "test_a.py", "def test():\n    assert 1\n")
            _write(root / "web" / "b.ts", "// c\nconst a = 1;\n")
            _write(root / "docs" / "h.md", "one\ntwo\n")
            _write(root / "api" / "openapi.json", "{}\n")
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "the lane")
            _git(root, "checkout", "-q", "main")
            _git(root, "merge", "-q", "--no-ff", "--no-edit", "claude/x")
            merges = failure_ledger.merged_since(root, _git(root, "rev-parse", "main~1"))
            self.assertEqual([m[2] for m in merges], ["Merge branch 'claude/x'"])
            counts = failure_ledger.added_by_kind(root, merges[0][1])
            self.assertEqual(counts["prod"], 3)  # x = 1, y = 2, const a = 1
            self.assertEqual(counts["test"], 2)
            self.assertEqual(counts["cmnt"], 7)  # 4 docstring lines, a blank, `# why`, `// c`
            self.assertEqual(counts["prose"], 2)
            self.assertEqual(counts["gen"], 1)


class SectionsTest(unittest.TestCase):
    """`sections` finds the retro's sections by heading or bold label, once each."""

    def test_heading_section_runs_to_the_next_heading_of_its_level(self):
        text = (
            "# Title\n\n## Review pass\n\nActed on a.\n\n### Dismissed\n\n- b, because.\n\n"
            "## What remains open\n\n- c\n"
        )
        found = failure_ledger.sections(text)
        self.assertEqual([label for label, _ in found], ["Review pass"])
        body = "\n".join(found[0][1])
        self.assertIn("Acted on a.", body)
        self.assertIn("- b, because.", body)  # the nested Dismissed rides inside, once
        self.assertNotIn("- c", body)

    def test_dressed_headings_and_bold_labels_count(self):
        # The bold labels sit under a heading the retro does not read, so each is its own
        # section; under "Review pass" they would ride inside it instead.
        text = (
            "# Title\n\n## The review pass\n\nx\n\n## Traps worth not rediscovering\n\ny\n\n"
            "## How it was verified\n\n**Not verified:** rendering in a browser.\nSecond line.\n\n"
            "Unrelated paragraph.\n\n**Dismissed findings, with reasons:** z\n"
        )
        found = failure_ledger.sections(text)
        self.assertEqual(
            [label for label, _ in found],
            [
                "The review pass",
                "Traps worth not rediscovering",
                "Not verified",
                "Dismissed findings, with reasons",
            ],
        )
        self.assertEqual(found[2][1], ["**Not verified:** rendering in a browser.", "Second line."])

    def test_the_title_line_is_never_a_section(self):
        # A handoff titled after its review pass is about one; reading the title as a
        # level-1 section would swallow the whole file, headings and all.
        text = "# Placeholder sign-in, and the review pass on it\n\n## Review pass\n\nx\n\n## Other\n\ny\n"
        found = failure_ledger.sections(text)
        self.assertEqual([label for label, _ in found], ["Review pass"])
        self.assertEqual(found[0][1], ["x"])

    def test_a_bold_label_paragraph_stops_at_a_heading(self):
        # No blank line between the paragraph and the next heading: the heading is still a
        # heading, and its section must not vanish inside the paragraph.
        text = "# T\n\n**Not verified:** x.\n## Review pass\n\ny\n"
        found = failure_ledger.sections(text)
        self.assertEqual([label for label, _ in found], ["Not verified", "Review pass"])
        self.assertEqual(found[0][1], ["**Not verified:** x."])
        self.assertEqual(found[1][1], ["y"])

    def test_a_heading_inside_a_fence_is_not_a_heading(self):
        text = "# Title\n\n## Review pass\n\n```\n# not a heading\n## Traps\n```\nafter\n\n## Next\n"
        found = failure_ledger.sections(text)
        self.assertEqual([label for label, _ in found], ["Review pass"])
        self.assertIn("after", found[0][1])


class PredictionsTest(unittest.TestCase):
    """`predictions` wants the heading named exactly Predictions, not "Predictions checked"."""

    def test_exact_heading_only(self):
        text = (
            "# 2026-09-12 — Retro v2: the predictions checked\n\n"
            "## Predictions checked (retro v1)\n\n1. *Old.* Held.\n\n"
            "## What worked\n\nx\n\n## Predictions\n\n1. **New.** The next run shows X.\n"
        )
        self.assertEqual(failure_ledger.predictions(text), ["1. **New.** The next run shows X."])

    def test_none_when_absent(self):
        self.assertIsNone(failure_ledger.predictions("# T\n\n## Predictions checked\n\n1. x\n"))


class ReportSummaryTest(unittest.TestCase):
    """`report_summary` reads the verdict in the shapes the reports have used, and the findings."""

    def test_bold_verdict_line_and_numbered_findings(self):
        text = (
            "# pr-tech-review — x\n\n**Verdict: changes requested.** One real miss.\n\n"
            "## Findings\n\n### 1. `a.py:1` — bad\n\ntext\n\n### 2. `b.py:2` — worse\n"
        )
        verdict, findings = failure_ledger.report_summary(text)
        self.assertEqual(verdict, "changes requested.")
        self.assertEqual(findings, ["1. `a.py:1` — bad", "2. `b.py:2` — worse"])

    def test_bold_label_verdict_and_lettered_findings(self):
        # The two shapes one real report each uses: the label alone in bold, and findings
        # numbered F1, F2 with a dash instead of a stop.
        text = (
            "# r\n\n**Verdict:** changes requested.\n\n"
            "### F1 — `docs/07-roadmap.md` still lists #54 (blocking)\n\ntext\n\n### F2 — second\n"
        )
        verdict, findings = failure_ledger.report_summary(text)
        self.assertEqual(verdict, "changes requested.")
        self.assertEqual(
            findings, ["F1. `docs/07-roadmap.md` still lists #54 (blocking)", "F2. second"]
        )

    def test_verdict_heading_takes_its_first_paragraph(self):
        text = "# r\n\n## Findings\n\n## Verdict\n\nYes, with edits.\nSecond line.\n\nNot this.\n"
        verdict, _ = failure_ledger.report_summary(text)
        self.assertEqual(verdict, "Yes, with edits. Second line.")

    def test_overall_heading_counts_too(self):
        text = "# r\n\n## 1. thing\n\nx\n\n## Overall\n\nNo blocking findings.\n"
        verdict, findings = failure_ledger.report_summary(text)
        self.assertEqual(verdict, "No blocking findings.")
        self.assertEqual(findings, ["1. thing"])

    def test_none_stated(self):
        self.assertEqual(failure_ledger.report_summary("# r\n\nprose only\n"), (None, []))


class SinceTest(unittest.TestCase):
    """The range: what a commit after the one adding the cut handoff added, deleted included."""

    def _repo(self, root: Path) -> None:
        _git(root, "init", "-q", "-b", "main")
        _write(
            root / "docs/handoffs/2026-09-01-old.md",
            HANDOFF_HEADER.format(title="Old", summary="before") + "## Review pass\n\nold pass\n",
        )
        _write(root / "docs/friction/2026-09-01-old-note.md", NOTE)
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "The record before the retro")
        _write(
            root / "docs/handoffs/2026-09-02-retro.md",
            HANDOFF_HEADER.format(title="Retro", summary="the cut")
            + "## Predictions checked\n\n1. earlier prediction, held\n\n"
            "## Predictions\n\n1. The next run shows X.\n   Continued.\n2. And Y.\n\n"
            "## Needs a decision\n\n1. **Fold or file.** Leaning fold.\n",
        )
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "The retro")
        _write(
            root / "docs/handoffs/2026-09-03-new.md",
            HANDOFF_HEADER.format(title="New", summary="after")
            + "## Review pass\n\nActed on a.\n\n### Dismissed\n\n- b, because.\n\n"
            "## How it was verified\n\n**Not verified:** rendering.\n\n"
            "## What carried it\n\n- the brief\n",
        )
        _write(root / "docs/friction/2026-09-03-stays.md", NOTE)
        _write(root / "docs/friction/2026-09-03-goes.md", NOTE)
        # Added in the range but not an entry by the contract: never a handoff to the ledger.
        _write(root / "docs/handoffs/README.md", "# Handoffs\n\nProse.\n\n## Review pass\n\nnot one\n")
        _write(
            root / "docs/reviews/x/pr-tech-review.md",
            "# pr-tech-review — x\n\n**Verdict: changes requested.**\n\n### 1. `a.py:1` — bad\n",
        )
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "Act on the review pass: a, b")
        _git(root, "rm", "-q", "docs/friction/2026-09-03-goes.md")
        _git(root, "commit", "-q", "-m", "Tidy the record")
        # A branch forked before the cut, merged after it, and a note born inside the merge
        # commit itself: the merge's diff against the side parent alone would show the cut's
        # own record as "added"; the combined diff added_since reads lists only the note.
        _git(root, "checkout", "-q", "-b", "side", "HEAD~3")
        _write(root / "docs/friction/2026-09-04-on-side.md", NOTE)
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "A note on a side branch")
        _git(root, "checkout", "-q", "main")
        _git(root, "merge", "-q", "--no-ff", "--no-commit", "side")
        _write(root / "docs/friction/2026-09-04-in-merge.md", NOTE)
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "Merge side, and the note written while resolving it")
        # A note present at the cut, deleted after it and added back — a revert and a re-land.
        # It is "since" again; the form that subtracted the cut's tree could never say so.
        _git(root, "rm", "-q", "docs/friction/2026-09-01-old-note.md")
        _git(root, "commit", "-q", "-m", "Revert the old note")
        _write(root / "docs/friction/2026-09-01-old-note.md", NOTE)
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "Re-land the old note")

    def test_since_the_named_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            code, out = _run(root, "--since", "2026-09-02-retro.md")
            self.assertEqual(code, 0)
            # the cut's own predictions, and only the new ones
            self.assertIn("1. The next run shows X.", out)
            self.assertIn("Continued.", out)
            self.assertNotIn("earlier prediction", out)
            # and the cut's open decisions, which nothing else reads
            self.assertIn("== Needs a decision of 2026-09-02-retro.md", out)
            self.assertIn("1. **Fold or file.** Leaning fold.", out)
            # handoffs added after the cut, with their sections; not the one before it
            self.assertIn("docs/handoffs/2026-09-03-new.md", out)
            self.assertIn("Summary: after", out)
            self.assertIn("-- Review pass", out)
            self.assertIn("- b, because.", out)
            self.assertNotIn("-- Dismissed", out)  # nested: printed inside its parent, once
            self.assertIn("-- Not verified", out)
            self.assertIn("-- What carried it", out)
            self.assertNotIn("old pass", out)
            self.assertNotIn("2026-09-01-old.md", out)
            self.assertNotIn("README.md", out)
            self.assertNotIn("not one", out)
            # friction notes since, with the verdict line; the deleted one named as gone
            self.assertIn("docs/friction/2026-09-03-stays.md", out)
            self.assertIn("Retro: Unprocessed", out)
            # present at the cut, but deleted and added back after it: since, like a new note
            self.assertIn("docs/friction/2026-09-01-old-note.md", out)
            self.assertIn("gone again, as of HEAD (1)", out)
            self.assertIn("docs/friction/2026-09-03-goes.md", out)
            # a note born inside a merge commit and one the merge carried across are since;
            # the cut's own handoff, which the merge diffs as "added" against one parent, is not
            self.assertIn("docs/friction/2026-09-04-in-merge.md", out)
            self.assertIn("docs/friction/2026-09-04-on-side.md", out)
            self.assertNotIn("Summary: the cut", out)
            # the report's verdict and findings, and the Act-on commit but not the other
            self.assertIn("Verdict: changes requested.", out)
            self.assertIn("1. `a.py:1` — bad", out)
            self.assertIn("Act on the review pass: a, b", out)
            # the census lists every merged commit by subject; the Act-on listing does not
            self.assertNotIn("Tidy the record", out.split("== Merged into ")[0])

    def test_default_cut_is_the_newest_retro_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            code, out = _run(root)
            self.assertEqual(code, 0)
            self.assertIn("since docs/handoffs/2026-09-02-retro.md", out)

    def test_an_unknown_cut_is_the_one_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            code, out = _run(root, "--since", "2026-09-09-nope.md")
            self.assertEqual(code, 1)
            self.assertIn("no such handoff", out)

    def test_an_uncommitted_cut_is_an_error_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            _write(root / "docs/handoffs/2026-09-09-retro.md", HANDOFF_HEADER.format(title="R", summary="s"))
            code, out = _run(root)  # the newest retro by name is the uncommitted one
            self.assertEqual(code, 1)
            self.assertIn("is it committed", out)


if __name__ == "__main__":
    unittest.main()
