"""Source-adapter interface that ``services/`` calls and ``sources/`` satisfies.

A service calls the interface; an entry point hands it the concrete adapter. The
structural protocol means neither layer imports the other: ``sources/`` does not
subclass anything from ``services/``, and ``services/`` imports no concrete adapter.

``CatalogueAdapter``, the second protocol (``docs/03-architecture.md``), is not declared
here yet: it yields catalogue facts for the cache, not drafts, and the shape of a fact is
settled with its first adapter, ``youtube-data-api``, in the enrichment lane.
"""

from collections.abc import Iterator, Mapping
from typing import Any, Protocol

from constellate.domain.draft import Batch


class SourceAdapter(Protocol):
    """What every adapter of a log source must look like.

    A concrete adapter in ``sources/`` satisfies this protocol structurally: it has the
    right members without subclassing. Reached only from an entry point (``poll.py``, an
    importer) or a service, never from another layer or leaf.
    """

    key: str
    """The source row's key, such as ``spotify-export``."""

    service: str
    """The service every draft it produces is of."""

    def fetch(self, cursor: Mapping[str, Any] | None = None) -> Iterator[Batch]:
        """Yield batches oldest first, each with the cursor position it covers.

        A file has no cursor and ignores the argument; a poller reads only its own shape
        from it. The adapter does HTTP or file parsing and never touches the database.
        """
        ...
