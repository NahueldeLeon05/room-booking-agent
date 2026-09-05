class DomainError(Exception):
    """Base exception for domain errors."""


class InvalidTimeRange(DomainError):
    """Raised when a time range does not end after it starts."""
