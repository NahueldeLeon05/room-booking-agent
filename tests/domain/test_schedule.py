from datetime import datetime

from app.config import OFFICE_TZ
from app.domain.schedule import derive_free_ranges, merge_contiguous
from app.domain.time_range import TimeRange


def test_contiguous_slots_are_merged_into_one_range() -> None:
    slots = [_at(10, 0), _at(10, 30), _at(11, 0)]

    ranges = merge_contiguous(slots)

    assert ranges == [TimeRange(_at(10, 0), _at(11, 30))]


def test_non_contiguous_slots_produce_separate_ranges() -> None:
    slots = [_at(10, 0), _at(10, 30), _at(15, 0)]

    ranges = merge_contiguous(slots)

    assert ranges == [
        TimeRange(_at(10, 0), _at(11, 0)),
        TimeRange(_at(15, 0), _at(15, 30)),
    ]


def test_empty_slot_list_produces_no_ranges() -> None:
    assert merge_contiguous([]) == []


def test_free_ranges_are_the_complement_of_taken_ranges() -> None:
    business_hours = TimeRange(_at(8, 0), _at(20, 0))
    taken_ranges = [
        TimeRange(_at(10, 0), _at(11, 30)),
        TimeRange(_at(15, 0), _at(15, 30)),
    ]

    free_ranges = derive_free_ranges(taken_ranges, business_hours)

    assert free_ranges == [
        TimeRange(_at(8, 0), _at(10, 0)),
        TimeRange(_at(11, 30), _at(15, 0)),
        TimeRange(_at(15, 30), _at(20, 0)),
    ]


def _at(hour: int, minute: int) -> datetime:
    return datetime(2026, 9, 7, hour, minute, tzinfo=OFFICE_TZ)
