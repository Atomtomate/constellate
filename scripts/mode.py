"""Which mode a lane runs in: unattended, the default, or attended, which the owner's own
checkout declares.

Unattended is the standing mode whenever the owner is not steering (their decision, 2026-09-14,
recorded in the fleet manual), so nothing declares it; attended is `git config --worktree
constellate.mode attended` (this clone has `extensions.worktreeConfig` on). Both hooks read it:
`hook_stop.py`, which refuses an unattended turn end while the branch has code and no pass, and
`hook_session_start.py`, which prints it. One reader, so the key and its default are spelled
once (architecture review of PR #238); `.claude/agents.local.md`, "Modes", says what each
expects of the session.

Not a script -- it answers nothing and exits nowhere.
"""

from __future__ import annotations

from pathlib import Path

import git_cmd

KEY = "constellate.mode"
UNATTENDED = "unattended"
ATTENDED = "attended"


def read(root: Path) -> str:
    """`attended` when the worktree says so, else `unattended`."""
    return ATTENDED if git_cmd.first(root, "config", "--get", KEY) == ATTENDED else UNATTENDED
