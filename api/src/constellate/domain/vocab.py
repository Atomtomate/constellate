"""The closed vocabularies the log's columns hold, and the type of an entity's id.

The values are ``docs/02-domain-model.md`` §7's ``CHECK`` lists. The database enforces the
same lists as literals; a test pushes every member through the ORM, so the two cannot drift
apart unseen.
"""

import uuid
from enum import StrEnum

# The key type of every table (the owner's decision, 2026-10-19): one alias, so changing it
# is one line.
type EntityId = uuid.UUID


class DurationBasis(StrEnum):
    """What an observation says about how long a play lasted."""

    MEASURED = "measured"
    TO_END = "to_end"
    START_ONLY = "start_only"


class ItemKind(StrEnum):
    """What an item is: a thing that is played or watched."""

    TRACK = "track"
    EPISODE = "episode"
    CHAPTER = "chapter"
    VIDEO = "video"


class CreatorKind(StrEnum):
    """What a creator is: nothing plays one, so it is never an item kind."""

    ARTIST = "artist"
    CHANNEL = "channel"
    SHOW = "show"


class CreatorRole(StrEnum):
    """How a creator stands to an item; a track has several artists, in order."""

    ARTIST = "artist"
    ALBUM_ARTIST = "album-artist"
    CHANNEL = "channel"
    SHOW = "show"
