"""The streams a source's records belong to, which precedence and matching are written in."""

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
    """Return the stream a source belongs to, refusing a source with no place in the orders."""
    try:
        return _STREAM_OF_SOURCE[source]
    except KeyError:
        raise ValueError(f"source {source!r} has no place in the precedence orders") from None
