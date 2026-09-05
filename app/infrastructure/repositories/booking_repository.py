from datetime import datetime

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import OFFICE_TZ
from app.domain.booking import Booking
from app.domain.exceptions import RoomNotAvailable
from app.domain.room import Room
from app.domain.time_range import TimeRange
from app.infrastructure.models import BookingModel, BookingSlotModel, RoomModel


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

    def create(
        self,
        user_id: int,
        room_id: int,
        title: str,
        attendees: int,
        time_range: TimeRange,
    ) -> Booking:
        booking_model = BookingModel(
            room_id=room_id,
            user_id=user_id,
            title=title,
            attendees=attendees,
            starts_at=time_range.starts_at,
            ends_at=time_range.ends_at,
            status="active",
            created_at=datetime.now(OFFICE_TZ),
        )

        try:
            self._session.add(booking_model)
            self._session.flush()
            self._session.add_all(
                BookingSlotModel(
                    booking_id=booking_model.id,
                    room_id=room_id,
                    slot_start=slot_start,
                )
                for slot_start in time_range.slot_starts()
            )
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()
            raise RoomNotAvailable() from error

        created_booking = self._session.execute(
            select(BookingModel, RoomModel.name)
            .join(RoomModel, BookingModel.room_id == RoomModel.id)
            .where(BookingModel.id == booking_model.id)
        ).one()

        return self._to_domain(*created_booking)

    def find_taken_slots(
        self,
        room_id: int,
        time_range: TimeRange,
    ) -> list[datetime]:
        statement = (
            select(BookingSlotModel.slot_start)
            .where(
                BookingSlotModel.room_id == room_id,
                BookingSlotModel.slot_start.in_(time_range.slot_starts()),
            )
            .order_by(BookingSlotModel.slot_start.asc())
        )

        return list(self._session.scalars(statement).all())

    def find_rooms_available_in(
        self,
        time_range: TimeRange,
        min_capacity: int,
    ) -> list[Room]:
        occupied_slot_exists = exists().where(
            BookingSlotModel.room_id == RoomModel.id,
            BookingSlotModel.slot_start.in_(time_range.slot_starts()),
        )
        statement = (
            select(RoomModel)
            .where(
                RoomModel.capacity >= min_capacity,
                ~occupied_slot_exists,
            )
            .order_by(RoomModel.capacity.asc(), RoomModel.name.asc())
        )

        return [
            self._room_to_domain(room_model)
            for room_model in self._session.scalars(statement).all()
        ]

    def get_room_by_name(self, name: str) -> Room | None:
        room_model = self._session.scalar(
            select(RoomModel).where(RoomModel.name == name)
        )

        if room_model is None:
            return None

        return self._room_to_domain(room_model)

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

    @staticmethod
    def _room_to_domain(room_model: RoomModel) -> Room:
        return Room(
            id=room_model.id,
            name=room_model.name,
            capacity=room_model.capacity,
        )
