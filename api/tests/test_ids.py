"""Tests for the UUIDv7 ordering guarantees in ids.py.

The module promises ids that sort in mint order — within a millisecond, across a counter
overflow, and across a backwards clock step. These tests hold it to that promise.
"""

from unittest.mock import patch

import constellate.ids as ids_mod
from constellate.ids import uuid7

# An arbitrary fixed point in time, expressed in nanoseconds.
_FROZEN_NS = 1_700_000_000_000_000_000


def test_uuid7_strict_ordering_within_millisecond_crossing_counter_overflow(monkeypatch):
    """5,000 ids at a frozen clock value ascend strictly, including across the counter overflow.

    The counter occupies 12 bits (maximum value 4,095), so generating 5,000 ids in one
    millisecond forces at least one overflow. On overflow the implementation borrows a
    millisecond from the timestamp field, so ordering is maintained even when the counter
    wraps.
    """
    monkeypatch.setattr(ids_mod, "_last_ms", -1)
    monkeypatch.setattr(ids_mod, "_counter", 0)
    with patch("constellate.ids.time.time_ns", return_value=_FROZEN_NS):
        ids = [uuid7() for _ in range(5_000)]
    assert all(a < b for a, b in zip(ids, ids[1:], strict=False))


def test_uuid7_strict_ordering_after_clock_step_backward(monkeypatch):
    """An id minted after a backwards clock step is still greater than the id before it.

    The implementation keeps _last_ms from the previous call and increments the counter
    when the observed clock is behind that value, so the new id's timestamp field is no
    less than the previous id's.
    """
    later_ns = _FROZEN_NS + 1_000_000_000  # 1 second ahead
    earlier_ns = _FROZEN_NS  # 1 second behind the previous call

    monkeypatch.setattr(ids_mod, "_last_ms", -1)
    monkeypatch.setattr(ids_mod, "_counter", 0)

    with patch("constellate.ids.time.time_ns", return_value=later_ns):
        id_before = uuid7()
    with patch("constellate.ids.time.time_ns", return_value=earlier_ns):
        id_after = uuid7()

    assert id_after > id_before
