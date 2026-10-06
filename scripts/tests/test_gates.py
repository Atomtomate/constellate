"""The hooks and the build agree on what a change needs checked.

`scripts/gates.py` decides which checks a change calls for; the workflows under
`.github/workflows/` decide which builds it starts. Both answer from a path list, and the
lists have to be the same one -- a path added to a workflow and not to `AREAS` is an area
the hooks stop guarding before a push, and the reverse is a build that stops running while
the hook still says the change is covered. Neither failure shows up as a red build, which
is exactly why it is pinned here.

Stdlib-only (`unittest`), matching `scripts/README.md`'s rule; run with
`python -m unittest discover scripts/tests`. The YAML is read by the small reader below
rather than a parser: the dependency is not available to a bare interpreter, and the shape
being read is fixed.
"""

import ast
import io
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gates  # noqa: E402

SCRIPTS = Path(__file__).resolve().parents[1]
WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def paths_blocks(text: str) -> list[list[str]]:
    """Every `paths:` list in a workflow, in order -- one per trigger that carries one.

    A block is the run of `- "…"` items indented under a line that is exactly `paths:`;
    it ends at the first line that is not one. Quotes are stripped, since the workflows
    spell every pattern with them and `AREAS` holds bare strings.
    """
    blocks: list[list[str]] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != "paths:":
            continue
        block: list[str] = []
        for candidate in lines[index + 1 :]:
            stripped = candidate.strip()
            if not stripped.startswith("- "):
                break
            block.append(stripped[2:].strip().strip('"').strip("'"))
        blocks.append(block)
    return blocks


class WorkflowPathsTest(unittest.TestCase):
    def test_every_area_names_a_workflow_that_exists(self):
        for area in gates.AREAS:
            with self.subTest(area=area.name):
                self.assertTrue(
                    (WORKFLOWS / area.workflow).is_file(),
                    f"{area.name} names {area.workflow}, which is not in .github/workflows/",
                )

    def test_every_workflow_is_claimed_by_an_area(self):
        # The other direction: a workflow no area owns is one the hooks never run the
        # local half of, and nothing else would say so.
        self.assertEqual(
            sorted(path.name for path in WORKFLOWS.glob("*.yml")),
            sorted(area.workflow for area in gates.AREAS),
        )

    def test_each_workflow_triggers_on_exactly_its_area_s_paths(self):
        for area in gates.AREAS:
            text = (WORKFLOWS / area.workflow).read_text(encoding="utf-8")
            blocks = paths_blocks(text)
            with self.subTest(area=area.name):
                self.assertTrue(blocks, f"{area.workflow} has no paths: filter at all")
                for block in blocks:
                    # Every trigger in the file filters the same way. A pull_request that
                    # guards more than the push does (or less) is the drift in miniature.
                    self.assertEqual(
                        block,
                        area.paths,
                        f"{area.workflow} triggers on {block}; gates.AREAS says {area.paths}",
                    )


class MatchTest(unittest.TestCase):
    """`matches` reads the three glob shapes the workflows spell, and nothing else."""

    def test_a_directory_pattern_covers_everything_under_it(self):
        self.assertTrue(gates.matches("app/src/main.py", "app/**"))
        self.assertTrue(gates.matches("app/pyproject.toml", "app/**"))
        self.assertFalse(gates.matches("web/src/main.tsx", "app/**"))
        # The prefix is the directory, not the bare name: `appdocs/x` is not under `app/`.
        self.assertFalse(gates.matches("appdocs/x.py", "app/**"))

    def test_a_suffix_pattern_covers_the_whole_tree(self):
        self.assertTrue(gates.matches("README.md", "**.md"))
        self.assertTrue(gates.matches("docs/adr/0001-fleet.md", "**.md"))
        self.assertFalse(gates.matches("docs/adr/0001-fleet.txt", "**.md"))

    def test_anything_else_is_one_exact_path(self):
        self.assertTrue(gates.matches("app/openapi.json", "app/openapi.json"))
        self.assertFalse(gates.matches("app/openapi.json.bak", "app/openapi.json"))


class AreasForTest(unittest.TestCase):
    def test_a_markdown_only_change_asks_for_the_record_area_alone(self):
        self.assertEqual(
            [area.name for area in gates.areas_for(["docs/handoffs/2026-09-21-x.md"])],
            ["record"],
        )

    def test_the_gate_s_own_machinery_is_guarded_by_something(self):
        # A workflow edit or a hook edit must run test_gates.py, the only thing holding
        # AREAS and the workflows together.
        for change in ([".github/workflows/record.yml"], [".githooks/pre-push"]):
            with self.subTest(change=change):
                labels = [c.label for c in gates.checks_for(change, quick=True)]
                self.assertIn("the record scripts' own tests", labels)

    def test_a_code_only_change_still_checks_the_record(self):
        # A rename anywhere can dangle a handoff's link to it; if check_docs.py does not
        # run here it fails an unrelated later pull request instead.
        labels = [c.label for c in gates.checks_for(["src/anything.py"], quick=True)]
        self.assertIn("the written record", labels)

    def test_no_path_in_the_tree_falls_outside_every_area(self):
        # The `record` area covers everything on purpose, so this is a guarantee rather
        # than a gap: whatever a commit touches, at least check_docs.py answers for it.
        for path in (".gitattributes", "README.md", "src/x.py", ".githooks/x"):
            with self.subTest(path=path):
                self.assertIn("record", [a.name for a in gates.areas_for([path])])

    def test_a_quick_run_skips_a_suite_the_change_cannot_affect(self):
        # One handoff committed: the record check runs, the test suite behind it does not.
        # This is the difference between a hook sessions leave on and one they learn to
        # pass --no-verify to.
        changed = ["docs/handoffs/2026-09-21-x.md"]
        quick = [check.label for check in gates.checks_for(changed, quick=True)]
        self.assertEqual(quick, ["the written record"])

    def test_a_scripts_change_does_pull_in_that_suite(self):
        changed = ["scripts/gates.py"]
        quick = [check.label for check in gates.checks_for(changed, quick=True)]
        self.assertIn("the record scripts' own tests", quick)

    def test_the_full_run_ignores_the_narrowing_and_stands_in_for_the_build(self):
        # The pre-push run answers for what the workflow will do, and the workflow has only
        # the area's path list -- so a narrowed check is still owed here.
        changed = ["docs/handoffs/2026-09-21-x.md"]
        full = [check.label for check in gates.checks_for(changed, quick=False)]
        self.assertEqual(full, [check.label for check in gates.AREAS[0].checks])

    def test_every_check_has_a_command_and_a_probe_that_is_defined(self):
        # Absence is one mechanism: the command is always well formed and `needs` alone
        # decides whether it runs, so an empty argv or an unknown `needs` is the drift.
        for area in gates.AREAS:
            for check in area.checks:
                with self.subTest(area=area.name, check=check.label):
                    self.assertTrue(check.argv, f"{check.label} has no command")
                    if check.needs:
                        self.assertIn(check.needs, gates.PROBES, f"{check.label}: unknown needs")

    def test_a_deletion_is_a_change_the_gate_sees(self):
        # `staged()` must not pass a --diff-filter that excludes deletions: a commit that
        # only deletes files would select nothing and run nothing, and a deletion is when
        # check_docs.py earns its place. Read off the call's arguments, not the source text:
        # the docstring says "--diff-filter" to explain its absence.
        tree = ast.parse((SCRIPTS / "gates.py").read_text(encoding="utf-8"))
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "staged")
        args = [n.value for n in ast.walk(fn) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertIn("--cached", args)
        self.assertEqual([a for a in args if a.startswith("--diff-filter")], [])

    def test_a_binary_that_will_not_start_is_a_notice_and_not_a_finding(self):
        # The probe answers for the toolchain, not for PATH. A check whose binary is absent
        # anyway must skip rather than abort the hook with a traceback.
        check = gates.Check("a missing binary", ["definitely-not-a-real-binary-xyz"], ci="")
        findings, notices = gates.run([check])
        self.assertEqual(findings, [])
        self.assertEqual(len(notices), 1)
        self.assertIn("a missing binary", notices[0])


class WorkflowCommandsTest(unittest.TestCase):
    """Each local check names a fragment of the `run:` line its workflow runs it with.

    The path lists being in step says the same builds start; this says the same commands
    run once they do. Only this direction is asserted: a workflow step with no check here
    is not drift, since a step may want something only CI has.
    """

    def run_lines(self, workflow: str) -> str:
        """A workflow flattened, comments stripped -- what it runs, not what explains it."""
        text = (WORKFLOWS / workflow).read_text(encoding="utf-8")
        kept = [line for line in text.splitlines() if not line.lstrip().startswith("#")]
        return " ".join(" ".join(kept).split())

    def test_every_check_appears_in_its_area_s_workflow(self):
        for area in gates.AREAS:
            lines = self.run_lines(area.workflow)
            for check in area.checks:
                with self.subTest(area=area.name, check=check.label):
                    fragment = check.ci or gates.ci_fragment(check)
                    self.assertIn(
                        fragment,
                        lines,
                        f"{area.workflow} does not run {fragment!r}, which {check.label} "
                        "runs locally — one of the two stopped doing what the other says",
                    )

    def test_an_override_still_stands_for_the_command_it_names(self):
        # An override may name less than the command does, never something else -- which is
        # what a hand-written fragment was free to do before it was derived.
        for area in gates.AREAS:
            for check in area.checks:
                if check.ci:
                    with self.subTest(check=check.label):
                        self.assertIn(check.ci, gates.ci_fragment(check))

    def test_a_command_that_drifts_from_its_workflow_fails(self):
        # The hole the derivation closes: changing what the local check does, while the
        # workflow keeps doing the old thing, must not stay green.
        drifted = gates.Check("the written record", gates._py("scripts/check_docs.py", "--strict"))
        self.assertNotIn(gates.ci_fragment(drifted), self.run_lines("record.yml"))


class HookTest(unittest.TestCase):
    """The two hooks run the gate the way their own headers say they do."""

    HOOKS = Path(__file__).resolve().parents[2] / ".githooks"

    def hook(self, name: str) -> str:
        return (self.HOOKS / name).read_text(encoding="utf-8")

    def test_each_hook_invokes_the_gate_with_the_depth_it_claims(self):
        self.assertIn("gates.py --staged --quick", self.hook("pre-commit"))
        self.assertIn("gates.py --branch --push-refs", self.hook("pre-push"))

    def code(self, name: str) -> str:
        """A hook with its comments stripped -- what actually runs, not what explains it."""
        kept = [
            line for line in self.hook(name).splitlines() if not line.lstrip().startswith("#")
        ]
        return "\n".join(kept)

    def test_pre_push_decides_on_arguments_and_not_on_a_terminal(self):
        # `[ -t 0 ]` hangs forever when the hook is run by hand from anything that is not a
        # terminal -- a script, a pipe -- because stdin is then open and silent. git passes
        # the remote's name and URL; a hand run passes neither. Read off the code: the
        # header names the rejected form in order to explain it.
        self.assertNotIn("-t 0", self.code("pre-push"))
        self.assertIn('[ "$#" -ge 2 ]', self.code("pre-push"))

    def test_both_hooks_resolve_the_committing_worktree_before_anything_else(self):
        # core.hooksPath can point at another checkout's copy of these files, so a hook
        # that trusted its own location would answer about the wrong tree.
        for name in ("pre-commit", "pre-push"):
            with self.subTest(hook=name):
                text = self.hook(name)
                self.assertIn("--show-toplevel", text)
                # GIT_INDEX_FILE too: git sets it for pre-commit, and this suite commits in
                # scratch repositories -- with it inherited, those commits would write into
                # the committing worktree's index.
                self.assertIn("unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE", text)


class PushRefsTest(unittest.TestCase):
    """What git puts on a pre-push stdin, and which of it this worktree can answer for."""

    ZERO = "0" * 40

    def revs(self, text: str) -> list[str]:
        return gates.push_revs(io.StringIO(text))

    def test_the_local_sha_of_each_ref_is_taken(self):
        lines = [
            "refs/heads/a aaa111 refs/heads/a bbb222",
            f"refs/heads/b ccc333 refs/heads/b {self.ZERO}",
        ]
        self.assertEqual(self.revs("\n".join(lines)), ["aaa111", "ccc333"])

    def test_a_branch_deletion_has_nothing_to_check(self):
        # git sends an all-zero local sha for `git push --delete`.
        line = f"refs/heads/gone {self.ZERO} refs/heads/gone ccc333"
        self.assertEqual(self.revs(line), [])

    def test_an_empty_or_ragged_stdin_yields_nothing_rather_than_raising(self):
        self.assertEqual(self.revs(""), [])
        self.assertEqual(self.revs("\n\nrubbish\n"), [])

    def test_only_this_worktree_s_head_can_be_gated(self):
        # Every check runs against the working tree, so a revision that is not HEAD cannot
        # be answered for here at all.
        head = gates.git_cmd.first(gates.ROOT, "rev-parse", "HEAD")
        if head is None:
            # `git archive HEAD` extracted to a clean directory is not a repository, and
            # running the suite there is exactly how the tree a commit *records* gets
            # checked rather than the one on disk. This case has nothing to ask git about.
            self.skipTest("not a git repository -- an extract of a commit, not a worktree")
        gating, elsewhere = gates.gating_split(gates.ROOT, ["HEAD", "origin/main"], head)
        self.assertEqual(gating, ["HEAD"])
        self.assertEqual(elsewhere, ["origin/main"])


class ProductAreasTest(unittest.TestCase):
    """The three areas the scaffold brought beside `record`, and the gap CI alone closes."""

    def test_the_contract_pulls_in_the_client(self):
        # The web client's types are generated from api/openapi.json, so the contract
        # changing starts the web build too -- without touching a file under web/.
        areas = [area.name for area in gates.areas_for(["api/openapi.json"])]
        self.assertEqual(areas, ["record", "api", "web"])

    def test_a_workflow_edit_runs_the_infra_area(self):
        # A change to a workflow is answered for by a run of one (ADR-0002's appendix).
        areas = [area.name for area in gates.areas_for([".github/workflows/api.yml"])]
        self.assertIn("infra", areas)

    def test_an_api_change_names_what_only_ci_runs(self):
        # The Alembic checks want a live database and never run here; a green result line
        # for an api change has to say so, since that line is what a PR body pastes.
        self.assertIn("Alembic", gates.not_run_here(gates.areas_for(["api/x.py"])))

    def test_a_record_only_change_names_no_gap(self):
        # record's paths are ["**"], so it is touched by everything -- api's gap must not
        # leak into a change that never touched api/.
        self.assertEqual(gates.not_run_here(gates.areas_for(["scripts/gates.py"])), "")

    def test_main_folds_the_gap_into_the_result_line(self):
        # Nothing else calls `main`, so the two lines wiring `not_run_here` in could be
        # deleted with the rest of the suite still green.
        class _Capture(io.StringIO):
            def reconfigure(self, **_kwargs):
                pass

        out = _Capture()
        with (
            mock.patch.object(sys, "argv", ["gates.py", "--staged"]),
            mock.patch.object(sys, "stdout", out),
            mock.patch.object(gates, "staged", return_value=["api/x.py"]),
            mock.patch.object(gates, "run", return_value=([], [])),
        ):
            gates.main()
        last_line = out.getvalue().strip().splitlines()[-1]
        self.assertIn("gates: consistent", last_line)
        self.assertIn("Alembic", last_line)


if __name__ == "__main__":
    unittest.main()
