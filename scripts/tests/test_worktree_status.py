"""Tests for `scripts/worktree_status.py`: scoping, the reading of a worktree, and `--remove`.

Stdlib-only (`unittest`), matching `scripts/README.md`'s rule -- no venv, nothing
installed. Run with `python -m unittest discover scripts/tests`.

Most of these fake the module's own git helpers rather than building a repository: a
two-line monkeypatch of `_git` or `read_status` stands in for one, with no temp directory
and no subprocess. The exceptions are the tests of `unreconstructable`, `husks` and
`idle_hours`, which walk and stat real directories, so those build one in `tempfile`.

The case worth pinning in `hooks_path_finding` is the absolute path: a regression to
`value.endswith(".githooks")` would pass `/home/user/somewhere/.githooks` as fine, when it
is exactly the pinned-copy problem the check exists to catch.

`CurrentScopeTest` drives `main()` rather than a helper: `--current` gating on the main
checkout (#157) was a bug in `main()`, and a helper-only test would have missed it exactly
the way this suite did. So was a failed removal being hidden behind a dirty worktree.
"""

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import worktree_status  # noqa: E402

State = worktree_status.State


@contextlib.contextmanager
def patched(*targets):
    """Monkeypatch `(module, name, value)` triples for the block: the suite's one shape."""
    with contextlib.ExitStack() as stack:
        for target, name, value in targets:
            stack.enter_context(mock.patch.object(target, name, value))
        yield


def clean(merged: str | None = "on main", merged_as: int = 0, hand_written=()) -> State:
    """A worktree git read happily: nothing to report, and standing where `merged` says.

    `merged_as` is the squash path: `main` does not hold the HEAD, and a merged PR does.
    Normalised the way `read_state` normalises it, so no case here can assert about a
    state the script cannot produce -- `on main` and a PR number together is the pair
    `describe` and `sweep_one` used to have to disqualify by hand (#223 review).
    """
    on_trunk = merged == f"on {worktree_status.trunk.NAME}"
    return State(None, (0, 0, 0), hand_written, merged, 0 if on_trunk else merged_as, on_trunk)


#: The worktree the rule tests are about. One copy: `why_kept` and `sweep_one` decide about
#: the same shape, and a parameter added to one of them should not need three edits here.
#: `HEAD` is what the squash path proves itself against, so it is part of the shape.
LANE = {"worktree": "/wt/lane", "branch": "refs/heads/claude/lane", "HEAD": "a" * 40}

#: `merged_heads` as it comes back for `LANE`: PR #192 merged at exactly the commit LANE is on.
MERGED_AS_192 = {"claude/lane": (192, "a" * 40)}

#: What `read_state` makes of that: six commits `main` does not hold, all of them #192's.
SQUASHED = clean("ahead 6 of main", merged_as=192)


class HooksPathFindingTest(unittest.TestCase):
    """Each case fakes one `git config --show-origin --get core.hooksPath` answer."""

    LANE = Path("/repo/.claude/worktrees/lane")
    MAIN = Path("/repo")

    def _finding(self, git_output: str) -> str | None:
        with mock.patch.object(worktree_status, "_git", lambda *a, **k: git_output):
            return worktree_status.hooks_path_finding(self.LANE, self.MAIN)

    def test_relative_githooks_is_not_a_finding(self):
        self.assertIsNone(self._finding("file:/repo/.git/config\t.githooks\n"))

    def test_unset_is_a_finding(self):
        self.assertIsNotNone(self._finding(""))

    def test_absolute_path_ending_in_githooks_is_a_finding(self):
        # Regression guard: `value.endswith(".githooks")` would wrongly let this through.
        finding = self._finding("file:/repo/.git/config\t/home/user/somewhere/.githooks\n")
        self.assertIsNotNone(finding)
        self.assertIn("not `.githooks`", finding)

    def test_this_worktrees_own_githooks_in_absolute_form_is_not_a_finding(self):
        # #161: the desktop app writes this form into the worktrees it creates, so the
        # finding came back at the next close however often a pass had cleared it.
        own = self.LANE / ".githooks"
        self.assertIsNone(self._finding(f"file:config.worktree\t{own}\n"))

    def test_the_main_checkouts_githooks_in_absolute_form_is_not_a_finding(self):
        # The other form the app leaves: a worktree pointed at the one clone's copy. The
        # hook runs either way; only a branch that changed the hook would notice which.
        shared = self.MAIN / ".githooks"
        self.assertIsNone(self._finding(f"file:.git/config\t{shared}\n"))


class AgainstTrunkTest(unittest.TestCase):
    """#143: the half of the retro's worktree audit that was hand-run twice.

    Since #151 the count comes from `trunk.ahead`, so that is what these fake -- the same
    two-line monkeypatch `HooksPathFindingTest` uses on `_git`. What is left to this module
    is the reading of the count: zero is "on main", any other count is the distance to
    print, and None is no column at all.
    """

    def _against(self, count: int | None, ref: str | None = "origin/main"):
        with mock.patch.object(worktree_status.trunk, "ahead", lambda *a: count):
            return worktree_status.against_trunk(Path("."), ref)[0]

    def _holds(self, count: int | None, ref: str | None = "origin/main") -> bool:
        with mock.patch.object(worktree_status.trunk, "ahead", lambda *a: count):
            return worktree_status.against_trunk(Path("."), ref)[1]

    def test_a_count_of_zero_is_on_main(self):
        self.assertEqual(self._against(count=0), "on main")

    def test_the_fact_comes_back_beside_the_sentence(self):
        # The rule reads this, never the sentence: a decision that parses its own display
        # text is one that breaks when the text is reworded (#223 review).
        self.assertIs(self._holds(count=0), True)
        self.assertIs(self._holds(count=3), False)

    def test_a_worktree_git_cannot_place_is_not_held_by_main(self):
        # False rather than unknown, and the safe way round: nothing to delete here.
        self.assertIs(self._holds(count=None), False)
        self.assertIs(self._holds(count=3, ref=None), False)

    def test_a_branch_main_does_not_hold_says_how_far_ahead(self):
        self.assertEqual(self._against(count=3), "ahead 3 of main")

    def test_no_trunk_ref_says_nothing(self):
        # A fresh clone with neither `origin/main` nor `main` gets no column, not a guess.
        # Guarded here as well as in `trunk.ahead`, which this case never reaches.
        self.assertIsNone(self._against(count=3, ref=None))

    def test_a_count_git_could_not_give_says_nothing(self):
        # `trunk.ahead` is None for a commit this checkout does not hold. That must not
        # print "ahead None of main", and must not be read as zero either.
        self.assertIsNone(self._against(count=None))


class ReadStateTest(unittest.TestCase):
    """One reading, carrying everything the line and the rule each need."""

    def _state(self, complaint: str | None, merged_as: int) -> State:
        with patched(
            (worktree_status, "read_status", lambda path: (complaint, (0, 0, 0), ())),
            (worktree_status, "against_trunk", lambda path, ref: (self.column, self.held)),
        ):
            return worktree_status.read_state(Path("/wt/lane"), "origin/main", merged_as)

    column, held = "ahead 6 of main", False

    def test_the_pr_the_head_merged_as_is_carried(self):
        self.assertEqual(self._state(None, 192).merged_as, 192)

    def test_a_worktree_main_already_holds_needs_no_second_proof(self):
        # Normalised here so no reader re-applies the qualifier the field's own name
        # carries; `describe` and `sweep_one` each did (#223 review).
        with mock.patch.multiple(type(self), column="on main", held=True):
            state = self._state(None, 192)
        self.assertEqual((state.merged_as, state.on_trunk), (0, True))

    def test_a_worktree_git_will_not_read_carries_no_claim_about_a_pr(self):
        # Every other column is emptied on a refusal for the same reason (#172): an answer
        # git could not give must not reach the rule dressed as one it did.
        self.assertEqual(self._state("dubious ownership", 192).merged_as, 0)


class MainWiresTheSquashProofTest(unittest.TestCase):
    """#219 item 10: the feature reaches `read_state` at all.

    Every other case here fakes one side or the other, so dropping `merged_here(entry, heads)`
    from `main()`'s call disconnected the whole feature with the suite green -- reproduced by
    `pr-tech-review` on this branch. This is the wire, and nothing else pins it.
    """

    LANE = Path("/repo/.claude/worktrees/lane").resolve()

    def _merged_as(self, argv: list[str], merged: list[dict]) -> int:
        """What `main()` handed `read_state` for the lane worktree."""
        seen: list[int] = []

        def recorder(path, ref, merged_as):
            seen.append(merged_as)
            return clean()

        entries = [
            {"worktree": str(self.LANE.parent.parent.parent), "branch": "refs/heads/main"},
            {"worktree": str(self.LANE), "branch": "refs/heads/claude/lane", "HEAD": "a" * 40},
        ]
        with patched(
            (worktree_status, "worktrees", lambda repo: entries),
            (worktree_status, "read_state", recorder),
            (worktree_status, "merged_prs", lambda **kwargs: merged),
            (worktree_status, "hooks_path_finding", lambda *a: None),
            (worktree_status, "submodule_paths", lambda root: ()),
            (worktree_status, "ahead_behind", lambda path: None),
            (worktree_status, "sweep_one", lambda *a, **k: 0),
            (worktree_status, "sweep_husks", lambda *a, **k: None),
            (worktree_status.trunk, "ref", lambda root: "origin/main"),
            (worktree_status.trunk, "refresh", lambda root: None),
            (Path, "cwd", lambda: self.LANE),
            (sys, "argv", ["worktree_status.py", *argv]),
        ):
            # A wrapper, not a `StringIO`: `main()` reconfigures stdout's encoding first.
            with contextlib.redirect_stdout(io.TextIOWrapper(io.BytesIO(), encoding="utf-8")):
                worktree_status.main()
        return seen[-1]

    MERGED = [
        {
            "number": 192,
            "headRefName": "claude/lane",
            "headRefOid": "a" * 40,
            "baseRefName": "main",
        }
    ]

    def test_the_pr_reaches_the_reading_of_the_worktree(self):
        self.assertEqual(self._merged_as(["--remove", "--fetch"], self.MERGED), 192)

    def test_a_run_with_no_merged_list_hands_over_nothing(self):
        self.assertEqual(self._merged_as(["--remove"], []), 0)


class MergedPrsTest(unittest.TestCase):
    """When the merged list is fetched at all, and what happens when gh will not give it."""

    @staticmethod
    def _prs(*, merged=None, fetch=False, remove=True):
        return worktree_status.merged_prs(merged=merged, fetch=fetch, remove=remove, gh=None)

    def test_a_bare_run_asks_gh_nothing(self):
        # The case the closing step runs: pure git, offline, no wait on anything.
        with patched((worktree_status.gh_json, "load_or_none", self._never)):
            self.assertEqual(self._prs(), [])

    def test_a_listing_asks_nothing_even_with_fetch(self):
        # Only `--remove` consumes the answer, so only `--remove` pays for it: `--fetch` on a
        # plain listing used to pull 200 merged PRs nothing would read.
        with patched((worktree_status.gh_json, "load_or_none", self._never)):
            self.assertEqual(self._prs(fetch=True, remove=False), [])

    def test_fetch_asks(self):
        with patched((worktree_status.gh_json, "load_or_none", lambda *a: [{"number": 1}])):
            self.assertEqual(self._prs(fetch=True), [{"number": 1}])

    def test_gh_refusing_keeps_the_run_alive_and_says_so(self):
        # `gh_json.load` would `raise SystemExit` here and kill a git-only listing that had
        # nothing to do with GitHub; the sweep keeps what it cannot prove instead.
        printed = io.StringIO()
        with patched((worktree_status.gh_json, "load_or_none", lambda *a: None)):
            with contextlib.redirect_stdout(printed):
                self.assertEqual(self._prs(fetch=True), [])
        self.assertIn("kept", printed.getvalue())

    @staticmethod
    def _never(*_args):
        raise AssertionError("gh was asked on a run that gave it neither --merged nor --fetch")


class ReadStatusTest(unittest.TestCase):
    """One `git status --porcelain --ignored`, read for its three answers.

    The refusal is the one that mattered: `""` used to come back both for a worktree git
    would not read and for a worktree with nothing to report, so the three the desktop app
    created under Administrator ownership were reported clean (#172).
    """

    def _read(self, stdout: str = "", returncode: int = 0, stderr: str = "", raises=None):
        def run(*args, **kwargs):
            if raises:
                raise raises
            return subprocess.CompletedProcess(list(args), returncode, stdout, stderr)

        # Patched at `git_cmd.run`, the one place under `scripts/` that spawns git; the
        # module's own `subprocess` import went with the last direct call site.
        with mock.patch.object(worktree_status.git_cmd, "run", run):
            return worktree_status.read_status(Path("/wt/x"))

    def test_a_worktree_git_reads_has_no_complaint(self):
        self.assertIsNone(self._read()[0])

    def test_dubious_ownership_carries_gits_own_remedy(self):
        stderr = "fatal: detected dubious ownership in repository at '/wt/x'\n"
        self.assertIn("safe.directory", self._read(returncode=128, stderr=stderr)[0])

    def test_a_directory_that_is_gone_is_not_an_empty_answer(self):
        # git lists a worktree whose directory was deleted from under it; `subprocess` then
        # fails on the cwd rather than returning a status, which used to crash the run.
        self.assertIn("prune", self._read(raises=FileNotFoundError())[0])

    def test_the_three_kinds_of_change_are_counted_apart(self):
        stdout = "M  staged.py\n M unstaged.py\n?? new.py\n"
        self.assertEqual(self._read(stdout)[1], (1, 1, 1))

    def test_ignored_output_is_not_counted_and_not_named(self):
        # `api/.venv/` and the app's own settings are the repository declaring them
        # disposable; `git worktree remove --force` deletes them and that is correct.
        stdout = "!! api/.venv/\n!! .claude/settings.local.json\n"
        _, counts, hand_written = self._read(stdout)
        self.assertEqual((counts, hand_written), ((0, 0, 0), ()))

    def test_an_ignored_env_file_is_named(self):
        # Ignored by design and hand-written: `infra/.env` exists in this repository, and
        # deleting a worktree holding one loses it for good (#176 review).
        self.assertEqual(self._read("!! web/.env.local\n")[2], ("web/.env.local",))


class DescribeTest(unittest.TestCase):
    """The `main` column reaches the printed line -- deleting the tail left the suite green."""

    ENTRY = {"worktree": "/wt/x", "branch": "refs/heads/claude/x"}

    def _line(self, state: State, entry: dict | None = None) -> str:
        with patched((worktree_status, "ahead_behind", lambda path: None)):
            return worktree_status.describe(entry or self.ENTRY, is_main=False, state=state)[0]

    def test_the_column_is_on_the_line(self):
        self.assertIn("[on main]", self._line(clean()))

    def test_a_squash_merged_worktree_says_so_in_the_column(self):
        # The disagreement this fixes: the column said `ahead 6 of main` for a worktree the
        # sweep deleted on the next line, because the criterion reached the rule and not the
        # line. One reading now serves both (#219).
        self.assertIn("[ahead 6 of main, squash-merged as #192]", self._line(SQUASHED))

    def test_a_worktree_main_holds_says_nothing_about_a_pr(self):
        # `read_state` never builds that pair, and neither does `clean`; the column says
        # the plain thing because there is nothing else left to say.
        self.assertIn("[on main]", self._line(clean(merged_as=192)))

    def test_a_bare_worktree_has_no_column(self):
        self.assertNotIn("main]", self._line(clean(), {"worktree": "/wt/x", "bare": ""}))

    def test_a_worktree_git_cannot_read_is_never_clean(self):
        line, counts_against = worktree_status.describe(
            self.ENTRY, is_main=False, state=State("dubious ownership", (0, 0, 0), (), None)
        )
        self.assertIn("UNREADABLE", line)
        self.assertTrue(counts_against)


class ContainingTest(unittest.TestCase):
    """Which listed worktree cwd is in, given this repo nests them inside the main checkout."""

    MAIN = Path("/repo").resolve()
    LANE = Path("/repo/.claude/worktrees/lane").resolve()

    def _containing(self, here: Path) -> Path | None:
        entries = [{"worktree": str(self.MAIN)}, {"worktree": str(self.LANE)}]
        return worktree_status.containing(entries, here)

    def test_the_nested_worktree_wins_over_the_main_checkout(self):
        # #157: both contain cwd, because worktrees live at `.claude/worktrees/`. The
        # nearest is the one the session is in; the old test took every ancestor.
        self.assertEqual(self._containing(self.LANE), self.LANE)

    def test_a_subdirectory_still_finds_its_worktree(self):
        # The case the ancestor test existed for, and the reason this is not plain equality.
        self.assertEqual(self._containing(self.LANE / "scripts" / "tests"), self.LANE)

    def test_the_main_checkout_finds_itself(self):
        self.assertEqual(self._containing(self.MAIN), self.MAIN)

    def test_outside_every_worktree_is_none(self):
        self.assertIsNone(self._containing(Path("/elsewhere").resolve()))


class IdleHoursTest(unittest.TestCase):
    """The clock that keeps `--remove` off a live session's working directory."""

    def _hours(self, *, written: float | None) -> float | None:
        with tempfile.TemporaryDirectory() as tmp:
            git_dir = Path(tmp)
            if written is not None:
                head = git_dir / "HEAD"
                head.write_text("ref: refs/heads/claude/lane\n")
                os.utime(head, (time.time() - written * 3600, time.time() - written * 3600))
            with patched((worktree_status, "_git", lambda *a, **k: f"{git_dir}\n")):
                return worktree_status.idle_hours(Path("/wt/lane"))

    def test_a_git_directory_nothing_has_written_cannot_say(self):
        # Not "zero hours", which would read as live, and not "forever", which would delete.
        self.assertIsNone(self._hours(written=None))

    def test_a_worktree_git_cannot_place_cannot_say(self):
        with patched((worktree_status, "_git", lambda *a, **k: "")):
            self.assertIsNone(worktree_status.idle_hours(Path("/wt/lane")))

    def test_the_newest_write_is_what_counts(self):
        self.assertAlmostEqual(self._hours(written=30.0), 30.0, places=1)


class WhyKeptTest(unittest.TestCase):
    """The removal rule, one reason at a time: `--remove` deletes only what answers None."""

    def _reason(
        self,
        state: State | None = None,
        *,
        is_main=False,
        is_here=False,
        idle: float | None = 48.0,
    ) -> str | None:
        with patched((worktree_status, "idle_hours", lambda path: idle)):
            return worktree_status.why_kept(
                LANE,
                state or clean(),
                is_main=is_main,
                is_here=is_here,
                path=Path("/wt/lane"),
            )

    def test_clean_merged_and_idle_may_go(self):
        self.assertIsNone(self._reason())

    def test_the_main_checkout_never_goes(self):
        self.assertIsNotNone(self._reason(is_main=True))

    def test_the_worktree_the_run_is_in_never_goes(self):
        self.assertIsNotNone(self._reason(is_here=True))

    def test_uncommitted_work_keeps_it(self):
        self.assertIsNotNone(self._reason(State(None, (0, 1, 0), (), "on main", 0, True)))

    def test_an_ignored_file_git_cannot_give_back_keeps_it(self):
        # `--force` deletes ignored files too, so the rule has to see them (#176 review).
        reason = self._reason(clean(hand_written=("web/.env.local",)))
        self.assertIn(".env.local", reason or "")

    def test_a_head_main_does_not_hold_keeps_it(self):
        self.assertIn("ahead", self._reason(clean("ahead 3 of main")) or "")

    def test_a_worktree_touched_an_hour_ago_keeps_it(self):
        # The guard against deleting a live session's working directory out from under it.
        self.assertIn("touched", self._reason(idle=1.0) or "")

    def test_an_idle_clock_that_cannot_be_read_keeps_it(self):
        self.assertIsNotNone(self._reason(idle=None))

    def test_an_unreadable_worktree_is_never_a_candidate(self):
        # Every other answer for one of these is the empty one git's refusal produces --
        # clean, on main -- which is how a cleaner would delete a worktree holding work.
        reason = self._reason(State("dubious ownership", (0, 0, 0), (), None))
        self.assertIn("unreadable", reason or "")

    # #197: the second way work reaches `main`, which git cannot see. A squash-merged PR puts
    # one new commit on `main` and leaves the branch's own commits ancestors of nothing, so
    # `against_trunk` says `ahead N of main` forever and only GitHub can settle it.

    def test_a_squash_merged_head_may_go_though_main_lacks_its_commits(self):
        self.assertIsNone(self._reason(SQUASHED))

    def test_a_head_no_merged_pr_accounts_for_is_still_kept(self):
        # A bare run reads every worktree this way, which is the case the closing step and
        # the retro's audit actually run.
        self.assertIn("ahead", self._reason(clean("ahead 6 of main")) or "")

    def test_the_squash_path_does_not_excuse_uncommitted_work(self):
        # It answers where the work went, never whether the tree is clean.
        state = State(None, (0, 1, 0), (), "ahead 6 of main", 192, False)
        self.assertIn("uncommitted", self._reason(state) or "")


def pr_merged(number, head="claude/lane", *, oid="a" * 40, base="main"):
    """A merged PR as `gh pr list --state merged` returns it, for `merged_heads`."""
    return {"number": number, "headRefName": head, "headRefOid": oid, "baseRefName": base}


class MergedHereTest(unittest.TestCase):
    """The squash proof itself. Deleted with the parameter in #223 and put back: both
    reviewers reproduced `return number` leaving the whole suite green, which is the
    guard on the data-loss path #216 fixed (#223 review).
    """

    def test_a_head_that_is_the_merged_commit_is_the_pr(self):
        self.assertEqual(worktree_status.merged_here(LANE, MERGED_AS_192), 192)

    def test_a_head_that_moved_since_the_merge_is_nothing(self):
        # The loss: a commit made after the squash merge, taken to `--force` and
        # `branch -D` because the branch name still matched.
        moved = {"claude/lane": (192, "b" * 40)}
        self.assertEqual(worktree_status.merged_here(LANE, moved), 0)

    def test_a_branch_no_merged_pr_names_is_nothing(self):
        self.assertEqual(worktree_status.merged_here(LANE, {"claude/other": (1, "a" * 40)}), 0)

    def test_an_empty_mapping_is_nothing(self):
        self.assertEqual(worktree_status.merged_here(LANE, {}), 0)


class MergedHeadsTest(unittest.TestCase):
    """Branch to the PR it headed and the commit that merged, from the list gh returns."""

    def test_the_mapping_carries_the_pr_and_the_commit(self):
        heads = worktree_status.merged_heads([pr_merged(192), pr_merged(188, "claude/other")])
        self.assertEqual(heads, {"claude/lane": (192, "a" * 40), "claude/other": (188, "a" * 40)})

    def test_a_branch_reused_by_two_prs_takes_the_highest_number(self):
        heads = worktree_status.merged_heads(
            [pr_merged(55), pr_merged(192, oid="b" * 40), pr_merged(119)]
        )
        self.assertEqual(heads, {"claude/lane": (192, "b" * 40)})

    def test_an_entry_missing_any_of_the_three_fields_is_skipped(self):
        # `gh` omits a field it has no value for rather than sending null, and a PR whose
        # head branch is gone comes back without one.
        heads = worktree_status.merged_heads(
            [
                {"number": 1, "baseRefName": "main"},
                {"headRefName": "claude/lane", "baseRefName": "main"},
                {},
                {"number": 0, "headRefName": "x", "headRefOid": "c" * 40, "baseRefName": "main"},
            ]
        )
        self.assertEqual(heads, {})

    def test_a_pr_merged_into_a_live_base_is_not_evidence(self):
        # The PR #80 shape `check_prs.py` checks for: merged, but not into `main`, so its
        # work has not shipped and its branch is not spent. Taking it would have deleted a
        # worktree whose commits reach `main` through nothing at all.
        heads = worktree_status.merged_heads([pr_merged(80, base="claude/maintain-2026-09-08")])
        self.assertEqual(heads, {})


class RemoveTest(unittest.TestCase):
    """`--force` is not optional here, so the refusal it forfeits is re-made on the spot."""

    def _remove(self, *, complaint=None, counts=(0, 0, 0), hand_written=()):
        called: list[list[str]] = []

        def run(*args, **kwargs):
            called.append(["git", *args])
            return subprocess.CompletedProcess(list(args), 0, "", "")

        with patched(
            (worktree_status, "read_status", lambda path: (complaint, counts, hand_written)),
            (worktree_status, "_git", lambda *a, **k: ""),
            (worktree_status.git_cmd, "run", run),
        ):
            failure = worktree_status.remove(Path("/wt/lane"), "claude/lane", Path("/repo"))
        return failure, called

    def test_a_clean_worktree_is_forced(self):
        # `git worktree remove` refuses any worktree holding a submodule, and every worktree
        # here has the fleet at `.claude/agents` (ADR-0019): without `--force`, nothing goes.
        failure, called = self._remove()
        self.assertIsNone(failure)
        self.assertIn("--force", called[0])

    def test_work_that_appeared_since_the_check_stops_the_delete(self):
        # What `--force` costs is git's own refusal to delete a tree with modifications.
        failure, called = self._remove(counts=(0, 1, 0))
        self.assertIsNotNone(failure)
        self.assertEqual(called, [])

    def test_a_worktree_git_stopped_reading_stops_the_delete(self):
        failure, called = self._remove(complaint="dubious ownership")
        self.assertIsNotNone(failure)
        self.assertEqual(called, [])


class HusksTest(unittest.TestCase):
    """The directories git no longer lists -- which `git worktree prune` can never find."""

    def _husks(self, names: tuple[str, ...], listed: tuple[str, ...] = ()) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / worktree_status.APP_WORKTREES
            root.mkdir(parents=True)
            for name in names:
                (root / name).mkdir()
            held = {(root / name).resolve() for name in listed}
            return [found.name for found in worktree_status.husks(Path(tmp), held)]

    def test_a_directory_git_does_not_list_is_a_husk(self):
        self.assertEqual(self._husks(("gone",)), ["gone"])

    def test_a_worktree_git_still_lists_is_not(self):
        self.assertEqual(self._husks(("live", "gone"), listed=("live",)), ["gone"])

    def test_no_app_directory_is_no_husks(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(worktree_status.husks(Path(tmp), set()), [])


class UnreconstructableTest(unittest.TestCase):
    """What deleting a husk would lose -- the one test the filesystem sweep rests on."""

    def _lost(
        self,
        files: dict[str, str],
        *,
        ignored: tuple = (),
        held: tuple = (),
        submodules: tuple = (),
        reusable: bool = True,
    ) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            husk = Path(tmp)
            for name, text in files.items():
                (husk / name).parent.mkdir(parents=True, exist_ok=True)
                (husk / name).write_text(text)

            def fed(args, paths, cwd=None):
                if args[0] == "check-ignore":
                    return [p for p in paths if p in ignored]
                if args[0] == "hash-object":
                    # The contents stand in for the digest, so `held` reads as file text.
                    return [Path(p).read_text() for p in paths]
                return [f"{h} blob 1" if h in held else f"{h} missing" for h in paths]

            with patched(
                (worktree_status, "_git_fed", fed),
                (worktree_status, "_reusable_submodule", lambda path: reusable),
            ):
                return worktree_status.unreconstructable(husk, Path("/repo"), submodules)

    def test_a_path_the_repo_ignores_is_no_loss(self):
        # The case that was actually found: a Vite cache the removal could not delete.
        lost = self._lost({"web/.vite/deps/x.json": "cache"}, ignored=("web/.vite",))
        self.assertEqual(lost, [])

    def test_a_file_git_already_holds_is_no_loss(self):
        # A checked-out copy of a committed file, however stale: git can hand it back.
        self.assertEqual(self._lost({"CLAUDE.md": "committed"}, held=("committed",)), [])

    def test_anything_else_is_a_loss(self):
        self.assertEqual(self._lost({"notes.md": "nobody committed this"}), ["notes.md"])

    def test_an_ignored_env_file_is_still_a_loss(self):
        # Ignored *and* hand-written: the ignore rules are not permission to delete it.
        lost = self._lost({"web/.env.local": "SECRET=1"}, ignored=("web/.env.local",))
        self.assertEqual(lost, ["web/.env.local"])

    def test_a_submodule_checkout_is_reconstructable(self):
        # Its blobs are in its own object database, not this one, so without this every
        # husk that still held `.claude/agents` was kept forever for a false reason.
        lost = self._lost({".claude/agents/CLAUDE.md": "fleet"}, submodules=(".claude/agents",))
        self.assertEqual(lost, [])

    def test_a_submodule_with_changes_of_its_own_keeps_the_husk(self):
        # The fleet-editing workflow the root `CLAUDE.md` describes, caught mid-flight.
        lost = self._lost(
            {".claude/agents/CLAUDE.md": "edited"},
            submodules=(".claude/agents",),
            reusable=False,
        )
        self.assertIn(".claude/agents", lost[0])

    def test_an_empty_directory_loses_nothing(self):
        self.assertEqual(self._lost({}), [])

    def test_a_git_directory_means_it_is_not_a_husk(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".git").mkdir()
            self.assertTrue(worktree_status.unreconstructable(Path(tmp), Path("/repo"), ()))


class SweepOneTest(unittest.TestCase):
    """What goes, what is said to have stayed, and what counts against the run."""

    def _sweep(self, *, kept: str | None = None, failure: str | None = None, state=None):
        removed: list[str] = []

        def remove(path, branch, repo):
            removed.append(branch)
            return failure

        printed = io.StringIO()
        with patched(
            (worktree_status, "why_kept", lambda *a, **k: kept),
            (worktree_status, "remove", remove),
        ):
            with contextlib.redirect_stdout(printed):
                refused = worktree_status.sweep_one(
                    LANE, state or clean(), is_main=False, is_here=False, repo=Path("/repo")
                )
        return refused, removed, printed.getvalue()

    def test_a_worktree_with_no_reason_to_stay_goes_with_its_branch(self):
        refused, removed, printed = self._sweep()
        self.assertEqual((refused, removed), (0, ["claude/lane"]))
        self.assertIn("removed lane", printed)

    def test_a_squash_merged_removal_names_the_pr_the_listing_could_not(self):
        # The line above this one says `ahead 6 of main`; a removal a reader cannot reconcile
        # with it is one they have to go and check.
        _, _, printed = self._sweep(state=SQUASHED)
        self.assertIn("squash-merged as #192", printed)

    def test_an_ordinary_removal_says_nothing_about_a_pr(self):
        # `on main` is its own explanation, and the listing already printed it.
        _, _, printed = self._sweep(state=clean(merged_as=192))
        self.assertNotIn("squash-merged", printed)

    def test_a_worktree_with_a_reason_stays_and_the_reason_is_printed(self):
        refused, removed, printed = self._sweep(kept="touched 1.0h ago")
        self.assertEqual((refused, removed), (0, []))
        self.assertIn("kept lane — touched 1.0h ago", printed)

    def test_a_removal_that_failed_counts(self):
        # It will still be there next run; a sweep that claims otherwise is worse than none.
        refused, _, printed = self._sweep(failure="fatal: busy")
        self.assertEqual(refused, 1)
        self.assertIn("could not remove", printed)


class SweepHusksTest(unittest.TestCase):
    """Husks are printed, never gated: what holds one open is not the session's to fix."""

    def _sweep(self, *, lost: tuple = (), refuses: str | None = None):
        deleted: list[str] = []

        def rmtree(path):
            if refuses:
                raise OSError(16, refuses)
            deleted.append(Path(path).name)

        printed = io.StringIO()
        with patched(
            (worktree_status, "husks", lambda root, listed: [Path("/wt/husk")]),
            (worktree_status, "unreconstructable", lambda h, root, subs: list(lost)),
            (worktree_status.shutil, "rmtree", rmtree),
        ):
            with contextlib.redirect_stdout(printed):
                worktree_status.sweep_husks(Path("/repo"), set(), ())
        return deleted, printed.getvalue()

    def test_a_husk_git_can_account_for_is_deleted(self):
        deleted, printed = self._sweep()
        self.assertEqual(deleted, ["husk"])
        self.assertIn("deleted husk", printed)

    def test_a_husk_git_cannot_reconstruct_stays(self):
        deleted, printed = self._sweep(lost=("notes.md",))
        self.assertEqual(deleted, [])
        self.assertIn("git does not hold notes.md", printed)

    def test_a_husk_the_filesystem_will_not_delete_is_said_and_not_gated(self):
        # An empty directory a live process holds open: Windows answers `Device or resource
        # busy`, and no session can fix that, so it is a notice rather than a finding.
        _, printed = self._sweep(refuses="Device busy")
        self.assertIn("could not delete husk", printed)


class CurrentScopeTest(unittest.TestCase):
    """`--current` gates on this worktree alone; the bare run still gates on all of them.

    Drives `main()`, because the scope test lives there and a helper-only suite missed
    #157 entirely. The mutation these have to fail is the original line -- scoping in
    every ancestor of cwd, which in this repository's layout is every worktree's parent.
    """

    MAIN = Path("/repo").resolve()
    LANE = Path("/repo/.claude/worktrees/lane").resolve()

    def _run(
        self,
        argv: list[str],
        dirty: tuple[Path, ...] = (),
        here: Path | None = None,
        hooks: str = "",
        refused: int = 0,
        unreadable: tuple[Path, ...] = (),
    ) -> tuple[int, str]:
        entries = [
            {"worktree": str(self.MAIN), "branch": "refs/heads/main"},
            {"worktree": str(self.LANE), "branch": "refs/heads/claude/lane"},
        ]
        # `complaint` set is what `describe` reports as UNREADABLE -- a separate outcome from
        # dirt since #199, so the helper has to be able to produce one without the other.
        state = lambda path, ref, merged_as=0: State(  # noqa: E731
            "dubious ownership" if path in unreadable else None,
            (0, 1, 0) if path in dirty else (0, 0, 0),
            (),
            None,
        )
        git = lambda args, **k: hooks if "config" in args else ""  # noqa: E731
        printed = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        with patched(
            (worktree_status, "worktrees", lambda repo: entries),
            (worktree_status, "read_state", state),
            (worktree_status, "_git", git),
            (worktree_status, "sweep_one", lambda *a, **k: refused),
            (worktree_status, "sweep_husks", lambda *a, **k: None),
            (worktree_status.trunk, "ref", lambda root: None),
            (worktree_status.trunk, "refresh", lambda root: None),
            (Path, "cwd", lambda: here or self.LANE),
            (sys, "argv", ["worktree_status.py", *argv]),
        ):
            with contextlib.redirect_stdout(printed):
                code = worktree_status.main()
                printed.flush()
        return code, printed.buffer.getvalue().decode("utf-8")

    def _exit_code(self, argv: list[str], dirty: tuple[Path, ...], here: Path | None = None) -> int:
        return self._run(argv, dirty, here)[0]

    def test_current_ignores_dirt_in_the_main_checkout(self):
        # The #157 regression guard: a spotless lane passed its closing check only after
        # the main checkout stopped counting as "this worktree".
        self.assertEqual(self._exit_code(["--current"], dirty=(self.MAIN,)), 0)

    def test_current_still_fails_on_this_worktrees_own_dirt(self):
        # Without this, "scope nothing" would pass the guard above.
        self.assertEqual(self._exit_code(["--current"], dirty=(self.LANE,)), 1)

    def test_the_bare_run_still_counts_the_main_checkout(self):
        # #157 put this out of scope on purpose: the retro's audit wants every worktree,
        # and the main checkout's dirt is real information there.
        self.assertEqual(self._exit_code([], dirty=(self.MAIN,)), 1)

    def test_current_outside_every_worktree_refuses_to_pass(self):
        # A check that cannot tell which worktree it is in must not report it clean.
        outside = Path("/elsewhere").resolve()
        self.assertEqual(self._exit_code(["--current"], dirty=(), here=outside), 1)

    def test_unattended_does_not_fail_on_dirt_it_owns_none_of(self):
        # #199: the 04:00 task owns none of these trees, and gating on their uncommitted work
        # made it report failure most mornings -- which hid a real removal failure behind the
        # normal state. An explicit flag, not an inference from `--remove`: the retro runs the
        # same `--remove` by hand and keeps the gate (`pr-direction-review`).
        code, printed = self._run(["--remove", "--unattended"], dirty=(self.MAIN, self.LANE))
        self.assertEqual(code, 0)
        self.assertIn("not gated on", printed)

    def test_unattended_still_fails_when_git_will_not_read_a_worktree(self):
        # The carve-out is for uncommitted work only. Git refusing to read a tree means the
        # sweep is blind there and that worktree will never be swept, which is a standing
        # fault with a remedy -- not the normal state (`pr-tech-review`).
        code, printed = self._run(["--remove", "--unattended"], unreadable=(self.LANE,))
        self.assertEqual(code, 1)
        self.assertIn("git cannot read it", printed)

    def test_unattended_still_fails_on_a_refused_removal(self):
        # What the sweep *can* act on still goes red, with nothing else competing for the
        # exit status. Distinct argv from the #176 guard below, which keeps both gates.
        code, printed = self._run(["--remove", "--unattended"], dirty=(self.MAIN,), refused=1)
        self.assertEqual(code, 1)
        self.assertIn("decided removal(s) failed", printed)

    def test_the_bare_sweep_still_gates_on_dirt(self):
        # `--remove` without the flag is the retro's hand-run (`.claude/agents/retro.md`), and
        # it keeps the gate it always had. Without this, the flag could be quietly widened
        # back into an inference from `--remove` and nothing would say so.
        self.assertEqual(self._exit_code(["--remove"], dirty=(self.LANE,)), 1)

    def test_a_failed_removal_is_not_hidden_behind_a_dirty_worktree(self):
        # Returning on the dirty count meant the one outcome of a `--remove` run nobody may
        # miss never reached the summary at all (#176 review). Argv is `--current --remove`,
        # the closing step's own: since #199 that is the invocation where both still gate, so
        # it is the only one where re-introducing that early return is visible (`pr-tech-review`,
        # which mutation-tested the old argv and found it passed).
        code, printed = self._run(["--current", "--remove"], dirty=(self.LANE,), refused=1)
        self.assertEqual(code, 1)
        self.assertIn("not clean", printed)
        self.assertIn("decided removal(s) failed", printed)

    def test_the_main_checkouts_githooks_is_accepted_for_a_lane(self):
        # Pins which entry `main_root` comes from: git lists the main worktree first, and
        # with any other entry this clone's own `.githooks` stops being recognised and the
        # finding fires on a worktree nobody misconfigured. `entries[-1]` passed without it.
        hooks = f"file:config.worktree\t{self.MAIN / '.githooks'}\n"
        code, printed = self._run(["--current"], hooks=hooks)
        self.assertEqual(code, 0)
        self.assertNotIn("core.hooksPath", printed)

    def test_a_pinned_copy_elsewhere_is_still_reported(self):
        # The other half: the acceptance must not have blinded the check.
        hooks = "file:config.worktree\t/somewhere/else/.githooks\n"
        code, printed = self._run(["--current"], hooks=hooks)
        self.assertEqual(code, 0)  # a hooks finding is printed, never gated
        self.assertIn("core.hooksPath", printed)


class GitFedTest(unittest.TestCase):
    """`_git_fed` answers for a whole list in one process, and only if it feeds stdin.

    Against a real repository, not a stub: all three callers stub it, so deleting the
    `input=` it passes left the whole suite green. The batching is the point -- a husk scan
    at a process per file took minutes (#176 review) -- and a batch that feeds git nothing
    answers for nothing while still looking like it worked.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        worktree_status.git_cmd.run("init", "-q", "-b", "main", cwd=self.repo, check=True)

    def test_every_fed_line_is_answered_in_one_process(self):
        blobs = ["alpha", "beta", "gamma"]
        digests = worktree_status._git_fed(["hash-object", "--stdin-paths"], [], cwd=self.repo)
        self.assertEqual(digests, [], "an empty list must not spawn git at all")

        for name in blobs:
            (self.repo / name).write_text(name, encoding="utf-8")
        digests = worktree_status._git_fed(
            ["hash-object", "--stdin-paths"], [str(self.repo / n) for n in blobs], cwd=self.repo
        )
        self.assertEqual(len(digests), len(blobs), "one answer per fed line")
        self.assertTrue(all(len(d) == 40 for d in digests), digests)

    def test_a_feed_that_never_reaches_git_is_not_mistaken_for_an_answer(self):
        # This is the mutation the suite could not see: drop `input=` and git reads EOF.
        real = worktree_status.git_cmd.run

        def starved(*args, **kwargs):
            # Empty rather than absent: dropping `input=` entirely leaves git reading an
            # inherited stdin and the test hangs instead of failing, which is worse than
            # the bug. An empty feed is the same observable -- git is asked nothing.
            kwargs["input"] = ""
            return real(*args, **kwargs)

        (self.repo / "one").write_text("one", encoding="utf-8")
        fed = [str(self.repo / "one")]
        self.assertEqual(
            len(worktree_status._git_fed(["hash-object", "--stdin-paths"], fed, cwd=self.repo)), 1
        )
        with mock.patch.object(worktree_status.git_cmd, "run", starved):
            self.assertEqual(
                worktree_status._git_fed(["hash-object", "--stdin-paths"], fed, cwd=self.repo),
                [],
                "git answered without being fed -- the batch is not reaching stdin",
            )


if __name__ == "__main__":
    unittest.main()
