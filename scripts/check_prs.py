"""Is every open PR in the state its readiness claims?

The rule is the root ``CLAUDE.md``'s working agreement (since 2026-09-14, after PR #119 merged
before its four-reviewer pass had run): a PR opens as a draft and is marked ready only when it
is ready to merge -- the pass run and folded, its reports committed -- and a PR that stacks on
another stays a draft until its base has merged. Ready is the one signal the owner merges on,
and GitHub cannot enforce the rule on a private repository on the free plan, so this script is
the check, run at the closing step. It reports, never fixes. It reads one repository
(``gh_json.REPO``) and asks about another only when a body names one it must merge after: a
stacked PR in the fleet repo is still re-pointed by hand, as the rule says.

For every open PR that is **not** a draft:

- its body must carry a "Review pass" section that is neither empty nor a placeholder ("to be
  filled", "pending"), and its diff must carry the four reviewers' reports under
  ``docs/reviews/<branch>/`` -- the ledger the overlay names as the pass's record, and evidence
  a sentence cannot fake. The rule's one exception is a record-only PR whose section says the
  pass was not run and why ("Not run: ..."); that statement stands in for the reports;
- its base must be ``main``, and no "merge after" in its body may name a PR still open. A bare
  ``#N`` is this repository's, answered from the list already loaded; ``owner/repo#N`` is
  another repository's, and under ``--fetch`` gh is asked about it directly -- the fleet split
  makes that the ordinary shape for agent work, and the rule is the same either way (#190).

Two things it prints and does not fail on. A ready PR standing on the exemption above, so the
one case the rule spells out is visibly considered rather than silently allowed (#126). And a
cross-repo dependency left unresolved -- nobody asked, running from a saved snapshot, or gh
refused to answer -- named as which of the two, since the one thing a gate may not do with a
rule it could not check is pass.
Which open PRs are heading for the same file is `open_work.py`'s, not this script's -- that
is a listing about work in flight, and this is a gate.

For every **merged** PR whose base was not ``main``, git is asked whether ``main`` holds the
commit ``gh`` says merged it. A PR merged into a live base -- the shape PR #80 took, its work
sitting on ``claude/maintain-2026-09-08`` for days while every check read the record and
passed -- reaches ``main`` only once that base does, and until then it has not shipped,
whatever its state says.

Input is ``gh pr list`` JSON, fetched with ``--fetch`` or read from saved files -- ``--prs``
for the open PRs (``gh_json.PRS_ARGS``), ``--merged`` for the merged ones
(``gh_json.MERGED_ARGS``) -- so the checks can be tested on a snapshot. The merged check
runs only when its list was given or fetched, and is the one part a snapshot cannot answer
alone: whether a commit is on ``main`` is git's to say.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import git_cmd

import gh_json
import pr_body
import report
import reviews
import trunk
#: What a section says while the pass is still owed. Tested at the start of every line, after
#: leading emphasis marks and dashes, and against the heading's own tail
#: (`## Review pass -- to be filled`). The committed reports are the evidence that counts;
#: this only names the honest-but-unfinished shapes so the finding can say which it saw.
PLACEHOLDER = re.compile(
    r"^[\s_*—–:-]*(to be filled|not yet run|not run yet|pending|tbd|todo)\b", re.IGNORECASE
)
TRUNK = trunk.NAME


def outrun(root: Path, pr: dict, fetch: bool = True) -> list[str] | None:
    """The commits a PR's head has made since its reports, or None when git cannot see the head.

    Ready is a property of the commit the pass saw (root ``CLAUDE.md``): PR #225 was marked
    ready with its pass folded, `main` was merged into it, the conflict resolution changed a
    published contract shape, and the flag stayed up because every gate reads a state reached
    rather than a state kept. `reviews.pass_state` reads where the pass stands from the commit
    that last touched the reports; the head is fetched first so the answer is GitHub's, not a
    stale local copy's.
    """
    head = pr.get("headRefName") or ""
    if not head:
        return None
    if fetch:
        git_cmd.run("fetch", "--quiet", "origin", head, cwd=root)
    ref = f"origin/{head}"
    if not git_cmd.first(root, "rev-parse", "--verify", "--quiet", ref):
        return None
    state, commits = reviews.pass_state(root, head, ref, trunk.ref(root))
    return commits if state == "stale" else []


def cross_repo_states(prs: list[dict], gh: str | None) -> dict[str, str | None]:
    """`pr_body.cross_repo_states` for the PRs this gate judges, which is the ones not drafts.

    A draft is already blocked, so what its cross-repo dependency became is nothing this gate
    has to resolve -- and asking would cost a call per reference for an answer it would not
    use. That filter is this script's rule; the asking is `pr_body.py`'s.
    """
    return pr_body.cross_repo_states([pr for pr in prs if not pr.get("isDraft")], gh)


def notices(prs: list[dict], states: dict[str, str | None] | None = None) -> list[str]:
    """What a ready PR carries that this gate prints rather than fails on.

    Cases of one kind: something the rule allows, or could not read, which the reader must
    still see. The pass-not-run exemption was taken in silence, which made the one case the
    rule spells out the one case its check could not be seen to have considered (#126). A
    dependency on a PR in another repository is a notice only while unresolved, and says
    which kind of unresolved: nobody asked (no ``--fetch``), or gh refused to answer, which
    is the one a reader must act on. A resolved dependency is a finding or nothing. Drafts
    raise none of it: a draft is already blocked.
    """
    printed = []
    for pr in prs:
        if pr.get("isDraft"):
            continue
        label = f"#{pr['number']} ({pr.get('title', '')})"
        if reason := reviews.not_run_reason(pr):
            printed.append(
                f"{label} is ready on the pass-not-run exemption: {report.clip(reason)} — no "
                "reports required, and the merge is yours"
            )
        elsewhere = pr_body.merge_after(pr.get("body") or "")[1]
        unasked = [ref for ref in elsewhere if ref not in (states or {})]
        refused = [ref for ref in elsewhere if ref in (states or {}) and not (states or {})[ref]]
        if unasked:
            printed.append(
                f"{label} is ready and says merge after {', '.join(unasked)}, which this run "
                "did not ask about (--fetch asks that repository) -- confirm it merged yourself"
            )
        if refused:
            printed.append(
                f"{label} is ready and says merge after {', '.join(refused)}, which gh would "
                "not answer for -- run `gh pr view` on it yourself to see why, since until "
                "then this gate is not checking that dependency at all"
            )
    return printed


def findings(
    prs: list[dict], states: dict[str, str | None] | None = None, outrun_by=None
) -> list[str]:
    """One line per PR whose readiness disagrees with the rule.

    ``states`` is `cross_repo_states`' answer, empty when this run did not fetch: a
    dependency in another repository can only be judged by what gh said about it, and one
    nobody asked about is `notices`' to raise rather than this function's to guess at.
    ``outrun_by`` is `outrun` with the root bound, or None from a snapshot, where git has no
    head to read; it runs only for a ready PR whose reports are all there.
    """
    open_numbers = {pr["number"] for pr in prs}
    found = []
    for pr in prs:
        if pr.get("isDraft"):
            continue
        label = f"#{pr['number']} ({pr.get('title', '')})"
        section = reviews.review_pass_section(pr.get("body") or "")
        if section is None:
            found.append(f"{label} is ready for review but its body has no Review pass section")
        elif not section:
            found.append(f"{label} is ready for review but its Review pass section is empty")
        elif any(PLACEHOLDER.match(line) for line in section.splitlines()):
            found.append(
                f"{label} is ready for review but its Review pass section is a placeholder: "
                f"{section.splitlines()[0][:60]!r}"
            )
        elif not reviews.not_run_reason(pr):
            missing = reviews.missing_reports(pr)
            if missing:
                found.append(
                    f"{label} is ready for review but its diff commits no report under "
                    f"docs/reviews/<branch>/ for: {', '.join(missing)}"
                )
            elif outrun_by is not None:
                later = outrun_by(pr)
                if later:
                    found.append(
                        f"{label} is ready for review but {len(later)} commit(s) since its "
                        f"reports change more than Markdown -- {'; '.join(later)} -- so the "
                        "pass has not seen the head: return it to draft until a second wave has"
                    )
        base = pr.get("baseRefName")
        if base and base != TRUNK:
            found.append(
                f"{label} is ready for review but based on `{base}`, not `{TRUNK}` -- a "
                "stacked PR stays a draft until its base merges"
            )
        here, elsewhere = pr_body.merge_after(pr.get("body") or "")
        for depends_on in sorted(here):
            if depends_on in open_numbers:
                found.append(
                    f"{label} is ready for review but says merge after #{depends_on}, "
                    "which is still open"
                )
        for reference in elsewhere:
            state = (states or {}).get(reference)
            if state and state != "MERGED":
                found.append(
                    f"{label} is ready for review but says merge after {reference}, which gh "
                    f"says is {state.lower()}"
                )
    return found


def merge_landed(root: Path, oid: str) -> bool | None:
    """Whether main holds the commit that merged a PR; None when git here has no such commit.

    ``trunk.ref`` puts ``origin/main`` before ``main`` and says why, and ``trunk.ahead`` is
    the shared answer to "does main hold this" (#151): no commits of its own means main
    holds it, and a commit this checkout does not hold comes back None rather than as a
    wrong answer -- a merge commit on a base branch since deleted is what makes that
    distinction load-bearing here. A commit git holds through some other ref while
    ``origin/main`` is stale reads as False, which is why ``main()`` refreshes ``origin/main``
    under ``--fetch`` and the finding says so. Assumes the base reaches main by a merge
    commit, as this repository's merge button makes one; a base squash-merged into main
    would carry no commit of the PR's, and its finding would never clear.
    """
    main = trunk.ref(root)
    if main is None:
        return None
    ahead = trunk.ahead(root, oid, main)
    return None if ahead is None else ahead == 0


def merged_findings(merged: list[dict], landed) -> list[str]:
    """One line per merged PR whose work main does not hold.

    A PR merged into ``main`` is on it by definition and is not asked about. For one merged
    into any other branch, ``landed(oid)`` -- ``merge_landed`` at the closing step, a stand-in
    in tests -- says whether main holds its merge commit: True once the base itself merged,
    False while the work sits on a live base, None when git cannot see the commit at all.
    """
    found = []
    for pr in merged:
        base = pr.get("baseRefName")
        if base == TRUNK:
            continue
        label = f"#{pr['number']} ({pr.get('title', '')})"
        oid = (pr.get("mergeCommit") or {}).get("oid") or ""
        verdict = landed(oid) if oid else None
        if verdict is True:
            continue
        if verdict is False:
            found.append(
                f"{label} merged into `{base}`, not `{TRUNK}`, and its merge commit {oid[:7]} "
                f"is not on {TRUNK} as git here has it (--fetch refreshes origin/{TRUNK}): the "
                "work has not shipped"
            )
        else:
            found.append(
                f"{label} merged into `{base}`, not `{TRUNK}`, and git here does not know its "
                f"merge commit {oid[:7] or '(none)'}: fetch and run again, or the base is gone"
            )
    return found


def main() -> int:
    """Parse the options, load the PRs, print the findings, exit 1 on any."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    gh_json.add_source_arguments(parser, "prs", "merged")
    args = parser.parse_args()
    if args.prs is None and not args.fetch:
        parser.error("give --prs FILE or --fetch")

    prs = gh_json.load(args.prs, args.gh, gh_json.PRS_ARGS)
    root = Path(__file__).resolve().parent.parent
    if args.fetch:
        trunk.refresh(root)  # what --fetch means here includes the ref this check reads
    states = cross_repo_states(prs, args.gh) if args.fetch else {}
    found = findings(prs, states, (lambda pr: outrun(root, pr)) if args.fetch else None)
    printed = notices(prs, states)
    drafts = sum(1 for pr in prs if pr.get("isDraft"))
    # "here" survives the fetch: a cross-repo dependency is either a finding above or a
    # notice above, and neither is something this line may fold into its vouch.
    vouched = (
        f"{len(prs)} open PR(s), {drafts} draft(s); every ready PR has its review pass "
        "folded and depends on nothing unmerged here"
    )
    if args.fetch:
        vouched += ", and no ready PR has outrun its reports"
    if args.merged is not None or args.fetch:
        merged = gh_json.load(args.merged, args.gh, gh_json.MERGED_ARGS)
        found += merged_findings(merged, lambda oid: merge_landed(root, oid))
        vouched += f"; each of {len(merged)} merged PR(s) is on {TRUNK}"
    return report.verdict(
        "prs", found, failed=f"{len(found)} finding(s)", consistent=vouched, notices=printed
    )


if __name__ == "__main__":
    sys.exit(main())
