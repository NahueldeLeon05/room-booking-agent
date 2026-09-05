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
