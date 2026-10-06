"""Source-adapter interface that ``services/`` calls and ``sources/`` satisfies.

A service calls the interface; an entry point hands it the concrete adapter. The
structural protocol means neither layer imports the other: ``sources/`` does not
subclass anything from ``services/``, and ``services/`` imports no concrete adapter.
"""

from typing import Protocol


class SourceAdapter(Protocol):
    """What every source adapter must look like.

    A concrete adapter in ``sources/`` satisfies this protocol structurally: it has the
    right members without subclassing. Reached only from an entry point (``poll.py``) or
    a service, never from another layer or leaf.

    No members are declared yet: a method's signature waits on the draft event type the
    first migration defines and the first adapter's confirmed shape.
    """
