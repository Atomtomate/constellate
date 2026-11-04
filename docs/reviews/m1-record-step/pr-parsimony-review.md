Reviewed at da0e45399cfc

**Verdict:** About right. Each owner answer is quoted once, in the file that owns it, and every
other site points there. The weight is the quoting habit reaching the two files every agent loads
each session, and ADR-0004 repeating itself. 2 findings.

### 1. Owner asks are quoted into the always-loaded files, with the rule inside the quote
- **What** — The root `CLAUDE.md` swaps a six-line banner for six lines, four of them the banner
  ask quoted; the overlay repeats the root's two pointers, which its paragraph above already
  promises. The withheld bullet adds a nine-line quote whose "Ready means the gates are met"
  restates the draft-flag bullet above it, and the PR says the quote is also "in the handoff".
- **Why it recurs** — Yes: "quote the ask" is now the practice for every answer. The root's style
  for an owner's word is a date and a pointer (the owner, 2026-09-23; ADR-0003).
- **The smaller version** — Root: "Where the project stands is not restated here: `docs/07`'s done
  markers say what is built, `docs/08` what is open (the owner, 2026-11-03)." Overlay: drop those
  two sentences, keep the *not yet* rule. Withheld bullet: "The coordinator merges ready PRs, the
  owner reviews on `main` by revert (the owner, 2026-10-19; the handoff). Ready is the gates above;
  a trivial held question gets the recommended option after a stated wait." Likewise the
  protection sentence.
- **Net effect** — About 15 lines out of what every session reads (4 on the branch, 9 withheld).
  Prose is the only remedy: no check can tell a quote that carries a rule from one that records it.

### 2. ADR-0004 quotes one option twice and carries plan detail it calls movable
- **What** — `docs/adr/0004-sign-in-stored-sessions.md`: the Decision quotes the signed-cookie
  option ("One owner password in config, exchanged for a stateless signed HttpOnly session
  cookie") and Alternatives quotes it again. The Decision's third paragraph names `auth_session`,
  `RequireSession` and its hash-and-expiry shape, then says "its lanes may move it"; the plans it
  cites hold all of that, and an ADR cannot be edited when they do.
- **Why it recurs** — Yes: the first ADR of the M1 round sets the template, the ask quoted and then
  "what the plan adds", and the next ADR copies both.
- **The smaller version** — Decision: "'Same login' is the signed-cookie option under Alternatives,
  without its stateless signature." Delete the "What the M1 plan adds" paragraph; Context already
  cites the director's decisions 2 and 9. `docs/03`'s 401 row can say "see ADR-0004" instead of
  repeating that the challenge is the sign-in lane's, which "Not decided here" already says.
- **Net effect** — About 7 lines. The ADR holds only what the owner decided and what follows, so a
  lane renaming the table leaves no decision record wrong.
