from datetime import datetime


class DomainError(Exception):
    """Base exception for domain errors."""


class InvalidTimeRange(DomainError):
    """Raised when a time range does not end after it starts."""


class BookingInThePast(DomainError):
    """Raised when a booking starts before the current time."""


class NonWorkingDay(DomainError):
    """Raised when a booking falls outside Monday through Friday."""


class OutsideBusinessHours(DomainError):
    """Raised when a booking falls outside office opening hours."""


class MisalignedSlot(DomainError):
    """Raised when booking boundaries do not align with the slot grid."""


class BookingTooLong(DomainError):
    """Raised when a booking exceeds the maximum duration."""


class InvalidAttendeeCount(DomainError):
    """Raised when a booking has fewer than the minimum attendees."""


class RoomCapacityExceeded(DomainError):
    """Raised when a room cannot hold all requested attendees."""


class BookingHorizonExceeded(DomainError):
    """Raised when a booking is requested too far in advance."""


class BookingAlreadyStarted(DomainError):
    """Raised when cancellation is attempted at or after the start time."""


class RoomNotFound(DomainError):
    """Raised when a requested room does not exist."""

    def __init__(self, room_name: str) -> None:
        self.room_name = room_name
        super().__init__(
            f"Room {room_name} does not exist. Choose one of the listed rooms."
        )


class RoomNotAvailable(DomainError):
    """Raised when one or more requested room slots are already occupied."""

    def __init__(
        self,
        room_name: str | None = None,
        taken_slots: list[datetime] | None = None,
        alternative_rooms: list[str] | None = None,
    ) -> None:
        self.room_name = room_name
        self.taken_slots = list(taken_slots or [])
        self.alternative_rooms = list(alternative_rooms or [])

        room_label = f"Room {room_name}" if room_name else "The selected room"
        message = f"{room_label} is not available for the full time range."

        if self.taken_slots:
            formatted_slots = ", ".join(
                slot.isoformat(timespec="minutes") for slot in self.taken_slots
            )
            message += f" Occupied slots: {formatted_slots}."

        if self.alternative_rooms:
            alternatives = ", ".join(self.alternative_rooms)
            message += f" Available rooms for the full range: {alternatives}."
        elif alternative_rooms is not None:
            message += (
                " No other room with enough capacity is available for the "
                "full range."
            )

        super().__init__(message)
