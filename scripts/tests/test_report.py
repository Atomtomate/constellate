"""Tests for `scripts/report.py`, the tail every gating script shares.

Stdlib-only (`unittest`), matching `scripts/README.md`'s rule; run with
`python -m unittest discover scripts/tests`. `VerdictTest` pins the whole contract: what is
printed, in what order, under which prefix, and which exit status goes with it.

`TailRosterTest` pins the rule *around* it, over every script in the directory; its own
docstring says how.
"""

import ast
import io
import re
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import report  # noqa: E402

SCRIPTS = Path(__file__).resolve().parents[1]

#: What tells a script from the modules beside it -- `report.py`, `trunk.py`, `gh_json.py`,
#: `record.py`, which the scripts import and which run nothing. Read off the file rather
#: than listed here, so the list cannot go stale against the directory.
_MAIN_GUARD = 'if __name__ == "__main__":'


def _verdict(findings: list[str]) -> tuple[int, list[str]]:
    """Run `report.verdict` under a fixed prefix and return its exit status and its lines."""
    out = io.StringIO()
    with redirect_stdout(out):
        code = report.verdict(
            "x", findings, failed=f"{len(findings)} finding(s)", consistent="all in step"
        )
    return code, out.getvalue().splitlines()


def _readme_exits() -> dict[str, str]:
    """`{script name: its Exit column}` from `scripts/README.md`'s table of what lives here."""
    exits: dict[str, str] = {}
    for line in (SCRIPTS / "README.md").read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in re.split(r"(?<!\\)\|", line)]
        name = cells[1].strip("`")
        if name.endswith(".py"):
            exits[name] = cells[-2]
    return exits


def _scripts() -> list[Path]:
    """Every runnable script beside `report.py` — the ones carrying a `__main__` guard."""
    return [
        path
        for path in sorted(SCRIPTS.glob("*.py"))
        if _MAIN_GUARD in path.read_text(encoding="utf-8")
    ]


def _main_of(path: Path) -> ast.FunctionDef:
    """The script's `main`, which is the only function whose return value is an exit status.

    Scoped to `main` deliberately: `worktree_status.sweep_one` returns 1 as a *count* of
    refused removals, and a module-wide scan for "returns 1" would read that as an exit path
    and fail a script that is doing nothing wrong.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            return node
    raise AssertionError(f"{path.name} has a __main__ guard but no module-level main()")


def _calls(fn: ast.FunctionDef, name: str) -> bool:
    """Does `main` call `report.<name>` anywhere in its body?"""
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == name
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "report"
        for node in ast.walk(fn)
    )


def _bare_nonzero_returns(fn: ast.FunctionDef) -> list[int]:
    """Lines where `main` returns a non-zero constant instead of going through `report`."""
    return [
        node.lineno
        for node in ast.walk(fn)
        if isinstance(node, ast.Return)
        and isinstance(node.value, ast.Constant)
        and node.value.value not in (0, None)
    ]


class VerdictTest(unittest.TestCase):
    def test_findings_print_under_the_prefix_then_the_count_and_exit_one(self):
        code, lines = _verdict(["a is off", "b is off"])
        self.assertEqual(code, 1)
        self.assertEqual(lines, ["x: a is off", "x: b is off", "x: 2 finding(s)"])

    def test_no_findings_prints_the_consistent_line_and_exits_zero(self):
        code, lines = _verdict([])
        self.assertEqual(code, 0)
        self.assertEqual(lines, ["x: consistent — all in step"])

    def test_a_none_failed_line_leaves_the_findings_as_their_own_count(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = report.verdict("x", ["2 of 9 not clean"], failed=None, consistent="all in step")
        self.assertEqual(code, 1)
        self.assertEqual(out.getvalue().splitlines(), ["x: 2 of 9 not clean"])


class TailRosterTest(unittest.TestCase):
    """Every script leaves through `report`, and the README's Exit column agrees (#177).

    Derived from the scripts, then the table asserted against the derivation — not the other
    way round. Reading the roster *out of* the prose was how the first version of this test
    let `failure_ledger.py` past on the wording of its row, which is the failure #177 filed
    one size up: a rule held by a sentence.
    """

    def test_every_script_has_a_row_in_the_readme_table(self):
        # Both directions, the way check_docs.py checks its own tables: a script with no row,
        # and a row naming no script.
        self.assertEqual(sorted(path.name for path in _scripts()), sorted(_readme_exits()))

    def test_no_main_returns_non_zero_on_its_own(self):
        # The rule in its strongest form: with `verdict` and `abort` the only ways out, which
        # one a script takes is a fact about its code, and hand-rolling a tail is unspellable
        # rather than merely discouraged.
        for path in _scripts():
            with self.subTest(script=path.name):
                bare = _bare_nonzero_returns(_main_of(path))
                self.assertEqual(
                    bare,
                    [],
                    f"{path.name}:{bare} leaves main with a non-zero status directly — a "
                    "finding ends through report.verdict, anything else through report.abort",
                )

    def test_no_script_spells_the_trunk_name(self):
        # `trunk.NAME` owns it; a second spelling is where a stacked base or a renamed trunk
        # goes wrong quietly (the architecture review of PR #214 found the second one).
        for path in _scripts():
            with self.subTest(script=path.name):
                self.assertNotIn('"main"', path.read_text(encoding="utf-8"))

    def test_the_readme_exit_column_says_what_the_script_does(self):
        # The column is machine-read, so its two shapes are load-bearing: a cell opening
        # "always 0" promises the script never gates, anything else promises it does.
        exits = _readme_exits()
        for path in _scripts():
            with self.subTest(script=path.name):
                exit_cell = exits[path.name]
                self.assertRegex(
                    exit_cell,
                    r"^(always 0|1 )",
                    f"{path.name}'s Exit column must open 'always 0' or '1 ' — it is read",
                )
                self.assertEqual(
                    _calls(_main_of(path), "verdict"),
                    not exit_cell.startswith("always 0"),
                    f"{path.name} calls report.verdict or not; its row says otherwise "
                    f"({exit_cell!r})",
                )


if __name__ == "__main__":
    unittest.main()
