"""Source adapters.

One module per external source — Spotify, YouTube, a Takeout export — that translates
what the source gives into the draft event ``domain/`` defines. Each adapter is reached
only through the ``SourceAdapter`` protocol in ``services/sources.py``; nothing in the
four layers imports a module from this package directly.

No adapters exist yet: which sources are needed and how they are polled or imported is
Q-D's answer. They arrive in later PRs once that question is settled.
"""
