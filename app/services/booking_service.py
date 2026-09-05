from typing import Protocol

from app.domain.booking import Booking


class BookingReader(Protocol):
    def find_active_by_user(self, user_id: int) -> list[Booking]: ...


class BookingService:
    def __init__(self, repository: BookingReader) -> None:
        self._repository = repository

    def list_my_bookings(self, user_id: int) -> list[Booking]:
        return self._repository.find_active_by_user(user_id)
