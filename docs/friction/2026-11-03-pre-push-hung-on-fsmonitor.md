# The pre-push gate hung on a test repository's filesystem monitor
**Agent:** the session on PR #27, briefed by the coordinator
**Summary:** A push sat over ten minutes on a `git add -A` inside the script tests, because the system gitconfig turns on `core.fsmonitor` and each temp repository starts a daemon; it cost a failed push and a retry.
**Retro:** Unprocessed

**What you were doing.** Pushing `claude/m1-record-step` for the first time, a documents-only diff,
through `.githooks/pre-push`, which runs `python -m unittest discover scripts/tests`.

**What happened.** The Bash call hit its 600-second timeout. The tree under the hook ended in `git
add -A`, at 0.016 s of CPU after ten minutes, in a temp repository from
`scripts/tests/test_git_cmd.py` holding `index.lock` and a `.git/fsmonitor--daemon` directory. `git
config --show-origin --get core.fsmonitor` said `file:C:/Program Files/Git/etc/gitconfig true`, and
46 `git fsmonitor--daemon` processes were running. Stopping that one child let the suite finish red,
so the gate refused the push. A retry was still running when the session ended, so it may have hung
too. After the machine restarted, the next push passed in under a minute.

**What it cost.** Over ten minutes, one refused push, and a retry lost to the restart. The chained
`gh pr create` also failed, on a branch that was not there.

**What would remove it.** Have `scripts/git_cmd.py` and the tests' own `_git` pass `-c
core.fsmonitor=false`, so a throwaway repository never starts a daemon: the tests stop leaking them
and stop being able to hang on one. Not verified that this is the only cause. The system setting is
the owner's, and a session should not change it.
