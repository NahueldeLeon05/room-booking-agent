from datetime import datetime, timedelta

import pytest

from app.domain.exceptions import InvalidTimeRange
from app.domain.time_range import TimeRange


def test_duration_is_computed_from_bounds() -> None:
    time_range = TimeRange(
        starts_at=datetime(2026, 9, 7, 10, 0),
        ends_at=datetime(2026, 9, 7, 11, 30),
    )

    assert time_range.duration == timedelta(hours=1, minutes=30)


def test_range_ending_before_it_starts_is_rejected() -> None:
    with pytest.raises(InvalidTimeRange):
        TimeRange(
            starts_at=datetime(2026, 9, 7, 10, 0),
            ends_at=datetime(2026, 9, 7, 9, 30),
        )


def test_range_with_equal_bounds_is_rejected() -> None:
    with pytest.raises(InvalidTimeRange):
        TimeRange(
            starts_at=datetime(2026, 9, 7, 10, 0),
            ends_at=datetime(2026, 9, 7, 10, 0),
        )


def test_range_ending_when_another_starts_does_not_overlap() -> None:
    first = TimeRange(
        starts_at=datetime(2026, 9, 7, 10, 0),
        ends_at=datetime(2026, 9, 7, 11, 30),
    )
    second = TimeRange(
        starts_at=datetime(2026, 9, 7, 11, 30),
        ends_at=datetime(2026, 9, 7, 12, 0),
    )

    assert first.overlaps(second) is False


def test_partially_covering_ranges_overlap() -> None:
    first = TimeRange(
        starts_at=datetime(2026, 9, 7, 10, 0),
        ends_at=datetime(2026, 9, 7, 11, 30),
    )
    second = TimeRange(
        starts_at=datetime(2026, 9, 7, 11, 0),
        ends_at=datetime(2026, 9, 7, 12, 0),
    )

    assert first.overlaps(second) is True


def test_range_not_aligned_to_slots_is_detected() -> None:
    time_range = TimeRange(
        starts_at=datetime(2026, 9, 7, 10, 15),
        ends_at=datetime(2026, 9, 7, 11, 0),
    )

    assert time_range.is_slot_aligned() is False


def test_slot_starts_excludes_the_end_boundary() -> None:
    time_range = TimeRange(
        starts_at=datetime(2026, 9, 7, 10, 0),
        ends_at=datetime(2026, 9, 7, 11, 30),
    )

    assert time_range.slot_starts() == [
        datetime(2026, 9, 7, 10, 0),
        datetime(2026, 9, 7, 10, 30),
        datetime(2026, 9, 7, 11, 0),
    ]
