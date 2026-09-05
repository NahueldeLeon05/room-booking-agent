from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.booking import Booking
from app.domain.time_range import TimeRange
from app.infrastructure.models import BookingModel, RoomModel


class BookingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_active_by_user(self, user_id: int) -> list[Booking]:
        statement = (
            select(BookingModel, RoomModel.name)
            .join(RoomModel, BookingModel.room_id == RoomModel.id)
            .where(
                BookingModel.user_id == user_id,
                BookingModel.status == "active",
            )
            .order_by(BookingModel.starts_at.asc())
        )
        rows = self._session.execute(statement).all()

        return [
            self._to_domain(booking_model, room_name)
            for booking_model, room_name in rows
        ]

    @staticmethod
    def _to_domain(booking_model: BookingModel, room_name: str) -> Booking:
        return Booking(
            id=booking_model.id,
            room_name=room_name,
            user_id=booking_model.user_id,
            title=booking_model.title,
            attendees=booking_model.attendees,
            time_range=TimeRange(
                starts_at=booking_model.starts_at,
                ends_at=booking_model.ends_at,
            ),
            status=booking_model.status,
        )
