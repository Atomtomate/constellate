"""`git_cmd` drops the caller's `GIT_*` names, and no script spawns git around it.

Why it matters is `git_cmd.py`'s to say. What is here is the part that failed: the strip was
written, every gate passed, and nothing went red when a later call site forgot it.

So the test that matters is not "does it strip" -- it is "does anything fail when it stops".
`test_a_lost_strip_is_caught` reverts the strip in place and asserts the rest of this class
goes red; `test_no_script_spawns_git_outside_git_cmd` reads the source, because a new call
site cannot be caught by running anything.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import git_cmd  # noqa: E402


class GitCmdEnvTest(unittest.TestCase):
    """A hostile `GIT_DIR` must not decide which repository `cwd` asked about."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        git_cmd.run("init", "-q", "-b", "main", cwd=self.repo, check=True)
        (self.repo / "only.txt").write_text("x", encoding="utf-8")
        git_cmd.run("add", "-A", cwd=self.repo, check=True)
        git_cmd.run(
            "-c", "user.name=t", "-c", "user.email=t@e.x", "commit", "-qm", "one",
            cwd=self.repo, check=True,
        )

    def test_the_names_are_gone(self):
        with mock.patch.dict("os.environ", {"GIT_DIR": "/elsewhere/.git", "GIT_X": "1"}):
            self.assertNotIn("GIT_DIR", git_cmd._env())
            self.assertNotIn("GIT_X", git_cmd._env())

    def test_everything_else_survives(self):
        with mock.patch.dict("os.environ", {"PATH_LIKE_THING": "kept"}):
            self.assertEqual(git_cmd._env().get("PATH_LIKE_THING"), "kept")

    def test_a_hostile_git_dir_does_not_redirect_a_read(self):
        # Without the strip this answers about /elsewhere and fails or lies.
        other = Path(self.tmp.name) / "other" / ".git"
        with mock.patch.dict("os.environ", {"GIT_DIR": str(other)}):
            self.assertEqual(git_cmd.first(self.repo, "rev-parse", "--abbrev-ref", "HEAD"), "main")
            self.assertEqual(git_cmd.lines(self.repo, "ls-tree", "--name-only", "HEAD"), ["only.txt"])

    def test_a_hostile_git_index_file_does_not_redirect_a_write(self):
        # This is the clobber itself: `git add` in one repository writing another's index.
        victim = Path(self.tmp.name) / "victim.index"
        victim.write_bytes(b"not an index")
        before = victim.read_bytes()
        (self.repo / "second.txt").write_text("y", encoding="utf-8")
        with mock.patch.dict("os.environ", {"GIT_INDEX_FILE": str(victim)}):
            git_cmd.run("add", "-A", cwd=self.repo, check=True)
        self.assertEqual(victim.read_bytes(), before, "the write reached the wrong index")

    def test_a_caller_may_not_pass_its_own_env(self):
        with self.assertRaises(TypeError):
            git_cmd.run("status", cwd=self.repo, env={"GIT_DIR": "/elsewhere"})

    def test_a_lost_strip_is_caught(self):
        """Revert the strip and confirm this class goes red. The guard on the guard."""
        import os

        with mock.patch.object(git_cmd, "_env", lambda: dict(os.environ)):
            with mock.patch.dict("os.environ", {"GIT_DIR": str(Path(self.tmp.name) / "no.git")}):
                # With the strip gone, `cwd` no longer decides: the read is answered elsewhere.
                self.assertNotEqual(
                    git_cmd.first(self.repo, "rev-parse", "--abbrev-ref", "HEAD"),
                    "main",
                    "reverting the strip changed nothing -- this suite cannot see it break",
                )


class NoGitSpawnOutsideGitCmdTest(unittest.TestCase):
    """One front door, checked in the source; a new call site cannot be caught by running."""

    def test_no_script_spawns_git_outside_git_cmd(self):
        offenders = []
        for path in sorted(SCRIPTS.glob("*.py")):
            if path.name == "git_cmd.py":
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if '["git"' in line or '"git",' in line.replace('["git",', ""):
                    offenders.append(f"{path.name}:{number}")
        self.assertEqual(
            offenders, [], "spawn git through git_cmd.run, which drops the inherited GIT_* names"
        )


if __name__ == "__main__":
    unittest.main()
