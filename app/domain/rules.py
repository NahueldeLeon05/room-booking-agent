from calendar import SATURDAY, SUNDAY
from datetime import datetime, timedelta

from app.config import (
    BUSINESS_END,
    BUSINESS_START,
    MAX_BOOKING_HORIZON_DAYS,
    MAX_BOOKING_HOURS,
    MIN_ATTENDEES,
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
from app.domain.time_range import TimeRange


def validate_not_in_the_past(time_range: TimeRange, now: datetime) -> None:
    if time_range.starts_at < now:
        raise BookingInThePast(
            f"Choose a start time at or after {now.isoformat()}; "
            f"the requested start was {time_range.starts_at.isoformat()}."
        )


def validate_working_day(time_range: TimeRange) -> None:
    if (
        time_range.starts_at.weekday() in (SATURDAY, SUNDAY)
        or time_range.ends_at.weekday() in (SATURDAY, SUNDAY)
    ):
        raise NonWorkingDay(
            "Bookings are only available Monday through Friday. "
            "Choose a weekday."
        )


def validate_business_hours(time_range: TimeRange) -> None:
    starts_at = time_range.starts_at.time()
    ends_at = time_range.ends_at.time()
    crosses_date_boundary = (
        time_range.starts_at.date() != time_range.ends_at.date()
    )

    if (
        crosses_date_boundary
        or starts_at < BUSINESS_START
        or ends_at > BUSINESS_END
    ):
        raise OutsideBusinessHours(
            f"Choose a time between {BUSINESS_START.strftime('%H:%M')} and "
            f"{BUSINESS_END.strftime('%H:%M')} on the same day."
        )


def validate_slot_alignment(time_range: TimeRange) -> None:
    if not time_range.is_slot_aligned():
        raise MisalignedSlot(
            f"Choose start and end times on {SLOT_MINUTES}-minute boundaries "
            "with no seconds or microseconds."
        )


def validate_max_duration(time_range: TimeRange) -> None:
    maximum_duration = timedelta(hours=MAX_BOOKING_HOURS)

    if time_range.duration > maximum_duration:
        raise BookingTooLong(
            f"Bookings can last at most {MAX_BOOKING_HOURS} hours. "
            "Choose a shorter time range."
        )


def validate_title(title: str) -> None:
    if not title.strip():
        raise InvalidTitle(
            "A booking needs a title. Provide a short description of the "
            "meeting."
        )


def validate_minimum_attendees(attendees: int) -> None:
    if attendees < MIN_ATTENDEES:
        raise InvalidAttendeeCount(
            f"A booking needs at least {MIN_ATTENDEES} attendee. "
            f"The requested count was {attendees}."
        )


def validate_room_capacity(attendees: int, capacity: int) -> None:
    if attendees > capacity:
        raise RoomCapacityExceeded(
            f"This room holds {capacity} attendees, but {attendees} were "
            "requested. Choose a larger room or reduce the attendee count."
        )


def validate_booking_horizon(time_range: TimeRange, now: datetime) -> None:
    latest_start = now + timedelta(days=MAX_BOOKING_HORIZON_DAYS)

    if time_range.starts_at > latest_start:
        raise BookingHorizonExceeded(
            f"Bookings can start at most {MAX_BOOKING_HORIZON_DAYS} days "
            f"ahead. Choose a start at or before {latest_start.isoformat()}."
        )


def validate_can_be_cancelled(starts_at: datetime, now: datetime) -> None:
    if starts_at <= now:
        raise BookingAlreadyStarted(
            f"This booking started at {starts_at.isoformat()} and can no "
            "longer be cancelled. Cancel bookings before their start time."
        )
