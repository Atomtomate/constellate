"""Run git in a directory and hand back what it printed, or nothing.

Every script here asks git something -- a ref, a log, a config value -- and by 2026-09-17 five
of them carried their own five-line `subprocess.run` with the same "empty on failure" guard
(parsimony review of PR #238). A failing command is an empty answer, never an exception: a
check that cannot ask git has one fact fewer, which is its caller's to report.

**Every git spawn by a script here goes through `run` below**, which is the only place the
inherited `GIT_*` names are dropped. `scripts/tests/` is the one exception and keeps its own
(`gitenv.py`): a test repository needs `GIT_AUTHOR_*` added back, which `run` will not do.

A caller that spells its own `subprocess.run(["git", ...])` is answered about whatever
repository the environment names, which under a git hook is the one being committed to and
not the one it asked about. That is not a style preference: it cost this
repository a pushed commit that deleted the application
(`docs/friction/2026-09-22-the-index-clobber-fix-lived-in-a-hook-that-never-runs.md`).

Not a script -- it answers nothing and exits nowhere.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _env() -> dict[str, str]:
    """`os.environ` without the `GIT_*` names, so `cwd` is what decides which repository.

    `git commit` exports `GIT_DIR`, `GIT_WORK_TREE` and `GIT_INDEX_FILE`, every child inherits
    them, and an absolute `GIT_DIR` beats a `cwd`. Private, and applied by `run` rather than
    passed by callers: sixteen call sites that must remember an argument is a rule, and the
    five that forgot it were in the one script that runs `git worktree remove --force`.
    """
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def run(*args: str, **kwargs) -> subprocess.CompletedProcess:
    """Spawn git with the inherited `GIT_*` names dropped; `kwargs` are `subprocess.run`'s.

    `capture_output` defaults on, since nothing here wants git writing to the caller's stdout.
    `env` is not a caller's to set -- passing one is a `TypeError` rather than a quiet reopening
    of the hole this exists to close.
    """
    if "env" in kwargs:
        raise TypeError("git_cmd.run sets env itself; a caller that overrides it can be lied to")
    kwargs.setdefault("capture_output", True)
    return subprocess.run(["git", *args], env=_env(), **kwargs)


def lines(root: Path, *args: str) -> list[str]:
    """git's stdout lines in `root`; a failing command is an empty list."""
    done = run(*args, cwd=root, text=True, encoding="utf-8")
    return done.stdout.splitlines() if done.returncode == 0 else []


def first(root: Path, *args: str) -> str | None:
    """git's first stdout line in `root`, stripped; None when it fails or prints nothing."""
    out = lines(root, *args)
    return out[0].strip() if out else None
