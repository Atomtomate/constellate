"""Tests for the poller entry point, ``python -m constellate.poll``.

The command runs as a subprocess so ``__name__`` is ``"__main__"``, as it is when the scheduler
fires it: that is the one context in which a logger named by ``__name__`` would be no child of
the ``constellate`` logger and the promised line would be dropped.
"""

import subprocess
import sys

import pytest


@pytest.fixture(scope="module")
def poll_run() -> subprocess.CompletedProcess[str]:
    """One run of the command for the module's tests to read."""
    return subprocess.run(
        [sys.executable, "-m", "constellate.poll"], capture_output=True, text=True, check=False
    )


def test_poll_emits_the_no_source_line(poll_run):
    assert "poll: no sources configured" in poll_run.stdout


def test_poll_exits_zero(poll_run):
    assert poll_run.returncode == 0
