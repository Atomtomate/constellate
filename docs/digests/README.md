# Digests

One file per `manager` run, `YYYY-MM-DD.md`: the record since the previous digest, compressed
and judged, with ranked recommendations the next retro answers first and the owner reads
first. What a digest reads and holds is `.claude/agents/manager.md`'s to say. A digest
supersedes the notes it names under `**Supersedes:**`; those stay as testimony.
`scripts/check_docs.py` holds a digest to its `**Covers:**`/`**Supersedes:**` header and to
`record.DIGEST_CAP` lines, and resolves every link in the record, so files are named in
backticks, never linked.
