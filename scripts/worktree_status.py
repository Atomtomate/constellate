"""Report the working state of every git worktree, so a session confirms its status by check.

Sessions kept leaving uncommitted work behind for the next one to trip over, and a prose
"tree is clean" in a report is not a check -- it is a claim, and the claim was wrong often
enough to matter. This answers the question mechanically and the same way every run: for
each worktree, is the tree clean, are there untracked files, and how far has the branch
drifted from its upstream.

Git answers all of that. The one question it cannot is whether a squash-merged branch's work
reached `main`, which `merged_heads` explains and `--remove` takes `--merged`/`--fetch` to
ask GitHub (#197). No other run asks it anything.

    python scripts/worktree_status.py --current   # just this worktree; for a closing check
    python scripts/worktree_status.py             # every worktree
    python scripts/worktree_status.py --remove    # and delete the ones git can reconstruct
    python scripts/worktree_status.py --remove --unattended   # the 04:00 task; #178
    python scripts/worktree_status.py --remove --fetch        # ...squash-merged ones too

What each of those exits 1 on is `scripts/README.md`'s Exit column, which a test reads --
restating it here is how this docstring came to describe a rule two changes out of date.
The short of it: a tree that strands a session fails the run, and `--unattended` says no
session is behind this one, so another tree's uncommitted work is not its business. Git
refusing to *read* a worktree fails every run, that one included.

Unpushed commits are reported but do not fail the run: a branch waiting for its PR is ahead
of its upstream on purpose, and a WIP commit is the sanctioned way to set work aside. The
failure this guards against is work that was never committed at all. Nor does the last
column fail it -- whether `main` already holds the worktree's HEAD, which is what makes a
clean worktree a removal candidate (#143).

`--remove` is the one thing under `scripts/` that changes anything; `scripts/README.md`
carries the exception it runs under. What may go is `why_kept`'s to say, and what
`git worktree prune` cannot see is `husks`'. Why a flag rather than a session remembering
to run `git worktree remove`: #172.

Each worktree's own `core.hooksPath` is checked too, in the same loop; see
`hooks_path_finding` for why it's per-worktree rather than read once.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

import git_cmd
from typing import NamedTuple

import gh_json
import report
import trunk

# How long a worktree must have sat untouched before `--remove` will delete it. The guard is
# against a live session, not against haste: see `idle_hours`.
IDLE_HOURS = 24.0

# The directory the desktop app creates worktrees in, and the only one swept for husks.
APP_WORKTREES = Path(".claude/worktrees")

# The one shape of ignored file this repository has that a person wrote and git cannot give
# back (`infra/.env`). Everything else `.gitignore` covers is output or machine-local state,
# which is the repository declaring it disposable -- `.claude/settings.local.json` is in
# every worktree, so "any ignored file keeps it" would keep all of them forever.
HAND_WRITTEN = ".env"


def _git(args: list[str], cwd: Path | None = None) -> str:
    """Run git and return stdout; the empty string when it fails (no upstream, say).

    `--no-optional-locks` goes on every command from here. `git status` otherwise writes the
    refreshed index back, and that file's timestamp is what `idle_hours` reads to decide
    whether a session is standing in the worktree: a reader that moves the clock it reads
    keeps every worktree looking live, and `--remove` would then delete nothing, ever. The
    flag lived at the two `status` call sites until a review pointed out that the next
    worktree-directed command would have to remember it; here it is true by construction.
    """
    result = git_cmd.run(
        "--no-optional-locks", *args, cwd=cwd, text=True, encoding="utf-8"
    )
    return result.stdout if result.returncode == 0 else ""


def _git_ok(args: list[str], cwd: Path | None = None) -> bool:
    """Did git succeed? For the commands whose answer is the exit code, not stdout."""
    return (
        git_cmd.run(
            "--no-optional-locks", *args, cwd=cwd, text=True, encoding="utf-8"
        ).returncode
        == 0
    )


def _git_fed(args: list[str], fed: list[str], cwd: Path | None = None) -> list[str]:
    """Run git with `fed` on its stdin, a line each, and return its output lines.

    The batching form. `check-ignore --stdin`, `hash-object --stdin-paths` and
    `cat-file --batch-check` each answer for a whole list in one process, and that is what
    keeps the husk scan from costing a process per file: a half-removed worktree holds the
    whole tree, and at a process apiece the scan took minutes (#176 review).
    """
    if not fed:
        return []
    result = git_cmd.run(
        "--no-optional-locks", *args,
        cwd=cwd, input="\n".join(fed) + "\n", text=True, encoding="utf-8",
    )
    return result.stdout.splitlines()


class State(NamedTuple):
    """One reading of a worktree: git's refusal, or what its tree holds and where it stands.

    Read once per worktree and handed to both the report line and the removal rule. They
    used to ask git the same three questions in turn, six `git status` runs per removal
    candidate -- and a criterion added to one of them would have gone missing from the
    other, which is the disagreement `why_kept` exists to prevent (#176 review).
    """

    complaint: str | None
    counts: tuple[int, int, int]
    hand_written: tuple[str, ...]
    merged: str | None
    #: The PR this worktree's HEAD was merged as *when `main` does not hold it* -- the
    #: squash path (#197). 0 when there is none, and 0 when `main` holds the HEAD anyway,
    #: so no reader re-applies that qualifier. In `State` and not a parameter beside it,
    #: because this docstring's own promise is that a criterion added to one reader cannot
    #: go missing from the other: as a parameter it did, and the listing printed
    #: `ahead 6 of main` for a worktree the next line deleted (#216 review).
    merged_as: int = 0
    #: Whether `main` holds this worktree's HEAD -- `against_trunk`'s own count, not its
    #: sentence read back (#223 review). False for a worktree git could not place at all.
    on_trunk: bool = False


def read_status(path: Path) -> tuple[str | None, tuple[int, int, int], tuple[str, ...]]:
    """git's complaint when it will not read this worktree, and what its tree holds when it will.

    One `git status --porcelain --ignored`, because the refusal, the (staged, unstaged,
    untracked) counts and the ignored entries are that one command's three answers. A caller
    that could get the counts without the refusal is a caller that can repeat #172: `""` was
    returned both for a worktree git would not read and for a worktree with nothing to
    report, and the three the desktop app created under Administrator ownership were
    reported clean for months.

    The ignored entries are here because `git worktree remove --force` deletes them too and
    a plain `status` does not show them. Most of them are the repository declaring its own
    output disposable -- `api/.venv/`, `__pycache__/`, `.claude/settings.local.json`. A
    `.env` is the exception: ignored by design *and* written by hand, so it is named and it
    keeps the worktree. Directories come back with a trailing slash and files without, which
    is how a wholly-ignored directory is told from a file inside a kept one.

    Ownership is the refusal seen: a worktree created by an elevated process belongs to
    `S-1-5-32-544`, and git refuses the repository rather than trusting it. The remedy is
    git's own, printed with the finding, because a session guessing at `takeown` is worse
    than telling it what git already said.
    """
    try:
        result = git_cmd.run(
            "--no-optional-locks", "status", "--porcelain", "--ignored",
            cwd=path, text=True, encoding="utf-8",
        )
    except OSError:
        return "its directory is gone -- run `git worktree prune`", (0, 0, 0), ()
    if result.returncode != 0:
        if "dubious ownership" in result.stderr:
            remedy = f"`git config --global --add safe.directory {path.as_posix()}`"
            return f"dubious ownership -- {remedy}", (0, 0, 0), ()
        lines = result.stderr.strip().splitlines()
        return (lines[0] if lines else f"git exited {result.returncode}"), (0, 0, 0), ()

    staged = unstaged = untracked = 0
    hand_written: list[str] = []
    for line in result.stdout.splitlines():
        mark, _, entry = line.partition(" ")
        if mark == "!!":
            if not entry.endswith("/") and Path(entry).name.startswith(HAND_WRITTEN):
                hand_written.append(entry)
            continue
        if line[:2] == "??":
            untracked += 1
            continue
        if line[:1] not in " ?":
            staged += 1
        if line[1:2] not in " ":
            unstaged += 1
    return None, (staged, unstaged, untracked), tuple(hand_written)


def read_state(path: Path, trunk_ref: str | None, merged_as: int) -> State:
    """Read a worktree once, for the line and for the rule.

    `merged_as` is the caller's to resolve -- `merged_here` against the mapping `--fetch`
    brings back -- because it is the one fact here that is not git's to answer. It is
    normalised away where it cannot apply, so every reader of the field means one thing
    by it: a worktree git would not read claims nothing, and one `main` already holds
    needs no second proof.
    """
    complaint, counts, hand_written = read_status(path)
    merged, on_trunk = (None, False) if complaint else against_trunk(path, trunk_ref)
    spent = 0 if complaint or on_trunk else merged_as
    return State(complaint, counts, hand_written, merged, spent, on_trunk)


def worktrees(repo: Path) -> list[dict[str, str]]:
    """Parse `git worktree list --porcelain` into one dict per worktree."""
    out = _git(["worktree", "list", "--porcelain"], cwd=repo)
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in out.splitlines():
        if not line.strip():
            if current:
                entries.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    if current:
        entries.append(current)
    return entries


def containing(entries: list[dict[str, str]], here: Path) -> Path | None:
    """The worktree `here` sits in: the longest listed path that is `here` or a parent of it.

    Not "any ancestor of cwd", which is what this used to test. This repository keeps its
    worktrees at `.claude/worktrees/`, inside the main checkout, so the main checkout is an
    ancestor of every one of them and the ancestor test scoped it into every `--current`
    run (#157). A session whose own tree was spotless then failed its closing check on a
    stray file in the main checkout that no session created -- which teaches the reader to
    disbelieve a red check, and that is worse than not running one.

    The ancestor test was there for a reason worth keeping: a session may run this from a
    subdirectory of its worktree, where the worktree's path is a parent of cwd rather than
    equal to it. Taking the nearest match keeps that case and drops the rest.

    None when cwd is in no listed worktree at all, which `main()` refuses to gate on.
    """
    here_and_parents = (here, *here.parents)
    listed = (Path(e["worktree"]).resolve() for e in entries)
    contains = [p for p in listed if p in here_and_parents]
    return max(contains, key=lambda p: len(p.parts), default=None)


def ahead_behind(path: Path) -> tuple[int, int] | None:
    """(ahead, behind) versus the branch's upstream, or None when there is no upstream."""
    upstream = _git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=path)
    if not upstream.strip():
        return None
    counts = _git(["rev-list", "--left-right", "--count", "@{u}...HEAD"], cwd=path).split()
    if len(counts) != 2:
        return None
    behind, ahead = int(counts[0]), int(counts[1])
    return ahead, behind


def hooks_path_finding(path: Path, main_root: Path) -> str | None:
    """None if this worktree's `core.hooksPath` is this clone's `.githooks`; the finding otherwise.

    Read per worktree rather than once: `extensions.worktreeConfig` (on for this clone)
    lets one worktree override the setting in its own config, silently shadowing the
    shared value, and `--show-origin` is what tells that apart from an inherited global.

    The relative `.githooks` is what the root `CLAUDE.md` asks for, and why: it resolves to
    each worktree's own copy. An absolute path naming this clone's `.githooks` -- its own or
    the main checkout's -- is accepted rather than reported, because the desktop app writes
    that form into the worktrees it creates, so the finding came back at the next close
    hours after a maintenance pass had cleared nine of them (#161). The hook runs either
    way; only a branch that changed the hook would notice which copy ran. A finding nobody
    can fix for good is one sessions learn to skip.

    An absolute path to any *other* `.githooks` is still a finding: that is the pinned-copy
    mistake the check exists to catch, and it survives this.
    """
    out = _git(["config", "--show-origin", "--get", "core.hooksPath"], cwd=path).strip()
    origin, _, value = out.partition("\t")
    clone_own = (path / ".githooks", main_root / ".githooks")
    if value == ".githooks" or Path(value) in clone_own:
        return None
    shown = f"{value!r} (from {origin})" if value else "unset"
    remedy = "run `git config core.hooksPath .githooks`"
    return f"core.hooksPath is {shown}, not `.githooks` -- {remedy}"


def against_trunk(path: Path, ref: str | None) -> tuple[str | None, bool]:
    """The column to print, and whether `main` already holds this worktree's HEAD.

    The retro audits every worktree for the ones that can be removed, and "is its branch
    already on `main`" is the half this script did not answer -- hand-run twice, with
    `git branch --merged origin/main` in one retro and forty `merge-base` calls in the next
    (#143). A clean worktree that is on main is a removal candidate, which is why this is
    printed and never gated: it is a thing to do, not a thing done wrong.

    `trunk.ahead` answers both halves in one call: zero means main holds this HEAD, and any
    other count is the distance to print. Why that count lives in `trunk.py` rather than
    here is its own docstring's to say (#143, #151).

    The ref is read as this checkout last fetched it, so a worktree whose branch merged
    since the last fetch still reads `ahead N of main`; `scripts/README.md`'s run order puts
    the refreshers first for that reason. `--remove` is the one run that cannot live with a
    stale answer and refreshes the ref itself.

    The column is None when git cannot say -- no trunk ref at all, or a ref this checkout
    does not hold -- and the fact is False, which is the safe reading: a worktree nobody
    can place is not one to delete.

    Both come from the one `trunk.ahead` call, and the second is what the rule actually
    needs. It used to be recovered by comparing the column against the sentence this
    function had just built, so three readers parsed display text for a decision while
    the count that answered it outright was thrown away here (#223 review).
    """
    if ref is None:
        return None, False
    ahead = trunk.ahead(path, "HEAD", ref)
    if ahead is None:
        return None, False
    shown = f"on {trunk.NAME}" if ahead == 0 else f"ahead {ahead} of {trunk.NAME}"
    return shown, ahead == 0


def idle_hours(path: Path) -> float | None:
    """Hours since git last wrote this worktree's git directory; None when it cannot say.

    The liveness guard `--remove` turns on: a session's worktree has to survive a cleaner
    that another session, or a scheduled run, is making at the time. Every git command run
    there moves one of these files -- a commit, a `status` that refreshes the index -- so
    the clock starts when the work stopped, not when the branch merged.

    The case it misses is a session that has only *read* its worktree for a day. What that
    costs is bounded by the rest of the rule: the tree is clean and `main` holds its HEAD,
    so `git worktree add` puts it back exactly as it was.
    """
    git_dir = _git(["rev-parse", "--absolute-git-dir"], cwd=path)
    if not git_dir:
        return None
    root = Path(git_dir.strip())
    written = [
        p.stat().st_mtime
        for p in (root / "HEAD", root / "index", root / "ORIG_HEAD", root / "logs" / "HEAD")
        if p.exists()
    ]
    return (time.time() - max(written)) / 3600 if written else None


def merged_here(entry: dict[str, str], merged_heads: dict[str, tuple[int, str]]) -> int:
    """The PR this worktree's HEAD was merged as, or 0 -- the squash path's whole proof.

    Both halves are load-bearing. The branch name says a PR of that name merged; the commit
    says this checkout is still at what merged rather than a commit somebody added after it,
    which `--remove` would delete beyond recovery.
    """
    number, oid = merged_heads.get(branch_of(entry), (0, ""))
    return number if oid and oid == entry.get("HEAD") else 0


def why_kept(
    entry: dict[str, str],
    state: State,
    *,
    is_main: bool,
    is_here: bool,
    path: Path,
) -> str | None:
    """None when this worktree may be deleted, else the one reason it may not.

    The rule in one place, so the listing and the removal cannot disagree about what a
    removal candidate is: git can account for everything in it, `main` holds its HEAD, it is
    neither the main checkout nor the worktree this run is in, and it has been idle long
    enough that no session is standing in it.

    "Account for everything" is the same test the husk sweep makes, asked the way a worktree
    git still lists can be asked: nothing staged, unstaged or untracked, and nothing ignored
    that a person wrote by hand. What is ignored otherwise goes with the directory, which is
    the repository's own declaration that it is output -- `git worktree remove --force`
    deletes it either way, and this is the sentence that makes that honest (#176 review).

    `main` is read from `state` as the caller resolved it, which `--remove` refreshes first:
    deciding this from a stale remote-tracking ref is how a cleaner deletes a branch that
    merged nowhere.

    `state.merged_as` is the second way work reaches `main`, which git cannot see at all;
    `merged_heads` says what that means and why nothing in git substitutes for it. A run
    that did not ask carries 0 there, and this rule is then exactly what it was.
    """
    if is_main:
        return "the main checkout"
    if is_here:
        return "the worktree this run is in"
    if state.complaint:
        return f"unreadable -- {state.complaint}"
    if any(state.counts):
        return "uncommitted or untracked work"
    if not state.on_trunk and not state.merged_as:
        return state.merged or f"git cannot place it against {trunk.NAME}"
    # Last of the tree's reasons rather than first: a worktree main does not hold yet is
    # kept for that, and naming the `.env` instead would bury the fact that matters.
    if state.hand_written:
        return f"holds `{state.hand_written[0]}`, which git cannot give back"
    idle = idle_hours(path)
    if idle is None:
        return "git cannot say when it was last touched"
    if idle < IDLE_HOURS:
        return f"touched {idle:.1f}h ago"
    return None


def remove(path: Path, branch: str, repo: Path) -> str | None:
    """Delete a worktree git lists, and the branch it held; git's complaint, or None.

    `--force` is not optional here, which is worth knowing before reading it as haste:
    `git worktree remove` refuses outright any worktree containing a submodule, and every
    worktree in this repository has the agent fleet at `.claude/agents` (ADR-0019), put
    there by `.githooks/post-checkout`. Without the flag this deletes nothing, ever --
    found by removing a throwaway worktree with it and watching git refuse.

    What `--force` costs is git's own refusal to delete a tree holding modifications, which
    was the second opinion on `why_kept`. So the reading is made again here, against the
    directory about to go, rather than trusted from the caller: it is the last moment
    anything can be known about it.

    The branch goes with the worktree -- one whose directory is gone and whose commits are
    on `main` is the same litter one level up. `-D` and not `-d`: `-d` proves merged-ness
    against the upstream, which GitHub deleted when the PR merged, so it would refuse for a
    reason that is not the question. `why_kept` has already proved it, by one of two facts:
    the fetched trunk ref holds the HEAD, or a merged PR does -- and for the second, that the
    HEAD is still the commit that merged rather than one added after it, which is what makes
    a squash-merged branch as spent as a merge-committed one (#216 review, #219).
    """
    complaint, counts, hand_written = read_status(path)
    if complaint:
        return complaint
    if any(counts) or hand_written:
        return "it holds work now that it did not hold when it was checked"
    result = git_cmd.run(
        "--no-optional-locks", "worktree", "remove", "--force", str(path),
        cwd=repo, text=True, encoding="utf-8",
    )
    if result.returncode != 0:
        refusal = result.stderr.strip().splitlines()
        return refusal[0] if refusal else f"git exited {result.returncode}"
    if branch:
        _git(["branch", "-D", branch], cwd=repo)
    _git(["worktree", "prune"], cwd=repo)
    return None


def husks(main_root: Path, listed: set[Path]) -> list[Path]:
    """Directories under the app's worktree directory that git no longer lists.

    `git worktree prune` cannot find these. It reconciles git's registry with the
    filesystem, and by the time one of these appears the registry is already consistent:
    the directory outlived its entry because Windows held a file open inside it while the
    removal ran -- a Vite cache under `web/.vite`, seen 2026-09-15. Only a filesystem sweep
    sees them, and only `unreconstructable` says whether one may go.

    Scoped to `.claude/worktrees/`, the directory the desktop app owns and keeps nothing
    else in. Not because a worktree elsewhere is sacred -- a *listed* one is removed
    wherever it sits, `C:\\wt\\…` included -- but because a directory git does not list is
    only recognisable as the corpse of a worktree where nothing else is ever put.
    """
    root = main_root / APP_WORKTREES
    if not root.is_dir():
        return []
    return [d for d in sorted(root.iterdir()) if d.is_dir() and d.resolve() not in listed]


def submodule_paths(main_root: Path) -> tuple[str, ...]:
    """The paths the superproject records as submodules -- `.claude/agents` here (ADR-0019)."""
    staged = _git(["ls-files", "--stage"], cwd=main_root)
    return tuple(
        line.split("\t", 1)[1] for line in staged.splitlines() if line.startswith("160000")
    )


def ignored_paths(main_root: Path, relatives: list[str]) -> set[str]:
    """Which of `relatives` the repository's own ignore rules cover, asked in one process.

    Asked as if the husk were the repository root, which is the only reading that means
    anything: the husk itself sits under a path `.git/info/exclude` covers wholesale, so
    asking about it where it actually is would call every file in it ignored.
    """
    asked = ["check-ignore", "--no-index", "--stdin"]
    return {line.strip() for line in _git_fed(asked, relatives, cwd=main_root) if line.strip()}


def unreconstructable(husk: Path, main_root: Path, submodules: tuple[str, ...]) -> list[str]:
    """What deleting this husk would lose: the paths git neither ignores nor already holds.

    The one test the sweep rests on, and the same one a person runs by hand before deleting
    a leftover directory. A path is safe when the repository's own ignore rules cover it --
    build output, `node_modules/`, a cache -- or when git holds a blob with its exact
    contents, which is what makes a checked-out copy of a committed file safe to delete
    however stale it is. A `.env` is safe under neither, whatever the ignore rules say.
    Anything else is work nobody committed, and the husk stays until a person has looked.

    A submodule checkout is reconstructable by definition -- `git submodule update` puts it
    back from its own remote -- and its blobs are in its own object database, not this one,
    so without this every husk that still held `.claude/agents` was kept forever for a
    reason that was not true (#176 review). Unless that checkout has changes of its own,
    which is the fleet-editing workflow the root `CLAUDE.md` describes, and then it stays.

    A stale `.git` *file* is the pointer the half-finished removal left behind, and counts
    as noise. A `.git` *directory* means this is a repository in its own right rather than a
    husk, and the whole thing is left alone.
    """
    if (husk / ".git").is_dir():
        return [".git/ -- a repository of its own, not a husk"]

    candidates: list[tuple[Path, str]] = []
    for walked, directories, files in os.walk(husk):
        here = Path(walked)
        below = {name: (here / name).relative_to(husk).as_posix() for name in directories}
        skip = ignored_paths(main_root, list(below.values()))
        for name, relative in below.items():
            if relative in submodules:
                if not _reusable_submodule(here / name):
                    return [f"{relative} -- a submodule checkout with changes of its own"]
                skip.add(relative)
        directories[:] = [name for name in directories if below[name] not in skip]
        for name in files:
            found = here / name
            if not found.is_symlink():
                candidates.append((found, found.relative_to(husk).as_posix()))

    lost = [relative for _, relative in candidates if Path(relative).name.startswith(HAND_WRITTEN)]
    unknown = [
        (found, relative)
        for found, relative in candidates
        if not Path(relative).name.startswith(HAND_WRITTEN) and relative != ".git"
    ]
    ignored = ignored_paths(main_root, [relative for _, relative in unknown])
    unknown = [(found, relative) for found, relative in unknown if relative not in ignored]

    digests = _git_fed(["hash-object", "--stdin-paths"], [str(found) for found, _ in unknown])
    if len(digests) != len(unknown):
        return lost + [relative for _, relative in unknown]
    held = _git_fed(["cat-file", "--batch-check"], digests, cwd=main_root)
    for (_, relative), answer in zip(unknown, held):
        if answer.strip().endswith("missing"):
            lost.append(relative)
    return lost


def _reusable_submodule(path: Path) -> bool:
    """Can `git submodule update` put this checkout back as it is -- nothing of its own in it?"""
    return _git_ok(["status", "--porcelain"], cwd=path) and not _git(
        ["status", "--porcelain"], cwd=path
    ).strip()


def branch_of(entry: dict[str, str]) -> str:
    """A short label for the worktree's checkout: the branch, or that it is detached/bare."""
    if "bare" in entry:
        return "(bare)"
    if "detached" in entry:
        return "(detached)"
    return entry.get("branch", "").removeprefix("refs/heads/") or "(unknown)"


def describe(entry: dict[str, str], is_main: bool, state: State) -> tuple[str, bool]:
    """One report line for a worktree, and whether it counts against the run.

    Uncommitted work counts, which is the state this exists to catch. So does a worktree git
    refuses to read: the columns after it -- clean, upstream, on main -- would every one be
    an empty answer dressed as a finding of fact (#172).
    """
    path = Path(entry["worktree"])
    name = f"{path.name} (main)" if is_main else path.name
    branch = branch_of(entry)
    if "bare" in entry:
        return f"{name}  {branch}  clean", False
    if state.complaint:
        return f"{name}  {branch}  UNREADABLE  [{state.complaint}]", True

    staged, unstaged, untracked = state.counts
    dirty = bool(staged or unstaged or untracked)
    if dirty:
        parts = []
        if staged:
            parts.append(f"{staged} staged")
        if unstaged:
            parts.append(f"{unstaged} unstaged")
        if untracked:
            parts.append(f"{untracked} untracked")
        shown = f"DIRTY ({', '.join(parts)})"
    else:
        shown = "clean"

    drift = ahead_behind(path)
    if drift is None:
        where = "no upstream"
    else:
        ahead, behind = drift
        where = "pushed" if not ahead and not behind else f"ahead {ahead}, behind {behind}"

    tail = f"  [{state.merged}]" if state.merged else ""
    if state.merged_as:
        tail = f"  [{state.merged}, squash-merged as #{state.merged_as}]"
    return f"{name}  {branch}  {shown}  [{where}]{tail}", dirty


def merged_heads(merged: list[dict], trunk_name: str = trunk.NAME) -> dict[str, tuple[int, str]]:
    """Branch name -> the PR it headed and the commit that was merged, for merges into trunk.

    The one fact git does not hold. A squash-merged PR's branch has no commit on `main` and
    no patch that matches one, so this mapping is the only evidence its work shipped (#197).

    **The commit is half the answer, not decoration.** "This branch was a merged PR's head"
    is not "this branch holds only merged work": a commit made after the merge sits on the
    same branch, and taking the name as proof deletes it with `--force` and `branch -D`,
    where no ref and no reflog has it. `why_kept` compares the worktree's HEAD against this,
    and a branch that has moved since is kept -- found by reproducing the loss (#216 review).

    Merges into anything but trunk are skipped for the reason `check_prs.py` checks the same
    thing: a PR merged into a live base has not reached `main`, so its branch is not spent.
    A branch reused by two PRs takes the highest-numbered; that is opening order rather than
    merge order, and only the number printed can be wrong, never the decision.
    """
    heads: dict[str, tuple[int, str]] = {}
    for pr in merged:
        head, number, oid = pr.get("headRefName"), pr.get("number"), pr.get("headRefOid")
        if head and number and oid and pr.get("baseRefName") == trunk_name:
            if number > heads.get(head, (0, ""))[0]:
                heads[head] = (number, oid)
    return heads


def sweep_one(
    entry: dict[str, str],
    state: State,
    *,
    is_main: bool,
    is_here: bool,
    repo: Path,
) -> int:
    """Delete this worktree if it may go, say why it stayed if it may not; 1 when it refused.

    A line either way -- a cleaner that deletes silently is one nobody can check, and the
    reason something stayed is what a reader came for. A removal that was decided on and
    then failed is counted, because it is the session's to look at: the directory is still
    there next run.
    """
    path = Path(entry["worktree"])
    kept = why_kept(entry, state, is_main=is_main, is_here=is_here, path=path)
    if kept:
        print(f"worktree: kept {path.name} — {kept}")
        return 0
    branch = entry.get("branch", "").removeprefix("refs/heads/")
    complaint = remove(path, branch, repo)
    if complaint:
        print(f"worktree: could not remove {path.name} — {complaint}")
        return 1
    # Which fact carried it, when `main` holding the HEAD was not the one. The listing says
    # the same thing in its own column, from the same reading -- this is the removal's half
    # of that, not a second derivation of it.
    how = f", squash-merged as #{state.merged_as}" if state.merged_as else ""
    print(f"worktree: removed {path.name} ({branch or 'detached'}{how})")
    return 0


def sweep_husks(main_root: Path, listed: set[Path], submodules: tuple[str, ...]) -> None:
    """Delete the leftover directories git no longer lists, and report the ones that stay.

    Printed, never gated. A husk that will not delete is an empty directory a live process
    holds open -- Windows answers `Device or resource busy` for the working directory of a
    process that outlived its worktree -- and nothing the session running this can do will
    change that. The repository's line is to gate on what the session can fix and print what
    it cannot (#176 review); this is the second kind.
    """
    for husk in husks(main_root, listed):
        lost = unreconstructable(husk, main_root, submodules)
        if lost:
            more = f", and {len(lost) - 3} more" if len(lost) > 3 else ""
            names = ", ".join(lost[:3])
            print(f"worktree: kept husk {husk.name} — git does not hold {names}{more}")
            continue
        try:
            shutil.rmtree(husk)
        except OSError as refused:
            print(f"worktree: could not delete husk {husk.name} — {refused.strerror or refused}")
        else:
            print(f"worktree: deleted husk {husk.name}")


def merged_prs(*, merged: Path | None, fetch: bool, remove: bool, gh: str | None) -> list[dict]:
    """The merged-PR list, when this run was given one and can read it; else empty.

    Three things this does not do, each of them once done, and all three decided here so a
    test can reach them. It does not fetch unless asked: a bare run is pure git and offline,
    and the closing step runs it that way. It does not fetch unless `--remove` is going to
    use the answer, which `--fetch` alone used to make it do. And it does not end the run
    when gh will not answer -- `gh_json.load` resolves to `raise SystemExit`, so an
    expired token or no network killed a git-only listing that had nothing to do with
    GitHub. The sweep keeps what it cannot prove reclaimable, which is what it does on a
    bare run too.
    """
    if not remove or (merged is None and not fetch):
        return []
    answer = gh_json.load_or_none(merged, gh, gh_json.MERGED_ARGS)
    if answer is None:
        print("worktree: gh would not list merged PRs; squash-merged worktrees are kept")
    return answer or []


def main() -> int:
    """Parse arguments, report every worktree, and fail by the rule `scripts/README.md` fixes."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--unattended",
        action="store_true",
        help="no session is behind this run: do not fail on another tree's uncommitted work",
    )
    parser.add_argument(
        "--current",
        action="store_true",
        help="gate the exit code on this worktree alone (still lists all)",
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="delete the worktrees and husks git can reconstruct in full (fetches first)",
    )
    gh_json.add_source_arguments(parser, "merged")
    args = parser.parse_args()

    here = Path.cwd().resolve()
    entries = worktrees(here)
    if not entries:
        return report.abort("worktree", "no worktrees found — is this a git repository?")

    # git lists the main worktree first -- the same guarantee `describe`'s `is_main` reads.
    # `hooks_path_finding` needs it to tell this clone's `.githooks` from a pinned copy.
    main_root = Path(entries[0]["worktree"]).resolve()
    here_wt = containing(entries, here)
    if args.current and here_wt is None:
        return report.abort(
            "worktree", f"{here} is in no listed worktree — cannot gate on 'this worktree'"
        )

    # `--remove` decides from the trunk ref, so it refreshes the one thing it decides from.
    # Everything else here reads the ref as it finds it; `scripts/README.md`'s run order is
    # what keeps that honest for the listing, and deleting on a stale ref is not a thing an
    # order can make safe.
    if args.remove:
        trunk.refresh(main_root)
    trunk_ref = trunk.ref(here)
    heads = merged_heads(
        merged_prs(merged=args.merged, fetch=args.fetch, remove=args.remove, gh=args.gh)
    )
    submodules = submodule_paths(main_root) if args.remove else ()

    failing = 0
    unowned_dirt = 0
    refused = 0
    listed: set[Path] = set()
    for index, entry in enumerate(entries):
        wt_path = Path(entry["worktree"]).resolve()
        listed.add(wt_path)
        bare = "bare" in entry
        state = (
            State(None, (0, 0, 0), (), None)
            if bare
            else read_state(wt_path, trunk_ref, merged_here(entry, heads))
        )
        line, counts_against = describe(entry, is_main=index == 0, state=state)
        scoped = (not args.current) or wt_path == here_wt
        marker = " <- here" if wt_path == here_wt else ""
        print(f"worktree: {line}{marker}")
        if counts_against and scoped:
            # `--unattended` demotes another tree's uncommitted work, never git refusing to
            # *read* one: the first is the normal state of a machine running several sessions
            # and no business of this run, the second means the sweep is blind there and that
            # worktree will never be swept at all (#199, `pr-tech-review`).
            if args.unattended and state.complaint is None:
                unowned_dirt += 1
            else:
                failing += 1
        if scoped and not bare and state.complaint is None:
            finding = hooks_path_finding(wt_path, main_root)
            if finding:
                print(f"worktree:   {finding}")
        if args.remove:
            refused += sweep_one(
                entry,
                state,
                is_main=index == 0,
                is_here=wt_path == here_wt,
                repo=main_root,
            )
    if args.remove:
        sweep_husks(main_root, listed, submodules)

    # Every line prints. Returning on the first hid a failed removal behind any worktree that
    # happened to be dirty, which is the one outcome of a `--remove` run nobody may miss.
    gate: list[str] = []
    notices: list[str] = []
    if failing:
        where = "this worktree" if args.current else f"{failing} of {len(entries)} worktree(s)"
        if not args.unattended:
            why = "uncommitted work, or git cannot read it"
        else:
            # Dirt is a notice under `--unattended`, so this line can only be the other one.
            why = "git cannot read it" if failing == 1 else "git cannot read them"
        gate.append(f"{where} not clean — {why}")
    if unowned_dirt:
        notices.append(
            f"{unowned_dirt} of {len(entries)} worktree(s) hold uncommitted work — not gated "
            "on, this run owns none of them"
        )
    if refused:
        gate.append(f"{refused} decided removal(s) failed — still there next run")
    scope = "this worktree" if args.current else f"{len(entries)} worktree(s)"
    # `failed=None`: the detail is the listing above, so each gate line is already the count
    # a check would put under its findings (#177). The not-gated lines -- a `core.hooksPath`
    # finding, a leftover that would not delete -- stay in that listing rather than becoming
    # `verdict`'s `notices`, which is what #177 proposed: each belongs to the worktree's row,
    # and hoisting them to the tail would break the order a reader scans by.
    return report.verdict(
        "worktree",
        gate,
        failed=None,
        notices=notices,
        consistent=(
            # Not "every removal was carried out": a husk a live process holds open prints
            # `could not delete husk` right above this line and is deliberately not gated
            # (`scripts/README.md`), so the narrower claim is the only true one.
            f"{len(entries)} worktree(s) swept; no worktree removal was refused"
            if args.unattended
            else f"no uncommitted work in {scope} (unpushed commits are fine)"
        ),
    )


if __name__ == "__main__":
    sys.exit(main())
