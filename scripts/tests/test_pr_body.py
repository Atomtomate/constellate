"""Tests for `scripts/pr_body.py` and the label grammar under it (`reviews.label`).

Stdlib-only (`unittest`), matching `scripts/README.md`'s rule; run with
`python -m unittest discover scripts/tests`.

A PR body is written for a person, so the same statement arrives emphasised, dashed or
plain, and the grammar that reads it has to take all three: hand-written twice, it already
had -- `reviews.NOT_RUN` read `**Not run:** a record PR` as a reason of `** a record PR`
and `**Not run** - a record PR` as no statement at all, which is the hole these tests pin
shut for every label at once.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pr_body  # noqa: E402
import reviews  # noqa: E402


class LabelGrammar(unittest.TestCase):
    """One factory, so `Not run` and `Blocked` cannot read the same line differently."""

    def test_every_emphasis_gives_the_same_reason(self):
        for line in ("Blocked: no CI (#282)", "**Blocked:** no CI (#282)",
                     "**Blocked** — no CI (#282)", "*Blocked* - no CI (#282)",
                     "  Blocked : no CI (#282)"):
            with self.subTest(line=line):
                match = pr_body.BLOCKED.match(line)
                self.assertIsNotNone(match, line)
                self.assertEqual(match.group(1), "no CI (#282)")

    def test_the_same_holds_for_the_pass_not_run_exemption(self):
        for line in ("Not run: a record-only PR.", "**Not run:** a record-only PR.",
                     "**Not run** — a record-only PR."):
            with self.subTest(line=line):
                match = reviews.NOT_RUN.match(line)
                self.assertIsNotNone(match, line)
                self.assertEqual(match.group(1), "a record-only PR.")

    def test_the_word_mid_sentence_is_not_a_statement(self):
        self.assertIsNone(pr_body.BLOCKED.match("This was blocked: until yesterday."))
        self.assertIsNone(reviews.NOT_RUN.match("The pass was not run: nobody asked."))

    def test_a_label_with_no_reason_is_no_statement(self):
        self.assertIsNone(pr_body.BLOCKED.match("Blocked:"))


class BlockedReason(unittest.TestCase):
    """The `Blocked:` line a finished draft states, which nothing else can derive."""

    def test_reads_the_first_statement_in_the_body(self):
        body = "## Review pass\n\nAll four ran.\n\nBlocked: no CI while Actions is stopped\n"
        self.assertEqual(pr_body.blocked_reason(body), "no CI while Actions is stopped")

    def test_a_body_that_says_nothing_blocks_nothing(self):
        self.assertIsNone(pr_body.blocked_reason("Nothing blocked here.\n"))


class MergeAfter(unittest.TestCase):
    """What a body declares it must merge after, here and elsewhere."""

    def test_a_bare_number_is_this_repository(self):
        self.assertEqual(pr_body.merge_after("merge after #12"), ({12}, []))

    def test_this_repository_spelled_out_is_still_here(self):
        self.assertEqual(
            pr_body.merge_after("merge after Atomtomate/constellate#12"), ({12}, [])
        )

    def test_another_repository_comes_back_as_written_and_once(self):
        body = "merge after **Atomtomate/agents#11**, and again merge after Atomtomate/agents#11"
        self.assertEqual(pr_body.merge_after(body), (set(), ["Atomtomate/agents#11"]))


class CrossRepoStates(unittest.TestCase):
    """One question per distinct reference, asked only about the PRs the caller passed."""

    def test_asks_once_per_reference_and_keeps_what_it_is_told(self):
        asked = []

        def answer(_gh, repo, number):
            asked.append(f"{repo}#{number}")
            return "MERGED"

        original = pr_body.gh_json.pr_state
        pr_body.gh_json.pr_state = answer
        try:
            states = pr_body.cross_repo_states(
                [{"body": "merge after Atomtomate/agents#11"},
                 {"body": "merge after Atomtomate/agents#11"}], None
            )
        finally:
            pr_body.gh_json.pr_state = original
        self.assertEqual(states, {"Atomtomate/agents#11": "MERGED"})
        self.assertEqual(asked, ["Atomtomate/agents#11"])


if __name__ == "__main__":
    unittest.main()
