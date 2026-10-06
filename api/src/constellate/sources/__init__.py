"""Source adapters.

One module per external source — Spotify, YouTube, a Takeout export — that translates
what the source gives into the draft event ``domain/`` defines. Each adapter is reached
only through the ``SourceAdapter`` protocol in ``services/sources.py``; nothing in the
four layers imports a module from this package directly.

No adapters exist yet; ``SourceAdapter`` in ``services/sources.py`` says what one must
satisfy and what it waits on.
"""
