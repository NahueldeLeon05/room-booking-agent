from datetime import datetime, timedelta

import pytest

from app.config import (
    MAX_BOOKING_HORIZON_DAYS,
    MAX_BOOKING_HOURS,
    MIN_ATTENDEES,
    OFFICE_TZ,
    SLOT_MINUTES,
)
from app.domain.exceptions import (
    BookingAlreadyStarted,
    BookingHorizonExceeded,
    BookingInThePast,
    BookingTooLong,
    InvalidAttendeeCount,
    InvalidTitle,
    MisalignedSlot,
    NonWorkingDay,
    OutsideBusinessHours,
    RoomCapacityExceeded,
)
from app.domain.rules import (
    validate_booking_horizon,
    validate_business_hours,
    validate_can_be_cancelled,
    validate_max_duration,
    validate_minimum_attendees,
    validate_not_in_the_past,
    validate_room_capacity,
    validate_slot_alignment,
    validate_title,
    validate_working_day,
)
from app.domain.time_range import TimeRange


NOW = datetime(2026, 9, 7, 10, 0, tzinfo=OFFICE_TZ)


def test_booking_starting_exactly_now_is_accepted() -> None:
    time_range = TimeRange(NOW, NOW + timedelta(minutes=SLOT_MINUTES))

    validate_not_in_the_past(time_range, NOW)


def test_booking_starting_in_the_past_is_rejected() -> None:
    time_range = TimeRange(
        NOW - timedelta(minutes=SLOT_MINUTES),
        NOW,
    )

    with pytest.raises(BookingInThePast):
        validate_not_in_the_past(time_range, NOW)


def test_booking_on_friday_is_accepted() -> None:
    time_range = TimeRange(
        datetime(2026, 9, 11, 10, 0, tzinfo=OFFICE_TZ),
        datetime(2026, 9, 11, 10, 30, tzinfo=OFFICE_TZ),
    )

    validate_working_day(time_range)


def test_booking_on_saturday_is_rejected() -> None:
    time_range = TimeRange(
        datetime(2026, 9, 12, 10, 0, tzinfo=OFFICE_TZ),
        datetime(2026, 9, 12, 10, 30, tzinfo=OFFICE_TZ),
    )

    with pytest.raises(NonWorkingDay):
        validate_working_day(time_range)


def test_booking_on_sunday_is_rejected() -> None:
    time_range = TimeRange(
        datetime(2026, 9, 13, 10, 0, tzinfo=OFFICE_TZ),
        datetime(2026, 9, 13, 10, 30, tzinfo=OFFICE_TZ),
    )

    with pytest.raises(NonWorkingDay):
        validate_working_day(time_range)


def test_booking_starting_at_business_opening_is_accepted() -> None:
    time_range = TimeRange(
        datetime(2026, 9, 7, 8, 0, tzinfo=OFFICE_TZ),
        datetime(2026, 9, 7, 8, 30, tzinfo=OFFICE_TZ),
    )

    validate_business_hours(time_range)


def test_booking_starting_before_business_opening_is_rejected() -> None:
    time_range = TimeRange(
        datetime(2026, 9, 7, 7, 30, tzinfo=OFFICE_TZ),
        datetime(2026, 9, 7, 8, 30, tzinfo=OFFICE_TZ),
    )

    with pytest.raises(OutsideBusinessHours):
        validate_business_hours(time_range)


def test_booking_ending_at_business_closing_is_accepted() -> None:
    time_range = TimeRange(
        datetime(2026, 9, 7, 19, 30, tzinfo=OFFICE_TZ),
        datetime(2026, 9, 7, 20, 0, tzinfo=OFFICE_TZ),
    )

    validate_business_hours(time_range)


def test_booking_ending_after_business_closing_is_rejected() -> None:
    time_range = TimeRange(
        datetime(2026, 9, 7, 19, 30, tzinfo=OFFICE_TZ),
        datetime(2026, 9, 7, 20, 30, tzinfo=OFFICE_TZ),
    )

    with pytest.raises(OutsideBusinessHours):
        validate_business_hours(time_range)


def test_booking_crossing_into_another_day_is_rejected() -> None:
    time_range = TimeRange(
        datetime(2026, 9, 7, 19, 30, tzinfo=OFFICE_TZ),
        datetime(2026, 9, 8, 8, 0, tzinfo=OFFICE_TZ),
    )

    with pytest.raises(OutsideBusinessHours):
        validate_business_hours(time_range)


def test_booking_aligned_to_slot_boundaries_is_accepted() -> None:
    time_range = TimeRange(
        datetime(2026, 9, 7, 10, 0, tzinfo=OFFICE_TZ),
        datetime(2026, 9, 7, 10, 30, tzinfo=OFFICE_TZ),
    )

    validate_slot_alignment(time_range)


def test_booking_not_aligned_to_slot_boundaries_is_rejected() -> None:
    time_range = TimeRange(
        datetime(2026, 9, 7, 10, 15, tzinfo=OFFICE_TZ),
        datetime(2026, 9, 7, 10, 45, tzinfo=OFFICE_TZ),
    )

    with pytest.raises(MisalignedSlot):
        validate_slot_alignment(time_range)


def test_booking_lasting_exactly_maximum_duration_is_accepted() -> None:
    time_range = TimeRange(
        NOW,
        NOW + timedelta(hours=MAX_BOOKING_HOURS),
    )

    validate_max_duration(time_range)


def test_booking_longer_than_maximum_duration_is_rejected() -> None:
    time_range = TimeRange(
        NOW,
        NOW
        + timedelta(
            hours=MAX_BOOKING_HOURS,
            minutes=SLOT_MINUTES,
        ),
    )

    with pytest.raises(BookingTooLong):
        validate_max_duration(time_range)


def test_booking_with_a_title_is_accepted() -> None:
    validate_title("Planning")


@pytest.mark.parametrize("title", ["", "   "])
def test_booking_with_a_blank_title_is_rejected(title: str) -> None:
    with pytest.raises(InvalidTitle):
        validate_title(title)


def test_booking_with_minimum_attendees_is_accepted() -> None:
    validate_minimum_attendees(MIN_ATTENDEES)


def test_booking_with_zero_attendees_is_rejected() -> None:
    with pytest.raises(InvalidAttendeeCount):
        validate_minimum_attendees(MIN_ATTENDEES - 1)


def test_attendees_equal_to_room_capacity_are_accepted() -> None:
    validate_room_capacity(attendees=4, capacity=4)


def test_attendees_above_room_capacity_are_rejected() -> None:
    with pytest.raises(RoomCapacityExceeded):
        validate_room_capacity(attendees=5, capacity=4)


def test_booking_exactly_at_maximum_horizon_is_accepted() -> None:
    starts_at = NOW + timedelta(days=MAX_BOOKING_HORIZON_DAYS)
    time_range = TimeRange(
        starts_at,
        starts_at + timedelta(minutes=SLOT_MINUTES),
    )

    validate_booking_horizon(time_range, NOW)


def test_booking_beyond_maximum_horizon_is_rejected() -> None:
    starts_at = NOW + timedelta(days=MAX_BOOKING_HORIZON_DAYS + 1)
    time_range = TimeRange(
        starts_at,
        starts_at + timedelta(minutes=SLOT_MINUTES),
    )

    with pytest.raises(BookingHorizonExceeded):
        validate_booking_horizon(time_range, NOW)


def test_booking_cancelled_before_start_is_accepted() -> None:
    starts_at = NOW + timedelta(minutes=SLOT_MINUTES)

    validate_can_be_cancelled(starts_at, NOW)


def test_booking_cancelled_exactly_at_start_is_rejected() -> None:
    with pytest.raises(BookingAlreadyStarted):
        validate_can_be_cancelled(NOW, NOW)


def test_booking_cancelled_after_start_is_rejected() -> None:
    starts_at = NOW - timedelta(minutes=SLOT_MINUTES)

    with pytest.raises(BookingAlreadyStarted):
        validate_can_be_cancelled(starts_at, NOW)
