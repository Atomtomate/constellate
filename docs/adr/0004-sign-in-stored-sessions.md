# ADR-0004 — Sign-in: one owner password, and stored sessions that can be revoked

- **Status:** Accepted
- **Date:** 2026-11-03
- **Accepted:** 2026-11-03, by the owner, over a stateless signed cookie and proxy-side auth

## Context

M1 is private and single user, and the owner signs in (`docs/07-roadmap.md`, M1). The read API has
to land already protected, so the scheme comes before it, and both the contract and the web
client's session handling take their shape from it. Until now nothing was settled, on purpose: the
scaffold put `unauthenticated` in the closed error set so the contract's enum would not move when
sign-in arrived, and named no credential and no challenge (`docs/03-architecture.md`, "One error
envelope"; issue #20). The stack ADR leaves the scheme undecided by name. The standing constraint
that a decision is written down before it is built on sends the answer here, ahead of the lane that
builds it (`docs/reviews/m1-plan/impl-director.md`, decisions 2 and 9).

## Decision

The owner, 2026-11-03, asked "How do you sign in (issue #20)? M1 is private, single user; the scheme
shapes the contract and the web client's session handling.", chose "Stored sessions, revocable":
"Same login, but sessions live in a table (one more migration, three repo functions) so a single
session can be revoked and listed."

"Same login" is the signed-cookie option's, under Alternatives, without its stateless signature.
Taken together:

**One owner password, in config, is exchanged for an HttpOnly session cookie. Each session is a row
in a table, so a single session can be revoked and the sessions can be listed. A request that needs
a session and has no live one gets a 401 in the error envelope, code `unauthenticated`.**

## Consequences

**What becomes easy.**

- One session can end without ending the others, and the owner can see which exist, once something
  exposes them (below). A stateless cookie can only revoke everything at once, by rotating its
  secret.
- The contract's error enum does not move, because `unauthenticated` is already in it.

**What becomes hard.**

- One more table, one more migration and three repo functions, so the sign-in lane now waits on
  `impl-database`. The stateless cookie would have kept it clear of the schema lanes.
- Every protected request reads the table. That is one indexed read, which costs nothing at one
  user's scale, but it does mean the API cannot authenticate a request without its database.
- Session rows have to leave the table once they expire. How they do is the sign-in lane's.

**What is expensive to reverse.** Nothing here. To a client the cookie is opaque, so moving to a
stateless cookie later would drop a table and whatever endpoints list and revoke sessions, and leave
the rest of the contract and the web client alone.

**Not decided here.** Whether M1 builds what lists and revokes sessions, as endpoints and a screen
or as a command: the plan's Lane 3 has only login, logout and `/me`, and until something exposes
them the table buys nothing, so the M1 plan's re-cut settles it (issue #20). How a client that is
not a browser, the later extension, presents a credential: every client consumes the contract on
equal terms, and `SameSite` decides whether it can use the cookie at all. And, because no option
distinguished them, the sign-in lane's to state in its plan: whether config holds the password or a
hash of it; the cookie's `SameSite`, `Secure` and `Path`; and whether a 401 carries a
`WWW-Authenticate` challenge.

## Alternatives considered

Both are the ask's own options, in its words. The owner gave no reason beyond the option taken.

- **Signed cookie, one password** — "One owner password in config, exchanged for a stateless signed
  HttpOnly session cookie; no table; revoke everything by rotating the secret; 401 in the envelope.
  The sibling's scheme, built here rather than copied." The ask's recommended option and the
  director's leaning, on the ground that "a single private user needs no per-session revocation,
  and it keeps Lane 3 off Lane 1" (`docs/reviews/m1-plan/impl-director.md`, decision 2). It lost to
  being able to revoke and list a single session.
- **Proxy-side auth, none in the API** — "The reverse proxy on the rig authenticates; the API trusts
  the proxy and has no sign-in of its own. Simplest API, but nothing protects it off the rig."
