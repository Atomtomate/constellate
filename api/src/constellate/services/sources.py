"""Source-adapter interface that ``services/`` calls and ``sources/`` satisfies.

The structural typing here enforces the one-ingestion-path rule
(``docs/03-architecture.md``, "The seams"): a service calls the interface; an entry
point hands it the concrete adapter; neither ``services/`` nor ``sources/`` imports the
other.

A source is structurally a ``SourceAdapter`` — it satisfies the protocol by having the
right method signatures, not by subclassing it. That way neither layer imports the
other: ``sources/`` does not import ``services/`` to inherit from this class, and
``services/`` does not import any concrete adapter.

No adapters exist yet: the draft event type that adapters produce is defined in
``domain/`` and arrives with the first migration after ``docs/02-domain-model.md``'s
tables are added. This Protocol exists now so the seam is declared before any adapter
is written.
"""

from typing import Protocol


class SourceAdapter(Protocol):
    """What every source adapter must look like.

    A concrete adapter in ``sources/`` satisfies this protocol structurally. It is
    reached only from an entry point (``poll.py``) or a service, never imported by
    another module in the four layers.

    No members are declared yet: the draft event type, and the method that produces it,
    arrive with the first migration after ``docs/02-domain-model.md``'s tables are added
    and Q-D's answer confirms what each source provides.
    """
