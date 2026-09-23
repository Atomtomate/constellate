"""Which mode a lane runs in: attended, or unattended with nobody to say continue.

Declared per worktree -- `git config --worktree constellate.mode unattended` (this clone has
`extensions.worktreeConfig` on) -- and read by both hooks: `hook_stop.py`, which refuses an
unattended turn end while the branch has code and no pass, and `hook_session_start.py`, which
prints it. One reader, so the key and its default are spelled once (architecture review of
PR #238); `.claude/agents.local.md`, "Review reports", says how a session declares it.

Not a script -- it answers nothing and exits nowhere.
"""

from __future__ import annotations

from pathlib import Path

import git_cmd

KEY = "constellate.mode"
UNATTENDED = "unattended"
ATTENDED = "attended"


def read(root: Path) -> str:
    """`unattended` when the worktree says so, else `attended`."""
    return git_cmd.first(root, "config", "--get", KEY) or ATTENDED
