"""Put the tree and the open work in front of a session before it does anything.

Runs from the `SessionStart` hook in `.claude/settings.json` on a new or cleared session, not a
resume. What it prints becomes the session's context: every worktree and whether it is clean,
the handoffs still open, and `open_work.py --fetch`, the queue the closing step reads. A session
that ended without closing leaves drift; this is where the next session sees it, rather than a
retro weeks later. When `gh` is not there, `open_work.py` runs without `--fetch` and lists the
record half alone. It never fails the start: a script that did not run is one line.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import mode

ROOT = Path(__file__).resolve().parent.parent


def run(*args: str, timeout: int = 60) -> tuple[int, str]:
    """A script's exit code and combined output, or a one-line note when it did not run."""
    try:
        result = subprocess.run(
            [sys.executable, *args], cwd=ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
        return result.returncode, (result.stdout + result.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, f"{args[0]}: did not run ({exc})"


def main() -> int:
    """Print the digest; exit 0 whatever happened."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("Session start — the tree and the open work (scripts/hook_session_start.py):")
    print(
        f"Mode: {mode.read(ROOT)} "
        f"(`git config --worktree {mode.KEY} {mode.UNATTENDED}` declares the other)"
    )
    print(run("scripts/worktree_status.py")[1])
    print(run("scripts/record_index.py", "handoffs", "--open")[1])
    code, work = run("scripts/open_work.py", "--fetch", timeout=120)
    if code != 0:
        print("open_work.py --fetch did not run; the record half alone:")
        work = run("scripts/open_work.py")[1]
    print(work)
    return 0


if __name__ == "__main__":
    sys.exit(main())
