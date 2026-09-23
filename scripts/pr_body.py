"""What a pull request's body declares about other work: what it must merge after, and what
is blocking it -- and, for a cross-repository dependency, what gh says became of it.

Shared by `check_prs.py`, which fails a ready PR that still names an unmerged dependency, and
`close_report.py`, which reports the same dependency on a draft as the ordinary state of a
stack. Both questions read one grammar out of a body written for a person, and the second
script began by copying the first's -- twelve lines of reasoning and all -- which is where
the two would have drifted (PR #293, found by the architecture and parsimony reviews from
different directions).

Not a script -- it answers nothing and exits nowhere.
"""

from __future__ import annotations

import re

import gh_json
import reviews

#: `merge after #12`, and `merge after Atomtomate/agents#11` for a PR in another
#: repository. The fleet split (ADR-0019) makes the second form ordinary rather than
#: exotic: a definition fix is a PR in the fleet repo plus the pointer bump here, and the
#: bump must not merge first. Matching only the bare form let that dependency through in
#: silence (#190). Emphasis between the phrase and the reference is skipped, since a body
#: writes the directive to be read -- `merge after **Atomtomate/agents#11**` is the same
#: instruction and used to match nothing at all.
#:
#: Deliberately not told apart from the same phrase quoted in prose: a body discussing the
#: directive raises the finding as though it carried one. That is a false red the author
#: clears by rewriting the sentence, and it is the side to err on -- the alternative is
#: anchoring to the start of a line, which would miss "this must merge after #55" written
#: mid-sentence, and missing a real dependency is the bug this exists to prevent.
MERGE_AFTER = re.compile(r"merge after[\s*_`]+([\w.-]+/[\w.-]+)?#(\d+)", re.IGNORECASE)
#: What a draft states when it is finished and something outside it stops it going ready:
#: `Blocked: no CI while Actions is stopped (#282)`. The one fact about a PR that nothing can
#: derive -- PR #280 said it in a paragraph instead, and sat in draft across four closes with
#: every check calling it work in progress.
BLOCKED = reviews.label("blocked")


def merge_after(body: str) -> tuple[set[int], list[str]]:
    """What a body says to merge after: this repository's PR numbers, and other repositories'.

    A bare `#N` means this repository, and so does `Atomtomate/constellate#N` spelled
    out; anything else is another repository, returned as written because that is all a
    reader of the body alone can honestly do with it.
    """
    here: set[int] = set()
    elsewhere: list[str] = []
    for repo, number in MERGE_AFTER.findall(body):
        if not repo or repo.casefold() == gh_json.REPO.casefold():
            here.add(int(number))
        elif f"{repo}#{number}" not in elsewhere:
            elsewhere.append(f"{repo}#{number}")
    return here, elsewhere


def blocked_reason(body: str) -> str | None:
    """The reason a body gives for a PR that cannot go ready, or None when it gives none.

    Read at the start of any line, so the statement may sit under a heading of the body's
    choosing; the first one wins.
    """
    for line in body.splitlines():
        match = BLOCKED.match(line)
        if match:
            return match.group(1).strip()
    return None


def cross_repo_states(prs: list[dict], gh: str | None) -> dict[str, str | None]:
    """What ``gh`` says about every ``owner/repo#N`` the given PRs are waiting on.

    One call per distinct reference. The rule is the same for a draft as for a stack -- a PR
    waiting on one in another repository stays a draft until that merges -- and a reader that
    will not ask is a reader that asks the owner to remember, which is what let PR #188's
    dependency through unnamed (#190).

    A reference gh would not answer for maps to ``None`` rather than being left out: absent
    means nobody asked, ``None`` means the asking failed, and the caller says which, because
    a token that has lost access to the other repository otherwise reverts to silence without
    saying so. Mapping it also stops the failure being retried once per PR that names it.

    Which PRs are worth asking about is the caller's: `check_prs.py` asks only about the ones
    claiming to be ready, `close_report.py` about every draft, since a dependency that has
    merged is a draft nobody is waiting on any more.
    """
    states: dict[str, str | None] = {}
    for pr in prs:
        for reference in merge_after(pr.get("body") or "")[1]:
            if reference in states:
                continue
            repo, _, number = reference.partition("#")
            states[reference] = gh_json.pr_state(gh, repo, number)
    return states
