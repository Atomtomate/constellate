"""The environment a test's throwaway git repository must be run with.

Four test modules build one of these, and every one of them inherited `os.environ` whole.
That is fine from a shell and wrong from a git hook: `.githooks/pre-commit` runs
`scripts/gates.py`, git exports `GIT_DIR` and `GIT_INDEX_FILE` pointing at the *real*
repository, and a nested `git commit` in a temp directory then commits against the outer
index and fails. Thirteen tests failed that way while passing standalone, so the suite
said the working tree was broken when nothing was.

Stripping every `GIT_*` name rather than the two observed ones: `GIT_WORK_TREE`,
`GIT_OBJECT_DIRECTORY`, `GIT_COMMON_DIR` and the rest reach a child the same way, and a
test repository has no reason to inherit any of them.
"""

import os

_IDENTITY = {
    # A commit needs an author, and a CI runner carries no global identity.
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
}


def git_env(**overrides: str) -> dict[str, str]:
    """`os.environ` with every `GIT_*` name dropped, then a test identity, then `overrides`."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(_IDENTITY)
    env.update(overrides)
    return env
