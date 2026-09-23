"""Table-driven tests for `scripts/check_prs.py`.

The root `CLAUDE.md`'s working agreement is the authority these tests pin: a PR is a draft
until it is ready to merge -- its review pass folded and the reports committed -- and a
stacked PR is a draft until its base merges. Stdlib only (`unittest`), like the script; run
with `python -m unittest discover scripts/tests`.

Each case is a list of PR dicts shaped like `gh pr list --json` output and an assertion on
the lines `findings()` returns, by substring. The first case is the one PR #119 would have
tripped: ready for review with a "to be filled" review-pass section. The merged-PR cases
hand `merged_findings()` a stand-in for git; `merge_landed()` itself runs against a
throwaway repository, since whether main holds a commit is the one thing a dict cannot say.
"""

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gitenv import git_env  # noqa: E402
import check_prs  # noqa: E402
import reviews  # noqa: E402
import trunk  # noqa: E402

SCRIPT = Path(check_prs.__file__)
FOLDED = "## Review pass\n\nAll four ran. Acted on: tech 1, direction 2. Dismissed: parsimony 1.\n"
PLACEHOLDER = "## Review pass\n\n_To be filled after the four reviewers run._\n\n## Decisions\n"
NOT_RUN = "## Review pass\n\nNot run: a docs-only record PR, the kind the session may merge.\n"
REPORTS = [f"docs/reviews/x/{agent}.md" for agent in reviews.REVIEWERS]
# A commit needs an author, and a CI runner carries no global identity -- the same reason
# `test_check_docs.py` sets these for its repository fixture.
_GIT_ENV = git_env()


class _Captured(io.StringIO):
    """Stdout for an in-process `main()`, which reconfigures the encoding of the real one."""

    def reconfigure(self, **_kwargs):
        """Accept and ignore: a capture has no encoding to set."""


def _git(root, *args):
    """Run git in `root`, failing loudly, and return what it printed."""
    done = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True, env=_GIT_ENV
    )
    return done.stdout.strip()


def pr(number, *, draft=False, base="main", body=FOLDED, title="a change", files=None):
    """A PR as `gh pr list` returns it; the four reports are committed unless `files` says."""
    paths = REPORTS if files is None else files
    return {
        "number": number, "title": title, "isDraft": draft, "baseRefName": base,
        "headRefName": "claude/x", "body": body, "files": [{"path": path} for path in paths],
    }


def merged(number, *, base="main", oid="a" * 40, title="a change"):
    """A merged PR as `gh pr list --state merged` returns it."""
    return {
        "number": number, "title": title, "baseRefName": base, "headRefName": "claude/x",
        "mergeCommit": {"oid": oid},
    }


class ReadyButOutrun(unittest.TestCase):
    """A ready PR whose head has commits after its reports is a finding, given a reader."""

    def test_commits_after_the_reports_fail_and_none_passes(self):
        outrun = {7: ["ab12  Merge branch 'main'"], 8: []}
        found = check_prs.findings([pr(7), pr(8)], outrun_by=lambda p: outrun[p["number"]])
        self.assertEqual(len(found), 1)
        self.assertIn("#7", found[0])
        self.assertIn("Merge branch 'main'", found[0])
        self.assertIn("return it to draft", found[0])

    def test_a_snapshot_run_has_no_reader_and_stays_silent(self):
        self.assertEqual(check_prs.findings([pr(7)]), [])


class ReadyWithoutAFoldedPass(unittest.TestCase):
    def test_placeholder_section_is_a_finding(self):
        found = check_prs.findings([pr(119, body=PLACEHOLDER)])
        self.assertEqual(len(found), 1)
        self.assertIn("#119", found[0])
        self.assertIn("placeholder", found[0])

    def test_missing_section_is_a_finding(self):
        found = check_prs.findings([pr(7, body="Closes #1.\n\n## Proof\n\nscreenshots\n")])
        self.assertEqual(len(found), 1)
        self.assertIn("no Review pass section", found[0])

    def test_empty_section_is_a_finding(self):
        found = check_prs.findings([pr(8, body="## Review pass\n\n## Decisions\n\n- D1\n")])
        self.assertEqual(len(found), 1)
        self.assertIn("is empty", found[0])

    def test_an_issue_reference_inside_the_section_is_not_a_heading(self):
        body = "## Review pass\n\n#119 merged before its pass.\n\n_To be filled._\n"
        found = check_prs.findings([pr(8, body=body)])
        self.assertEqual(len(found), 1)
        self.assertIn("placeholder", found[0])

    def test_a_placeholder_in_the_heading_itself_is_seen(self):
        found = check_prs.findings([pr(8, body="## Review pass — to be filled\n\nsee above\n")])
        self.assertEqual(len(found), 1)
        self.assertIn("placeholder", found[0])

    def test_todo_under_a_comment_is_a_placeholder(self):
        body = "## Review pass\n\n<!-- acted on / dismissed -->\nTODO\n"
        found = check_prs.findings([pr(8, body=body)])
        self.assertEqual(len(found), 1)
        self.assertIn("placeholder", found[0])

    def test_not_run_yet_is_a_placeholder_not_a_statement(self):
        found = check_prs.findings([pr(8, body="## Review pass\n\nNot run yet.\n", files=[])])
        self.assertEqual(len(found), 1)
        self.assertIn("placeholder", found[0])

    def test_a_level_three_heading_is_found(self):
        body = "## Checks\n\n### Review pass\n\nfolded: tech 1 acted on.\n\n## Handoff\n"
        self.assertEqual(check_prs.findings([pr(8, body=body)]), [])

    def test_null_body_is_a_missing_section(self):
        found = check_prs.findings([pr(8, body=None)])
        self.assertEqual(len(found), 1)
        self.assertIn("no Review pass section", found[0])

    def test_draft_with_placeholder_is_fine(self):
        self.assertEqual(check_prs.findings([pr(119, draft=True, body=PLACEHOLDER)]), [])

    def test_folded_section_with_committed_reports_is_fine(self):
        self.assertEqual(check_prs.findings([pr(5)]), [])

    def test_subsection_inside_the_pass_counts_as_content(self):
        body = (
            "## Review pass\n\n### Acted on\n\n- tech 1\n\n### Dismissed\n\n- none\n\n## Handoff\n"
        )
        self.assertEqual(check_prs.findings([pr(5, body=body)]), [])


class ReadyWithoutCommittedReports(unittest.TestCase):
    def test_folded_prose_without_the_reports_is_a_finding(self):
        found = check_prs.findings([pr(5, files=["web/src/App.tsx"])])
        self.assertEqual(len(found), 1)
        self.assertIn("commits no report", found[0])

    def test_the_finding_names_the_missing_reviewer(self):
        found = check_prs.findings([pr(5, files=REPORTS[:3])])
        self.assertEqual(len(found), 1)
        self.assertIn("pr-architecture-review", found[0])
        self.assertNotIn("pr-tech-review", found[0])

    def test_reports_under_the_full_branch_name_do_not_count(self):
        # One spelling: `docs/reviews/<branch>` with `claude/` dropped, which the overlay
        # prescribes, the brief sends reviewers to, and no pass in thirty has departed from.
        # Accepting the other excused only a report filed by hand in the wrong place (#193).
        files = [f"docs/reviews/claude/x/{agent}.md" for agent in reviews.REVIEWERS]
        found = check_prs.findings([pr(5, files=files)])
        self.assertEqual(len(found), 1)
        self.assertIn("commits no report", found[0])

    def test_a_stated_reason_for_not_running_the_pass_needs_no_reports(self):
        self.assertEqual(check_prs.findings([pr(120, body=NOT_RUN, files=[])]), [])


class ReadyWhileDependingOnSomethingUnmerged(unittest.TestCase):
    def test_stacked_base_is_a_finding(self):
        found = check_prs.findings([pr(63, base="claude/web-invites-55")])
        self.assertEqual(len(found), 1)
        self.assertIn("based on `claude/web-invites-55`", found[0])

    def test_stacked_draft_is_fine(self):
        self.assertEqual(check_prs.findings([pr(63, draft=True, base="claude/web-invites-55")]), [])

    def test_merge_after_an_open_pr_is_a_finding(self):
        body = "Merge after #55.\n\n" + FOLDED
        found = check_prs.findings([pr(55, draft=True, body=PLACEHOLDER), pr(63, body=body)])
        self.assertEqual(len(found), 1)
        self.assertIn("merge after #55, which is still open", found[0])

    def test_merge_after_a_merged_pr_is_fine(self):
        body = "Merge after #55.\n\n" + FOLDED
        self.assertEqual(check_prs.findings([pr(63, body=body)]), [])

    def test_this_repository_named_in_full_is_still_this_repository(self):
        body = "Merge after Atomtomate/constellate#55.\n\n" + FOLDED
        found = check_prs.findings([pr(55, draft=True, body=PLACEHOLDER), pr(63, body=body)])
        self.assertEqual(len(found), 1)
        self.assertIn("merge after #55, which is still open", found[0])

    def test_another_repository_is_a_notice_and_not_a_finding(self):
        body = "Merge after Atomtomate/agents#11.\n\n" + FOLDED
        # #11 of *this* repository is open in the same list: a cross-repo reference that leaked
        # into the local set would raise a false "merge after #11, which is still open".
        prs = [pr(11, draft=True, body=PLACEHOLDER), pr(188, body=body)]
        self.assertEqual(check_prs.findings(prs), [])
        printed = check_prs.notices(prs)
        self.assertEqual(len(printed), 1)
        self.assertIn("Atomtomate/agents#11", printed[0])
        self.assertIn("did not ask", printed[0])

    def test_emphasis_between_the_phrase_and_the_reference_is_skipped(self):
        # A body writes the directive to be read, and bold is how it is read.
        bold = "**Merge after Atomtomate/agents#11.**\n\n" + FOLDED
        self.assertEqual(len(check_prs.notices([pr(188, body=bold)])), 1)
        local = "Merge after **#55**.\n\n" + FOLDED
        found = check_prs.findings([pr(55, draft=True, body=PLACEHOLDER), pr(63, body=local)])
        self.assertEqual(len(found), 1)
        self.assertIn("merge after #55", found[0])

    def test_a_resolved_open_dependency_is_a_finding_and_not_a_notice(self):
        body = "Merge after Atomtomate/agents#11.\n\n" + FOLDED
        states = {"Atomtomate/agents#11": "OPEN"}
        found = check_prs.findings([pr(188, body=body)], states)
        self.assertEqual(len(found), 1)
        self.assertIn("Atomtomate/agents#11", found[0])
        self.assertIn("is open", found[0])
        self.assertEqual(check_prs.notices([pr(188, body=body)], states), [])

    def test_a_resolved_merged_dependency_says_nothing_at_all(self):
        body = "Merge after Atomtomate/agents#11.\n\n" + FOLDED
        states = {"Atomtomate/agents#11": "MERGED"}
        self.assertEqual(check_prs.findings([pr(188, body=body)], states), [])
        self.assertEqual(check_prs.notices([pr(188, body=body)], states), [])

    def test_a_closed_unmerged_dependency_is_a_finding(self):
        # Not merged is not merged; the state is named so the reader can see which it was.
        body = "Merge after Atomtomate/agents#11.\n\n" + FOLDED
        found = check_prs.findings([pr(188, body=body)], {"Atomtomate/agents#11": "CLOSED"})
        self.assertEqual(len(found), 1)
        self.assertIn("is closed", found[0])

    def test_one_reference_gh_could_not_answer_is_still_a_notice(self):
        # Two dependencies, one resolved: the notice names only the one nobody read.
        body = "Merge after Atomtomate/agents#11 and merge after Atomtomate/other#3.\n\n" + FOLDED
        printed = check_prs.notices([pr(188, body=body)], {"Atomtomate/agents#11": "MERGED"})
        self.assertEqual(len(printed), 1)
        self.assertIn("Atomtomate/other#3", printed[0])
        self.assertNotIn("agents#11", printed[0])

    def test_a_draft_waiting_on_another_repository_is_not_noticed(self):
        body = "Merge after Atomtomate/agents#11.\n\n" + FOLDED
        self.assertEqual(check_prs.notices([pr(188, draft=True, body=body)]), [])

    def test_a_cross_repo_dependency_named_twice_is_one_notice(self):
        body = "Merge after Atomtomate/agents#11 — really, merge after Atomtomate/agents#11."
        found = check_prs.notices([pr(188, body=body + "\n\n" + FOLDED)])
        self.assertEqual(len(found), 1)

    def test_the_same_dependency_named_twice_is_one_finding(self):
        body = "Merge after #55 — really, merge after #55.\n\n" + FOLDED
        found = check_prs.findings([pr(55, draft=True, body=PLACEHOLDER), pr(63, body=body)])
        self.assertEqual(len(found), 1)


class AskingTheOtherRepositoryAboutItsPr(unittest.TestCase):
    """#190: the gate resolves a cross-repo dependency rather than asking the owner to."""

    def states_for(self, prs, answers):
        """`cross_repo_states` with gh replaced by a mapping of arguments to its JSON."""
        asked = []

        def fake(_gh, args):
            asked.append(args)
            return answers.get(f"{args[4]}#{args[2]}")

        with unittest.mock.patch.object(check_prs.gh_json, "fetch_or_none", fake):
            return check_prs.cross_repo_states(prs, None), asked

    def test_a_reference_gh_refused_is_asked_once_and_says_so(self):
        # Mapped to None rather than left out: absent means nobody asked, and the difference
        # is what tells a reader their token lost access instead of the run being offline.
        body = "Merge after Atomtomate/gone#4.\n\n" + FOLDED
        two = [pr(188, body=body), pr(189, body=body)]
        states, asked = self.states_for(two, {})
        self.assertEqual(states, {"Atomtomate/gone#4": None})
        self.assertEqual(len(asked), 1)
        printed = check_prs.notices(two, states)
        self.assertEqual(len(printed), 2)
        self.assertIn("would not answer", printed[0])
        self.assertNotIn("did not ask", printed[0])

    def test_nobody_asked_reads_differently_from_gh_refused(self):
        body = "Merge after Atomtomate/agents#11.\n\n" + FOLDED
        printed = check_prs.notices([pr(188, body=body)], {})
        self.assertEqual(len(printed), 1)
        self.assertIn("did not ask", printed[0])

    def test_gh_failing_leaves_pr_state_with_no_answer_rather_than_ending_the_run(self):
        # `fetch` ends the run on failure, which is right for this repository's own data and
        # wrong for a question about someone else's; without the swallow, --fetch would abort
        # on any cross-repo reference gh cannot read.
        def explode(_gh, _args):
            raise SystemExit("gh pr view failed: could not resolve to a Repository")

        with unittest.mock.patch.object(check_prs.gh_json, "fetch", explode):
            self.assertIsNone(check_prs.gh_json.pr_state(None, "Atomtomate/gone", "4"))

    def test_the_state_gh_reports_is_what_lands_in_the_mapping(self):
        body = "Merge after Atomtomate/agents#11.\n\n" + FOLDED
        states, asked = self.states_for([pr(188, body=body)], {"Atomtomate/agents#11": {"state": "MERGED"}})
        self.assertEqual(states, {"Atomtomate/agents#11": "MERGED"})
        self.assertEqual(asked, [["pr", "view", "11", "--repo", "Atomtomate/agents", "--json", "state"]])

    def test_the_same_reference_in_two_bodies_is_asked_once(self):
        body = "Merge after Atomtomate/agents#11.\n\n" + FOLDED
        two = [pr(188, body=body), pr(189, body=body)]
        _, asked = self.states_for(two, {"Atomtomate/agents#11": {"state": "OPEN"}})
        self.assertEqual(len(asked), 1)

    def test_a_draft_is_not_worth_a_network_call(self):
        body = "Merge after Atomtomate/agents#11.\n\n" + FOLDED
        _, asked = self.states_for([pr(188, draft=True, body=body)], {})
        self.assertEqual(asked, [])


class MergedIntoSomethingOtherThanMain(unittest.TestCase):
    """The after-the-fact half of the stacked-PR rule: did a merged PR's work reach main?"""

    def test_a_pr_merged_into_main_asks_git_nothing(self):
        def never(_oid):
            raise AssertionError("git was asked about a PR merged into main")

        self.assertEqual(check_prs.merged_findings([merged(125)], never), [])

    def test_a_base_that_has_since_reached_main_is_fine(self):
        found = check_prs.merged_findings([merged(80, base="claude/maintain")], lambda _oid: True)
        self.assertEqual(found, [])

    def test_a_base_main_does_not_hold_is_a_finding(self):
        found = check_prs.merged_findings([merged(80, base="claude/maintain")], lambda _oid: False)
        self.assertEqual(len(found), 1)
        self.assertIn("#80", found[0])
        self.assertIn("into `claude/maintain`", found[0])
        self.assertIn("not on main", found[0])

    def test_a_merge_commit_git_cannot_see_is_a_finding(self):
        found = check_prs.merged_findings([merged(80, base="claude/maintain")], lambda _oid: None)
        self.assertEqual(len(found), 1)
        self.assertIn("does not know", found[0])


class MergeLanded(unittest.TestCase):
    """`merge_landed` against a real repository: a commit on main, one off it, one unknown."""

    def test_on_main_off_main_and_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git(root, "init", "-q", "-b", "main")
            _git(root, "commit", "--allow-empty", "-q", "-m", "root")
            on_main = _git(root, "rev-parse", "HEAD")
            _git(root, "checkout", "-q", "-b", "side")
            _git(root, "commit", "--allow-empty", "-q", "-m", "side work")
            off_main = _git(root, "rev-parse", "HEAD")
            _git(root, "checkout", "-q", "main")
            self.assertIs(check_prs.merge_landed(root, on_main), True)
            self.assertIs(check_prs.merge_landed(root, off_main), False)
            self.assertIsNone(check_prs.merge_landed(root, "f" * 40))

    def test_origin_main_is_asked_before_a_local_main_that_differs(self):
        # The preference trunk.py fixes: the remote-tracking ref is the one asked, so a
        # commit only the local main holds is not "on main".
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git(root, "init", "-q", "-b", "main")
            _git(root, "commit", "--allow-empty", "-q", "-m", "root")
            _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
            _git(root, "commit", "--allow-empty", "-q", "-m", "only on the local main")
            self.assertIs(check_prs.merge_landed(root, _git(root, "rev-parse", "HEAD")), False)


class TrunkAhead(unittest.TestCase):
    """`trunk.ahead` against a real repository: the count itself, not just whether it is zero.

    Its callers read the count two ways -- `merge_landed` and `branch_merged` only ask
    whether it is zero, `worktree_status.py` prints it -- so a version that returned 1 for
    every commit main lacks would pass every other test in the suite. Tested here rather
    than beside `worktree_status.py`, whose own cases fake this, because this is where the
    git fixture lives (the same reason `TrunkRefresh` is here).
    """

    def test_zero_on_main_the_real_distance_off_it_and_none_for_an_unknown_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git(root, "init", "-q", "-b", "main")
            _git(root, "commit", "--allow-empty", "-q", "-m", "root")
            on_main = _git(root, "rev-parse", "HEAD")
            _git(root, "checkout", "-q", "-b", "side")
            for n in range(3):
                _git(root, "commit", "--allow-empty", "-q", "-m", f"side {n}")
            three_ahead = _git(root, "rev-parse", "HEAD")
            _git(root, "checkout", "-q", "main")
            self.assertEqual(trunk.ahead(root, on_main, "main"), 0)
            self.assertEqual(trunk.ahead(root, three_ahead, "main"), 3)
            self.assertIsNone(trunk.ahead(root, "f" * 40, "main"))

    def test_an_empty_commit_is_none_rather_than_silently_head(self):
        # `<ref>..` is git's own spelling of `<ref>..HEAD`, so without the guard the one
        # input a caller passes by accident is answered confidently about another commit.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git(root, "init", "-q", "-b", "main")
            _git(root, "commit", "--allow-empty", "-q", "-m", "root")
            _git(root, "checkout", "-q", "-b", "side")
            _git(root, "commit", "--allow-empty", "-q", "-m", "side")
            self.assertIsNone(trunk.ahead(root, "", "main"))
            self.assertIsNone(check_prs.merge_landed(root, ""))


class TrunkRefresh(unittest.TestCase):
    """`trunk.refresh` moves `origin/main` to the remote's tip; tested here, beside the check
    whose answer it decides, because this is where the git fixture lives."""

    def test_refresh_moves_origin_main_to_the_remote_tip(self):
        with tempfile.TemporaryDirectory() as tmp:
            remote, clone = Path(tmp) / "remote", Path(tmp) / "clone"
            _git(Path(tmp), "init", "-q", "-b", "main", str(remote))
            _git(remote, "commit", "--allow-empty", "-q", "-m", "root")
            _git(Path(tmp), "clone", "-q", str(remote), str(clone))
            _git(remote, "commit", "--allow-empty", "-q", "-m", "merged after the clone")
            tip = _git(remote, "rev-parse", "HEAD")
            self.assertIs(check_prs.merge_landed(clone, tip), None)  # stale: never seen
            trunk.refresh(clone)
            self.assertIs(check_prs.merge_landed(clone, tip), True)

    def test_refresh_without_a_remote_is_quiet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git(root, "init", "-q", "-b", "main")
            trunk.refresh(root)  # must not raise


class ReviewPassSection(unittest.TestCase):
    def test_none_when_absent(self):
        self.assertIsNone(reviews.review_pass_section("## Proof\n\nx\n"))

    def test_ends_at_the_next_heading_of_the_same_level(self):
        section = reviews.review_pass_section(PLACEHOLDER)
        self.assertEqual(section, "_To be filled after the four reviewers run._")


class ExitCodes(unittest.TestCase):
    """`main()` over a saved snapshot: 1 on a finding, 0 when every ready PR is in order."""

    def run_on(self, prs, merged_prs=None):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "prs.json"
            snapshot.write_text(json.dumps(prs), encoding="utf-8")
            command = [sys.executable, str(SCRIPT), "--prs", str(snapshot)]
            if merged_prs is not None:
                landed = Path(tmp) / "merged.json"
                landed.write_text(json.dumps(merged_prs), encoding="utf-8")
                command += ["--merged", str(landed)]
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        return result.returncode, result.stdout

    def run_fetching(self, prs, answer):
        """`main()` in process under `--fetch`, with gh and the trunk refresh stood in for.

        The subprocess helper above cannot pass `--fetch`: it would reach the network. This
        is the only way to pin the wire between `cross_repo_states` and `findings` -- dropping
        `states` from that call deletes the whole cross-repo check and leaves every function
        test green, which is exactly how the notice half broke earlier on this branch.
        """
        captured = _Captured()
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "prs.json"
            snapshot.write_text(json.dumps(prs), encoding="utf-8")
            landed = Path(tmp) / "merged.json"
            landed.write_text("[]", encoding="utf-8")
            argv = [str(SCRIPT), "--prs", str(snapshot), "--merged", str(landed), "--fetch"]
            with (
                unittest.mock.patch.object(sys, "argv", argv),
                unittest.mock.patch.object(check_prs.trunk, "refresh", lambda _root: None),
                unittest.mock.patch.object(check_prs.gh_json, "fetch_or_none", lambda *_: answer),
                contextlib.redirect_stdout(captured),
            ):
                code = check_prs.main()
        return code, captured.getvalue()

    def test_an_open_dependency_in_another_repository_fails_the_run(self):
        body = "Merge after Atomtomate/agents#11.\n\n" + FOLDED
        code, out = self.run_fetching([pr(188, body=body)], {"state": "OPEN"})
        self.assertEqual(code, 1)
        self.assertIn("Atomtomate/agents#11", out)
        self.assertIn("is open", out)

    def test_a_merged_dependency_in_another_repository_passes_the_run(self):
        body = "Merge after Atomtomate/agents#11.\n\n" + FOLDED
        code, out = self.run_fetching([pr(188, body=body)], {"state": "MERGED"})
        self.assertEqual(code, 0)
        self.assertIn("consistent", out)
        self.assertNotIn("agents#11", out)

    def test_a_finding_exits_one(self):
        code, out = self.run_on([pr(119, body=PLACEHOLDER)])
        self.assertEqual(code, 1)
        self.assertIn("prs: #119", out)

    def test_no_finding_exits_zero(self):
        code, out = self.run_on([pr(5), pr(6, draft=True, body=PLACEHOLDER)])
        self.assertEqual(code, 0)
        self.assertIn("consistent", out)

    def test_a_merged_list_of_main_bases_is_vouched_for_without_git(self):
        code, out = self.run_on([pr(5)], merged_prs=[merged(1), merged(2)])
        self.assertEqual(code, 0)
        self.assertIn("2 merged PR(s) is on main", out)

    def test_the_exemption_notice_reaches_stdout_and_does_not_fail_the_run(self):
        # `exemptions` was tested as a function while `main()` printed nothing: deleting
        # `report.verdict`'s notice loop left the suite green. This is the wire.
        code, out = self.run_on([pr(125, body=NOT_RUN, files=[])])
        self.assertEqual(code, 0)
        self.assertIn("pass-not-run exemption", out)
        self.assertIn("consistent", out)

    def test_the_cross_repo_notice_reaches_stdout_and_does_not_fail_the_run(self):
        # The same wire as the exemption above, and it broke the same way: deleting the
        # cross-repo case left every function test green while the gate said nothing.
        body = "Merge after Atomtomate/agents#11.\n\n" + FOLDED
        code, out = self.run_on([pr(188, body=body)])
        self.assertEqual(code, 0)
        self.assertIn("Atomtomate/agents#11", out)
        self.assertIn("consistent", out)

    def test_a_notice_prints_above_the_findings(self):
        two = [pr(119, body=PLACEHOLDER), pr(125, body=NOT_RUN, files=[])]
        code, out = self.run_on(two)
        self.assertEqual(code, 1)
        self.assertLess(out.index("pass-not-run exemption"), out.index("is ready for review but"))

    def test_a_merged_pr_off_main_reaches_git_through_main(self):
        # The wiring a stand-in cannot cover: main() handing merged_findings the real
        # merge_landed, asked in this repository about a commit it has never held.
        code, out = self.run_on(
            [pr(5)], merged_prs=[merged(80, base="claude/maintain", oid="f" * 40)]
        )
        self.assertEqual(code, 1)
        self.assertIn("prs: #80", out)
        self.assertIn("does not know", out)


class TheExemptionIsPrintedRatherThanTakenInSilence(unittest.TestCase):
    """#126: the one case the rule spells out is the one the script said nothing about."""

    def test_a_stated_reason_becomes_a_notice(self):
        notices = check_prs.notices([pr(125, body=NOT_RUN, files=[])])
        self.assertEqual(len(notices), 1)
        self.assertIn("#125", notices[0])
        self.assertIn("a docs-only record PR", notices[0])

    def test_a_folded_pass_is_not_an_exemption(self):
        self.assertEqual(check_prs.notices([pr(5)]), [])

    def test_a_placeholder_is_not_an_exemption(self):
        # "Not run yet." is a placeholder, not the exemption's "Not run: <reason>"; the
        # finding for it stands and must not be excused by a notice as well.
        excuse = "## Review pass\n\nNot run yet.\n"
        self.assertEqual(check_prs.notices([pr(8, body=excuse, files=[])]), [])
        self.assertEqual(len(check_prs.findings([pr(8, body=excuse, files=[])])), 1)

    def test_a_draft_claims_nothing(self):
        self.assertEqual(check_prs.notices([pr(125, draft=True, body=NOT_RUN, files=[])]), [])

    def test_the_reason_is_what_the_section_said(self):
        self.assertEqual(
            reviews.not_run_reason(pr(125, body=NOT_RUN, files=[])),
            "a docs-only record PR, the kind the session may merge.",
        )


if __name__ == "__main__":
    unittest.main()


class OutrunTest(unittest.TestCase):
    """`outrun` itself, on a repository: a stub for it proves nothing about the head it reads."""

    def _repo(self, root: Path) -> None:
        env = git_env()

        def git(*args: str) -> None:
            subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, env=env)

        def commit(path: str, message: str) -> None:
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text("x\n", encoding="utf-8")
            git("add", path)
            git("commit", "-q", "-m", message)

        git("init", "-q")
        git("checkout", "-q", "-b", "main")
        commit("README.md", "root")
        git("checkout", "-q", "-b", "claude/x")
        commit("web/a.ts", "code")
        for agent in reviews.REVIEWERS:
            commit(f"docs/reviews/x/{agent}.md", "reports")
        git("update-ref", "refs/remotes/origin/claude/x", "HEAD")
        self.git, self.commit = git, commit

    def test_a_code_commit_after_the_reports_is_named_and_a_report_at_the_tip_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            pr = {"headRefName": "claude/x"}
            self.assertEqual(check_prs.outrun(root, pr, fetch=False), [])
            self.commit("web/b.ts", "a fix nobody reviewed")
            self.git("update-ref", "refs/remotes/origin/claude/x", "HEAD")
            later = check_prs.outrun(root, pr, fetch=False)
            self.assertEqual(len(later), 1)
            self.assertIn("a fix nobody reviewed", later[0])

    def test_a_head_git_cannot_see_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            self.assertIsNone(check_prs.outrun(root, {"headRefName": "claude/elsewhere"}, fetch=False))
