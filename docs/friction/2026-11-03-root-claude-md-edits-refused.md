# A lane cannot be assumed able to edit the root `CLAUDE.md`
**Agent:** the session on PR #27, briefed by the coordinator
**Summary:** Two root `CLAUDE.md` edits an owner's answer had asked for were refused as self-modification, late in the task, so the PR shipped without them and #31 now waits on the owner.
**Retro:** Applied 2026-11-04 — a root `CLAUDE.md` gotcha says the refusal can happen and what a brief says about it; whether a `CLAUDE.md` edit is on the list of what waits for the owner is in the retro handoff's Needs a decision.

**What you were doing.** M1's record step, PR #27, under the coordinator's brief: writing the
owner's answers of 2026-10-19 and 2026-11-03 into the files that own them, the root `CLAUDE.md`
among them. The step was the third commit.

**What happened.** The harness's permission check refused two edits with "Reason:
[Self-Modification]": the working agreement's merge rule and protection sentence, and the fleet
gotcha's pointer sentence. A third edit to the same file, dropping the banner, went through in the
same batch. Nothing says beforehand which will pass. The owner's own answers named these edits, and
the session had verified them at the source, but the check does not read that. The session did not
retry another way or hand the edit to another session, since a refusal is the owner's to lift.

**What it cost.** The root still states the old rule on three points, and an issue and a section of
the PR body now carry text that should have been a commit. The owner has been asked for a word they
already gave. On 2026-10-06 this same session stopped on an ask about one root sentence, and it sat
five days (`docs/digests/2026-10-11.md`, class 1).

**What would remove it.** A brief that asks a lane for a root edit should expect the refusal: keep
those edits to one commit at the end, and say in the brief who applies them if refused. The durable
fix is the owner's: a permission rule for the file, or a root edit made in a session the owner is
in.
