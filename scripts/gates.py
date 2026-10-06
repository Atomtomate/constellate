"""Run the checks a change calls for, here, before a push spends CI on the same answer.

Each CI workflow guards one area and is triggered by the paths that area owns. `AREAS`
below is where those path lists are written down, and `scripts/tests/test_gates.py` fails
when a workflow's `paths:` and the area here disagree -- so the question "what does this
change need checked" has one answer, and the hook and the build read the same one.

Two depths, because a gate nobody waits for is a gate everyone bypasses. `--quick` is what
`.githooks/pre-commit` runs: the record checks, the layering check, ruff, and the stdlib
test suite, nothing over about twenty seconds. The full run is `.githooks/pre-push`'s, and
adds whatever suites a build would otherwise be the first to fail on -- pytest, the
contract check, vitest, the client build, the compose file.

A check whose tool is not installed here is a notice, never a finding: a worktree with no
venv, a clone with no `node_modules`, a machine with Docker down. Skipping loudly keeps the
hook worth leaving on; failing there would teach every session to pass `--no-verify`, and a
gate that is always bypassed is worse than none, since it also reads as cover. `PROBES` is
where a toolchain's presence is asked.

What stays CI's alone: the Alembic checks. Both want a live database, and the drift one
writes a revision into `api/alembic/versions/` to read it back -- a file this has no
business leaving in someone's working tree when a run dies between the write and the
delete. Named on `api`'s `Area.ci_only`, which the result line carries, so a green run
here says what it did not prove.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import git_cmd
import report
import trunk

ROOT = Path(__file__).resolve().parent.parent
PREFIX = "gates"


#: The interpreter of `api/.venv`, which is where ruff, pytest and the API package live.
#: A worktree gets its own (the overlay's Toolchain); until it has one these checks skip
#: rather than run the main checkout's package and report *its* behaviour as this branch's.
VENV = ROOT / "api" / ".venv" / ("Scripts" if os.name == "nt" else "bin")


def _venv_tool(name: str) -> Path:
    """Where `api/.venv` would put `name`, installed or not -- `PROBES` decides whether it runs.

    Deliberately unconditional: returning None for a missing tool would make "nothing to
    run" a second way of saying "nothing installed", and the message would come from the
    wrong one -- a venv that existed but had no ruff in it would report the venv as absent.
    """
    return VENV / (f"{name}.exe" if os.name == "nt" else name)


@dataclass(frozen=True)
class Check:
    """One command, what it vouches for, and what has to be installed for it to say so.

    `quick` marks the checks fast enough for every commit; the rest run once per push.
    `needs` names the thing whose absence makes this a skip instead of a failure -- and
    `probe` answers whether it is here, so the reason a check skipped is reported in the
    same words the roster uses.
    """

    label: str
    argv: list[str]
    #: Only where `ci_fragment` cannot reach the workflow's spelling. `test_gates.py` holds
    #: an override to the command it stands for -- it must be a fragment of what
    #: `ci_fragment` derives -- so it can name less than the command does, never something
    #: else.
    ci: str = ""
    cwd: Path = ROOT
    quick: bool = False
    needs: str = ""
    #: Narrows this check within its area, for `--quick` only. The area's paths are what
    #: start its workflow, so the pre-push run keeps to them exactly and gets the build's
    #: answer early; the per-commit run can be finer, and is, because the common commit
    #: here touches Markdown and would otherwise wait on a test suite it cannot affect.
    paths: list[str] = field(default_factory=list)

    def probe(self) -> bool:
        """Is this check's toolchain present? A missing one is skipped, not failed."""
        return PROBES[self.needs]() if self.needs else True


def _docker_up() -> bool:
    """Does a Docker daemon answer? Wrapped in a timeout: a starting Desktop hangs, not fails."""
    try:
        done = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0


#: What each `needs` means, asked once. A row here rather than a branch in `probe`, so a
#: new toolchain costs a line; the key is also the words the skip is reported in, which is
#: why each one names the thing a reader would go and install.
PROBES = {
    "ruff": lambda: _venv_tool("ruff").exists(),
    "the api venv": lambda: _venv_tool("python").exists(),
    "web/node_modules": lambda: (ROOT / "web" / "node_modules").exists(),
    "docker": _docker_up,
}


def _py(*args: str) -> list[str]:
    """A bare-interpreter command -- the stdlib-only checks, which need no venv at all."""
    return [sys.executable, *args]


def _venv(tool: str, *args: str) -> list[str]:
    """A command run by one of `api/.venv`'s tools, whether or not it is installed there."""
    return [str(_venv_tool(tool)), *args]


def _npm(*args: str) -> list[str]:
    """An npm command. `npm` is a shim on Windows, so it is run through the shell there."""
    return ["npm.cmd", *args] if os.name == "nt" else ["npm", *args]


@dataclass(frozen=True)
class Area:
    """One area of the tree: the paths that own it, and the checks a change to them calls for.

    `paths` is the same list the area's workflow triggers on, in GitHub's own glob spelling.
    `test_gates.py` asserts the two agree, so a path added to one and not the other is a
    test failure rather than a build that silently stops guarding something.
    """

    name: str
    workflow: str
    paths: list[str]
    checks: list[Check] = field(default_factory=list)
    #: What this area's workflow runs that has no local counterpart at all, worded for the
    #: result line's "not run here" tail -- empty for an area with none. A fact about the
    #: area, so it lives beside the paths and checks that are also the area's: a step added
    #: to or removed from the workflow is a one-line diff here, not a new branch keyed on
    #: the area's name further down.
    ci_only: str = ""


AREAS = [
    Area(
        name="record",
        workflow="record.yml",
        # Everything. `check_docs.py` answers for links across the whole tree, so a rename
        # anywhere can break a handoff's link to it, and a deletion anywhere can dangle
        # one. It also puts the workflows and the hooks in an area that runs
        # `test_gates.py`, so the guard holding `AREAS` and the workflows together runs
        # when either changes.
        paths=["**"],
        checks=[
            Check("the written record", _py("scripts/check_docs.py"), quick=True),
            Check(
                "the layering",
                _py("scripts/check_layering.py"),
                quick=True,
                # Its subject is `api/`, but it is itself a script here, and an edit to the
                # checker is answered for by running it rather than by its fixtures alone.
                paths=["api/**", "scripts/check_layering.py"],
            ),
            Check(
                "the record scripts' own tests",
                _py("-m", "unittest", "discover", "scripts/tests"),
                quick=True,
                paths=["scripts/**", ".github/workflows/**", ".githooks/**"],
            ),
        ],
    ),
    Area(
        name="api",
        workflow="api.yml",
        paths=["api/**"],
        checks=[
            Check("lint", _venv("ruff", "check", "."), cwd=ROOT / "api", quick=True, needs="ruff"),
            Check(
                "formatting",
                _venv("ruff", "format", "--check", "."),
                cwd=ROOT / "api",
                quick=True,
                needs="ruff",
            ),
            Check(
                "the api tests",
                _venv("python", "-m", "pytest", "-q"),
                cwd=ROOT / "api",
                needs="the api venv",
            ),
            Check(
                "the OpenAPI contract",
                _venv("python", "scripts/export_openapi.py", "--check"),
                cwd=ROOT / "api",
                needs="the api venv",
            ),
        ],
        # The Alembic checks want a live database (module docstring), and the api tests
        # run on the one backend `CONSTELLATE_TEST_DATABASE_URL` selects, SQLite unless it
        # is set, while CI runs them on both: unconditional, unlike a skipped check, since
        # none of it has ever had a local counterpart to skip.
        ci_only=(
            "the Alembic round trip and drift check, and the api tests on their other "
            "backend (CI-only — need a live database)"
        ),
    ),
    Area(
        name="web",
        workflow="web.yml",
        # `api/openapi.json` too: the client's types are generated from that contract, so a
        # change to it can break this client without touching a file under `web/`.
        paths=["web/**", "api/openapi.json"],
        checks=[
            Check(
                "the generated client",
                _npm("run", "check:api-types"),
                cwd=ROOT / "web",
                needs="web/node_modules",
            ),
            Check("the web tests", _npm("test"), cwd=ROOT / "web", needs="web/node_modules"),
            Check(
                "the web build", _npm("run", "build"), cwd=ROOT / "web", needs="web/node_modules"
            ),
        ],
    ),
    Area(
        name="infra",
        workflow="infra.yml",
        # The workflow files too: a change to a workflow should be answered for by a run
        # of one. Only the compose file is checked while Q-E is open (ADR-0002's appendix
        # names the stack script's tests and the Caddyfile; both arrive with Q-E's answer).
        paths=["infra/**", "compose.yaml", ".github/workflows/**"],
        checks=[
            Check("the compose file", ["docker", "compose", "config", "--quiet"], needs="docker"),
        ],
    ),
]


def ci_fragment(check: Check) -> str:
    """What the area's workflow must contain to be running this same check.

    Derived from `argv`, never written beside it. A hand-written token pins a spelling
    rather than the command: changing what a check runs while the token still matched the
    workflow's old line would keep the test green while the hook checked something
    narrower than the build did.

    Two normalisations, because CI and a worktree spell the same command differently and
    for good reason: CI installs into the runner's own interpreter, so there is no
    `api/.venv` to name and no `python -m` before a console script. The interpreter is
    dropped, and so is a `-m` before a module, since the workflow's `run:` line names the
    script or module and not the `python` that starts it.
    """
    argv = list(check.argv)
    head, rest = Path(argv[0]).stem, argv[1:]
    if head.startswith("python"):
        head = ""
        if rest[:1] == ["-m"]:
            rest = rest[1:]
    return " ".join(([head] if head else []) + rest)


def matches(path: str, pattern: str) -> bool:
    """Does `path` fall under `pattern`, in the subset of GitHub's glob syntax `AREAS` uses?

    Three shapes, which is all the workflows spell: `dir/**` is everything under a directory,
    `**.md` is every file with a suffix anywhere in the tree, and anything else is one exact
    path. Kept this small on purpose -- a general globber here would let a pattern into the
    workflows that this agrees with and GitHub reads differently, which is the drift the
    shared list exists to stop.
    """
    if pattern.endswith("/**"):
        return path.startswith(pattern[:-2])
    if pattern.startswith("**"):
        return path.endswith(pattern[2:])
    return path == pattern


def _touches(changed: list[str], patterns: list[str]) -> bool:
    """Does any changed path fall under any of `patterns`?"""
    return any(matches(path, pattern) for path in changed for pattern in patterns)


def areas_for(changed: list[str]) -> list[Area]:
    """The areas `changed` touches, in `AREAS` order; empty when it touches none of them."""
    return [area for area in AREAS if _touches(changed, area.paths)]


def checks_for(changed: list[str], *, quick: bool) -> list[Check]:
    """The checks `changed` calls for: every check of every area it touches, or the quick few.

    Under `quick` a check that narrows itself with its own `paths` is asked about those
    instead of its area's, so a commit of one handoff runs the record check and not the
    test suite behind it. The full run ignores that narrowing on purpose: it stands in for
    the build, and the build has only the area's list to go on.
    """
    chosen: list[Check] = []
    for area in areas_for(changed):
        for check in area.checks:
            if not quick:
                chosen.append(check)
            elif check.quick and _touches(changed, check.paths or area.paths):
                chosen.append(check)
    return chosen


def not_run_here(areas: list[Area]) -> str:
    """The result line's own tail: what no run here can prove that CI will, or "".

    Folded into `consistent=` by `main` rather than printed as a notice: the result line is
    what a handoff or a PR body pastes as evidence, and a gap named above it never reaches
    the reader of the paste. Each touched area supplies its own unconditional gap
    (`Area.ci_only`); a toolchain this run skipped is a notice, since it is this machine's
    gap and not the change's.
    """
    gaps = [area.ci_only for area in areas if area.ci_only]
    return f"; not run here — {', '.join(gaps)}" if gaps else ""


def staged(root: Path) -> list[str]:
    """Paths staged for commit, deletions included -- what a pre-commit hook is asked about.

    No `--diff-filter`: excluding `D` would let a commit that only deleted files select no
    area and run nothing -- and a deletion is exactly when `check_docs.py` earns its place,
    since what it catches is the link the deletion just broke.
    """
    return git_cmd.lines(root, "diff", "--cached", "--name-only")


def pushing(root: Path, rev: str = "HEAD") -> list[str]:
    """Paths `rev` changes against main -- what a push would put in front of the build.

    Against the merge base rather than main's tip, so a branch that has not merged main in
    is not asked to answer for what landed there meanwhile. With no trunk ref to compare to
    -- a clone that has never fetched -- the answer is every tracked file, which runs
    everything rather than quietly running nothing.
    """
    ref = trunk.ref(root)
    if not ref:
        return git_cmd.lines(root, "ls-files")
    base = git_cmd.first(root, "merge-base", ref, rev)
    return git_cmd.lines(root, "diff", "--name-only", f"{base or ref}..{rev}")


def push_revs(stream) -> list[str]:
    """The local shas git names on a pre-push stdin, skipping a branch deletion's zero sha.

    git writes one `<local ref> <local sha> <remote ref> <remote sha>` line per ref being
    pushed. Parsed here rather than in the hook: every other "what changed" question in this
    repository is Python, and in awk the deletion case and the several-refs case could only
    be pinned by matching the hook's source text -- which is a spelling, not a behaviour.
    """
    revs = []
    for line in stream:
        parts = line.split()
        if len(parts) >= 2 and set(parts[1]) != {"0"}:
            revs.append(parts[1])
    return revs


def gating_split(root: Path, revs: list[str], head: str) -> tuple[list[str], list[str]]:
    """Split `revs` into the ones this worktree can answer for and the ones it cannot.

    Every check runs against the working tree, so a revision that is not this worktree's
    HEAD cannot be gated here at all: selecting its changed paths and then running the
    checks would report on whatever happens to be checked out. Pushing a branch from a
    different checkout is exactly that case.
    """
    gating, elsewhere = [], []
    for rev in revs:
        resolved = git_cmd.first(root, "rev-parse", rev) or rev
        (gating if resolved == head else elsewhere).append(rev)
    return gating, elsewhere


def run(checks: list[Check]) -> tuple[list[str], list[str]]:
    """Run `checks` in order, printing each one's output; return its findings and its notices.

    Output goes straight to the terminal as it happens rather than being captured: what a
    session needs from a failed gate is the failure, and a summary line that says "the
    tests failed" without the traceback under it just sends the reader to run it again.
    """
    findings: list[str] = []
    notices: list[str] = []
    for check in checks:
        if not check.probe():
            notices.append(f"skipped {check.label} — {check.needs} is not here")
            continue
        print(f"{PREFIX}: {check.label} …", flush=True)
        try:
            done = subprocess.run(check.argv, cwd=check.cwd)
        except OSError as exc:
            # The probe answers for the toolchain, not for PATH: a binary can be installed
            # and absent from a GUI client's environment. Raising here would abort the push
            # with a traceback, which is the one thing the skip-don't-fail rule exists to
            # prevent.
            notices.append(f"skipped {check.label} — {check.argv[0]} would not start ({exc})")
            continue
        if done.returncode != 0:
            findings.append(f"{check.label} failed")
    return findings, notices


def main() -> int:
    """Run the gates the change calls for; 1 on a failing check, 0 when there is nothing owed."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--staged", action="store_true", help="check what is staged for commit (pre-commit)"
    )
    source.add_argument(
        "--branch", action="store_true", help="check what this branch changes (pre-push)"
    )
    parser.add_argument(
        "--rev", default="HEAD", help="with --branch: the commit being pushed (default HEAD)"
    )
    parser.add_argument(
        "--push-refs",
        action="store_true",
        help="with --branch: read the refs being pushed from git's pre-push stdin",
    )
    parser.add_argument(
        "--quick", action="store_true", help="only the checks fast enough for every commit"
    )
    args = parser.parse_args()

    owed: list[str] = []
    if args.staged:
        changed = staged(ROOT)
    else:
        revs = push_revs(sys.stdin) if args.push_refs else [args.rev]
        head = git_cmd.first(ROOT, "rev-parse", "HEAD") or ""
        gating, elsewhere = gating_split(ROOT, revs, head)
        owed = [
            f"not gating {rev[:12]} — the checks read this worktree, which is at {head[:12]}"
            for rev in elsewhere
        ]
        changed = sorted({path for rev in gating for path in pushing(ROOT, rev)})

    areas = areas_for(changed)
    checks = checks_for(changed, quick=args.quick)
    if not checks:
        touched = ", ".join(area.name for area in areas) or "no gated area"
        return report.verdict(
            PREFIX,
            [],
            failed=None,
            consistent=f"{len(changed)} changed path(s) — {touched} — nothing to run",
            notices=owed,
        )

    findings, notices = run(checks)
    tail = not_run_here(areas)
    return report.verdict(
        PREFIX,
        findings,
        failed=f"{len(findings)} of {len(checks)} check(s) failed",
        consistent=f"{', '.join(a.name for a in areas)} — {len(checks)} check(s){tail}",
        notices=owed + notices,
    )


if __name__ == "__main__":
    raise SystemExit(main())
