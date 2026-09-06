from collections.abc import Callable
from datetime import date, datetime
from typing import Protocol

from app.config import (
    BUSINESS_END,
    BUSINESS_START,
    OFFICE_TZ,
    ROOM_CAPACITIES,
)
from app.domain.booking import Booking
from app.domain.exceptions import (
    BookingNotFound,
    RoomCapacityExceeded,
    RoomNotAvailable,
    RoomNotFound,
)
from app.domain.room import Room
from app.domain.schedule import derive_free_ranges, merge_contiguous
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


class BookingRepositoryProtocol(Protocol):
    def find_active_by_user(self, user_id: int) -> list[Booking]: ...

    def find_by_id_and_user(
        self,
        booking_id: int,
        user_id: int,
    ) -> Booking | None: ...

    def create(
        self,
        user_id: int,
        room_id: int,
        title: str,
        attendees: int,
        time_range: TimeRange,
    ) -> Booking: ...

    def find_taken_slots(
        self,
        room_id: int,
        time_range: TimeRange,
    ) -> list[datetime]: ...

    def find_available_rooms(
        self,
        time_range: TimeRange,
        min_capacity: int,
    ) -> list[Room]: ...

    def find_taken_slots_for_day(
        self,
        room_id: int,
        day: date,
    ) -> list[datetime]: ...

    def get_room_by_name(self, name: str) -> Room | None: ...

    def cancel(self, booking_id: int) -> None: ...


def _current_office_time() -> datetime:
    return datetime.now(OFFICE_TZ)


class BookingService:
    def __init__(
        self,
        repository: BookingRepositoryProtocol,
        clock: Callable[[], datetime] = _current_office_time,
    ) -> None:
        self._repository = repository
        self._clock = clock

    def list_my_bookings(self, user_id: int) -> list[Booking]:
        return self._repository.find_active_by_user(user_id)

    def list_available_rooms(
        self,
        time_range: TimeRange,
        attendees: int,
    ) -> list[Room]:
        now = self._clock()
        self._validate_booking_request(time_range, attendees, now)

        maximum_capacity = max(ROOM_CAPACITIES.values())
        if attendees > maximum_capacity:
            raise RoomCapacityExceeded(
                f"The largest room holds {maximum_capacity} attendees, but "
                f"{attendees} were requested. Reduce the attendee count."
            )

        return self._repository.find_available_rooms(
            time_range,
            attendees,
        )

    def get_room_schedule(
        self,
        room_name: str,
        day: date,
    ) -> tuple[list[TimeRange], list[TimeRange]]:
        room = self._repository.get_room_by_name(room_name)
        if room is None:
            raise RoomNotFound(room_name)

        business_hours = TimeRange(
            starts_at=datetime.combine(
                day,
                BUSINESS_START,
                tzinfo=OFFICE_TZ,
            ),
            ends_at=datetime.combine(
                day,
                BUSINESS_END,
                tzinfo=OFFICE_TZ,
            ),
        )
        validate_working_day(business_hours)
        validate_booking_horizon(business_hours, self._clock())

        taken_slots = self._repository.find_taken_slots_for_day(
            room.id,
            day,
        )
        taken_ranges = merge_contiguous(taken_slots)
        free_ranges = derive_free_ranges(taken_ranges, business_hours)
        return taken_ranges, free_ranges

    def cancel_booking(self, user_id: int, booking_id: int) -> None:
        booking = self._repository.find_by_id_and_user(
            booking_id,
            user_id,
        )
        if booking is None or booking.status == "cancelled":
            raise BookingNotFound(booking_id)

        validate_can_be_cancelled(
            booking.time_range.starts_at,
            self._clock(),
        )
        self._repository.cancel(booking_id)

    def create_booking(
        self,
        user_id: int,
        room_name: str,
        title: str,
        attendees: int,
        starts_at: datetime,
        ends_at: datetime,
    ) -> Booking:
        time_range = TimeRange(starts_at=starts_at, ends_at=ends_at)
        validate_title(title)
        self._validate_booking_request(
            time_range,
            attendees,
            self._clock(),
        )

        room = self._repository.get_room_by_name(room_name)
        if room is None:
            raise RoomNotFound(room_name)

        validate_room_capacity(attendees, room.capacity)

        try:
            return self._repository.create(
                user_id=user_id,
                room_id=room.id,
                title=title,
                attendees=attendees,
                time_range=time_range,
            )
        except RoomNotAvailable as error:
            taken_slots = self._repository.find_taken_slots(
                room.id,
                time_range,
            )
            alternatives = self._repository.find_available_rooms(
                time_range,
                attendees,
            )
            raise RoomNotAvailable(
                room_name=room.name,
                taken_slots=taken_slots,
                alternative_rooms=[
                    alternative.name for alternative in alternatives
                ],
            ) from error

    @staticmethod
    def _validate_booking_request(
        time_range: TimeRange,
        attendees: int,
        now: datetime,
    ) -> None:
        validate_slot_alignment(time_range)
        validate_working_day(time_range)
        validate_max_duration(time_range)
        validate_business_hours(time_range)
        validate_not_in_the_past(time_range, now)
        validate_booking_horizon(time_range, now)
        validate_minimum_attendees(attendees)
