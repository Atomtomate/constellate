"""Activity poller entry point.

Run as ``python -m constellate.poll`` by the OS scheduler. When sources are configured
this command asks each pollable source for what is new since the cursor it stored,
ingests it through the service layer, stores the new cursor, and exits. A source that
is not configured is skipped with a log line rather than aborting the whole run.

No sources are configured yet: the draft event type arrives with the first migration,
and the first source adapter with its data-source document. Until then the command logs
once and exits 0, so the scheduling infrastructure can be wired up before the sources
exist.
"""

import logging

from constellate.logging_config import configure_logging

# Named, not __name__: run as `python -m constellate.poll` this module is `__main__`, which is
# no child of the "constellate" logger the handler is installed on, and the line would be lost.
logger = logging.getLogger("constellate.poll")


def main() -> int:
    """Poll all configured sources for new events and ingest them.

    Returns 0. No sources are configured yet.
    """
    configure_logging()
    logger.info("poll: no sources configured, nothing to do")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
