Reviewed at 6e8c8a387ade

**Verdict:** Well placed; no findings. The code in this mostly-prose diff is 10 lines under
`scripts/`. Its one new dependency, `repo=gh_json.REPO` at `review_briefs.py:191`, takes the
repository's name from `scripts/gh_json.py:16`. That module owns every repository fact this
tooling sends to `gh`, and `review_briefs.py` already imported it (`:33`) and already used
`REPO` from it (`:218`). The diff adds no import anywhere. `scripts/` has no written layer
standard, so none binds beyond the standing constraints. `scripts/check_layering.py` does not
exist yet (the overlay says it arrives with the scaffold, PR #9), so the imports were read by
hand rather than measured. The Markdown is outside this axis, since a mixed diff is reviewed
as code.

**What carried it:** the definition's rule to follow a changed symbol into its defining file.
Opening `scripts/gh_json.py` and `review_briefs.py:218` showed that the new `gh_json.REPO`
reference adds no new crossing. It reuses a dependency the module already declared, and that
dependency is the one that owns the fact.
