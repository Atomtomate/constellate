"""The record's header contract: how a handoff and a friction note say what they are.

Both directories used to carry a hand-maintained table -- one row per entry, in a README
every closing branch had to edit. Two sessions editing the same table clobbered each
other's rows into merge conflicts every few sessions (#111), so the row moved into the
file it describes: a short header, directly under the title. This module is the one
parser for that header, and every reader of the record goes through it --
`record_index.py` prints it as a table, `check_docs.py` enforces it, `open_work.py` and
`failure_ledger.py` read it to say what is still open and what a retro must look at.

A handoff's header is its title line, then `**Summary:**` and `**State:**`. A friction
note's is its title, then `**Agent:**`, `**Summary:**` and `**Retro:**`. Both contracts,
including the `Open`/`Folded` and `Unprocessed`/`Applied`/`Declined`/`Resolved`/`Filed`
vocabularies, are fixed in `docs/handoffs/README.md` and `docs/friction/README.md`, one
directory's contract per README. Date is not part of either header -- the filename
(`YYYY-MM-DD-slug.md`) already carries it, and repeating it would be one more place for
the two to disagree.

Not a script: it prints nothing and checks nothing, so that four readers of one contract
cannot drift into four readings of it. Stdlib only, like everything here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

DATED_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})-.+\.md$")
TITLE = re.compile(r"^# .+$")
HEADER_LINE = re.compile(r"^\*\*(\w+):\*\*\s*(\S.*)$")

# The Retro vocabulary, stated in words in `docs/friction/README.md` and enforced by
# `check_docs.py`, so a new word is a one-file change. There is no `STATE_WORDS` beside it:
# a handoff's State is not enforced, and the two predicates below spell their own prefixes.
RETRO_WORDS = ("Unprocessed", "Applied", "Declined", "Resolved", "Filed")

#: A handoff is at most this many lines, for one dated on or after HANDOFF_CAP_FROM; the
#: earlier ones stand as written. `check_docs.py` enforces it. The median handoff ran 120 lines
#: on 2026-09-17 and the owner could not read the record at that volume; a table that will not
#: fit goes in a file the handoff names.
HANDOFF_CAP = 100
HANDOFF_CAP_FROM = "2026-09-18"

#: A digest is `YYYY-MM-DD.md` under `docs/digests/`, at most this many lines, with `**Covers:**`
#: and `**Supersedes:**` under its title (`.claude/agents/manager.md`, `docs/digests/README.md`).
#: `check_docs.py` enforces both: the one record whose value is compression is not the one
#: exempt from the guard on volume (PR #243 review).
DIGEST_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
DIGEST_CAP = 120


class HeaderError(ValueError):
    """A handoff or friction file's header does not match its directory's contract.

    Carries the offending file's name as `.path`, apart from the human-readable
    `.message`, so a caller with its own path formatting (`check_docs.py`'s `rel(root,
    path)`) does not have to parse a path back out of `str(exc)`.
    """

    def __init__(self, path: str, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path
        self.message = message


@dataclass(frozen=True)
class Handoff:
    """One handoff, as its filename and header say -- never as a README row says."""

    date: str
    filename: str
    summary: str
    state: str

    @property
    def is_open(self) -> bool:
        """Work not yet folded into the docs it changed."""
        return self.state.startswith("Open")

    @property
    def is_folded(self) -> bool:
        """Content and open items already folded elsewhere; nothing left to list."""
        return self.state.startswith("Folded")


@dataclass(frozen=True)
class Friction:
    """One friction note, as its filename and header say."""

    date: str
    filename: str
    agent: str
    summary: str
    retro: str

    @property
    def is_unprocessed(self) -> bool:
        """A note the retro has not yet given a verdict -- what `--open` keeps."""
        return self.retro.startswith("Unprocessed")


def _date(path: Path) -> str:
    """The entry's date, read from the filename the header contract leaves it to."""
    m = DATED_FILE.match(path.name)
    if not m:
        raise HeaderError(path.name, "filename is not YYYY-MM-DD-slug.md")
    return m.group(1)


def _header(path: Path, *keys: str) -> tuple[str, ...]:
    """Read the fixed `**Key:**` lines that follow the title, in order.

    Line 1 must be the title; line N+1 must be `**keys[N-1]:**`. A handoff and a friction
    note are the same shape with a different key list, so this is the one parser both use
    -- the dataclasses stay distinct, but there is exactly one place that reads a header.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or not TITLE.match(lines[0]):
        raise HeaderError(path.name, "line 1 is not '# <title>'")
    values = []
    for n, key in enumerate(keys, start=1):
        m = HEADER_LINE.match(lines[n]) if len(lines) > n else None
        if not m or m.group(1) != key:
            raise HeaderError(path.name, f"line {n + 1} is not '**{key}:** ...'")
        values.append(m.group(2))
    return tuple(values)


def parse_handoff(path: Path) -> Handoff:
    """Read a handoff's title, Summary and State from the three lines the contract fixes."""
    summary, state = _header(path, "Summary", "State")
    return Handoff(_date(path), path.name, summary, state)


def parse_friction(path: Path) -> Friction:
    """Read a friction note's title, Agent, Summary and Retro from the header's four lines."""
    agent, summary, retro = _header(path, "Agent", "Summary", "Retro")
    return Friction(_date(path), path.name, agent, summary, retro)


@dataclass(frozen=True)
class Digest:
    """A digest's header: the range it covers and the notes it supersedes."""

    date: str
    name: str
    covers: str
    supersedes: str


def parse_digest(path: Path) -> Digest:
    """Read a digest's title, Covers and Supersedes from the three lines its contract fixes."""
    m = DIGEST_FILE.match(path.name)
    if not m:
        raise HeaderError(path.name, "filename is not YYYY-MM-DD.md")
    covers, supersedes = _header(path, "Covers", "Supersedes")
    return Digest(m.group(1), path.name, covers, supersedes)


def digest_entries(directory: Path) -> list[Path]:
    """Every digest in `directory`, oldest first; the README is not one."""
    return sorted(p for p in directory.glob("*.md") if DIGEST_FILE.match(p.name))


def entries(directory: Path) -> list[Path]:
    """Every dated file in `directory`, README excluded, oldest first.

    The one filename filter every consumer of this contract shares, so `check_docs.py` and
    `open_work.py` cannot drift into requiring a header from a file this module would
    never print, or skipping one it would.
    """
    return sorted(p for p in directory.glob("*.md") if DATED_FILE.match(p.name))


def _parse_all(directory: Path, parse) -> tuple[list, list[HeaderError]]:
    """Parse every entry in `directory`; a malformed one is collected, never raised here."""
    good: list = []
    bad: list[HeaderError] = []
    for path in entries(directory):
        try:
            good.append(parse(path))
        except HeaderError as exc:
            bad.append(exc)
    return good, bad


def handoffs(directory: Path, *, open_only: bool = False) -> list[Handoff]:
    """Every handoff in `directory`, parsed and sorted; raises on the first malformed one.

    For a listing that must keep going past a bad file, see `scan_handoffs`.
    """
    good, bad = _parse_all(directory, parse_handoff)
    if bad:
        raise bad[0]
    return [h for h in good if h.is_open] if open_only else good


def friction(directory: Path, *, open_only: bool = False) -> list[Friction]:
    """Every friction note in `directory`, parsed and sorted; raises on the first bad one."""
    good, bad = _parse_all(directory, parse_friction)
    if bad:
        raise bad[0]
    return [f for f in good if f.is_unprocessed] if open_only else good


def scan_handoffs(directory: Path) -> tuple[list[Handoff], list[HeaderError]]:
    """Every handoff that parses, and the errors for the ones that don't -- never raises.

    For `open_work.py`, which must keep listing the roadmap and the friction queue even
    when one handoff predates this contract or an agent forgot it.
    """
    return _parse_all(directory, parse_handoff)


def scan_friction(directory: Path) -> tuple[list[Friction], list[HeaderError]]:
    """Every friction note that parses, and the errors for the ones that don't."""
    return _parse_all(directory, parse_friction)
