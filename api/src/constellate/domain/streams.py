"""The streams a source's records belong to, which precedence and matching are written in.

A new source takes its place in one of two ways. A source of a service already observed joins
a stream: one line of ``_STREAM_OF_SOURCE``. A new observer adds a ``Stream`` member, its rank
in ``precedence.py``'s ``ITEM_ORDER`` and ``START_ORDER`` (``DURATION_ORDER`` too if it
measures), and a window in ``matching.py`` if it pairs with another stream.
"""

from enum import StrEnum


class Stream(StrEnum):
    """One independent observer of plays: a stream sees a given play at most once.

    Takeout and Portability are two paths to one Google store, so they are one stream: both
    produce the same record keys, and matching never pairs a stream with itself.
    """

    SPOTIFY_EXPORT = "spotify-export"
    LASTFM_SCROBBLES = "lastfm-scrobbles"
    SPOTIFY_POLLER = "spotify-poller"
    GOOGLE_HISTORY = "google-history"
    YOUTUBE_EXTENSION = "youtube-extension"


_STREAM_OF_SOURCE: dict[str, Stream] = {
    "spotify-export": Stream.SPOTIFY_EXPORT,
    "lastfm-scrobbles": Stream.LASTFM_SCROBBLES,
    "spotify-poller": Stream.SPOTIFY_POLLER,
    "youtube-takeout": Stream.GOOGLE_HISTORY,
    "google-portability": Stream.GOOGLE_HISTORY,
    "youtube-extension": Stream.YOUTUBE_EXTENSION,
}


def stream_of(source: str) -> Stream:
    """Return the stream a source belongs to, refusing a source with no stream."""
    try:
        return _STREAM_OF_SOURCE[source]
    except KeyError:
        raise ValueError(f"source {source!r} belongs to no stream") from None
