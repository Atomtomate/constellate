"""Service-layer errors, mapped to HTTP status codes by ``api/errors.py``.

Each class names a category of failure; the mapping to status code and ``ErrorCode``
string lives in ``api/errors.py``, not here, so the service layer carries no knowledge
of HTTP. A router raises one of these and never a ``HTTPException``; the handler in
``api/errors.py`` translates it for the wire.
"""


class ServiceError(Exception):
    """Base for errors the API should report rather than log as a crash."""


class NotFound(ServiceError):
    """A referenced entity does not exist."""


class Conflict(ServiceError):
    """The request collides with something that already exists."""


class Malformed(ServiceError):
    """The request itself is unreadable — distinct from breaking a domain rule."""


class Unauthenticated(ServiceError):
    """No usable session — the caller is not signed in, or the session has ended.

    Deliberately indistinguishable from an expired or revoked token: telling a caller
    which of the three it was tells an attacker whether a token was ever real.
    """


class Forbidden(ServiceError):
    """Signed in, but not allowed to perform this action."""
