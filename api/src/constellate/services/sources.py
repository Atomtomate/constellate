"""Source-adapter interface that ``services/`` calls and ``sources/`` satisfies.

The structural typing here enforces the one-ingestion-path rule
(``docs/03-architecture.md``, "The seams"): a service calls the interface; an entry
point hands it the concrete adapter; neither ``services/`` nor ``sources/`` imports the
other.

A source is structurally a ``SourceAdapter`` — it satisfies the protocol by having the
right method signatures, not by subclassing it. That way neither layer imports the
other: ``sources/`` does not import ``services/`` to inherit from this class, and
``services/`` does not import any concrete adapter.

No adapters exist yet: the draft event type that ``poll`` returns comes from
``domain/``, which is Q-C's answer. This Protocol exists now so the seam is declared
before any adapter is written.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class SourceAdapter(Protocol):
    """What every source adapter must look like.

    A concrete adapter in ``sources/`` satisfies this protocol structurally. It is
    reached only from an entry point (``poll.py``) or a service, never imported by
    another module in the four layers.

    The method signatures here are placeholders. They will be replaced when Q-C
    answers what a draft event is and Q-D answers what each source provides.
    """

    @property
    def name(self) -> str:
        """A short, stable identifier for this source, e.g. ``"spotify_poll"``."""
        ...

    def is_configured(self) -> bool:
        """Whether this adapter has the credentials it needs to run.

        ``poll.py`` calls this before asking for events; an unconfigured adapter is
        skipped with a log line rather than crashing the whole run.
        """
        ...
