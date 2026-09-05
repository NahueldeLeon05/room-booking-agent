from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from app.config import OFFICE_TZ
from app.domain.booking import Booking
from app.domain.exceptions import (
    BookingNotFound,
    RoomNotAvailable,
    RoomNotFound,
)
from app.domain.room import Room
from app.domain.rules import (
    validate_booking_horizon,
    validate_business_hours,
    validate_can_be_cancelled,
    validate_max_duration,
    validate_minimum_attendees,
    validate_not_in_the_past,
    validate_room_capacity,
    validate_slot_alignment,
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

    def find_rooms_available_in(
        self,
        time_range: TimeRange,
        min_capacity: int,
    ) -> list[Room]: ...

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
        now = self._clock()

        validate_slot_alignment(time_range)
        validate_max_duration(time_range)
        validate_working_day(time_range)
        validate_business_hours(time_range)
        validate_not_in_the_past(time_range, now)
        validate_booking_horizon(time_range, now)
        validate_minimum_attendees(attendees)

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
            alternatives = self._repository.find_rooms_available_in(
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
