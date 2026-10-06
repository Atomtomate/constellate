"""UUIDv7 generation (RFC 9562).

Python 3.13 has no ``uuid.uuid7``; it arrives in 3.14. This is a small local
implementation so ids are time-ordered, which keeps index locality sane and makes
creation order recoverable from the id alone.

Ordering holds *within a millisecond* too, via the monotonic counter RFC 9562 permits
in place of ``rand_a``. Without it, two ids minted in the same millisecond sort at
random, which would make "newest first" wrong exactly when several events are ingested
in one sitting. Guaranteed monotonic per process; across processes, ordering is only as
good as the clock.

Whether UUIDv7 is the right key type for this project's tables is decided in
``docs/02-domain-model.md`` §7–§8, which was a placeholder at porting time.
"""

import os
import secrets
import threading
import time
import uuid

__all__ = ["uuid7"]

_VERSION = 0x7
_VARIANT = 0b10
_COUNTER_BITS = 12
_COUNTER_MAX = (1 << _COUNTER_BITS) - 1

_lock = threading.Lock()
_last_ms = -1
_counter = 0


def uuid7() -> uuid.UUID:
    """Return a time-ordered UUID version 7.

    Layout: 48-bit big-endian Unix timestamp in milliseconds, 4-bit version, a 12-bit
    monotonic counter, 2-bit variant, then 62 bits of randomness.
    """
    global _last_ms, _counter

    with _lock:
        now_ms = time.time_ns() // 1_000_000
        if now_ms > _last_ms:
            _last_ms = now_ms
            # Seed with the top bit clear so there is always room to increment.
            _counter = secrets.randbits(_COUNTER_BITS - 1)
        else:
            # Same millisecond, or the clock went backwards. Either way, step the
            # counter and borrow a millisecond if it overflows.
            _counter += 1
            if _counter > _COUNTER_MAX:
                _last_ms += 1
                _counter = 0
        timestamp_ms, counter = _last_ms, _counter

    value = timestamp_ms << 80
    value |= _VERSION << 76
    value |= counter << 64
    value |= _VARIANT << 62
    value |= int.from_bytes(os.urandom(8), "big") & ((1 << 62) - 1)

    return uuid.UUID(int=value)
