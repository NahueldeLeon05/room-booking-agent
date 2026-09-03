from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.database import init_db
from app.infrastructure.models import (
    BookingModel,
    BookingSlotModel,
    RoomModel,
    UserModel,
)
from app.infrastructure.seed import seed


def test_seed_creates_five_rooms_and_two_users(db_engine: Engine) -> None:
    init_db(db_engine)

    with Session(bind=db_engine) as session:
        seed(session)

        room_count = session.scalar(select(func.count()).select_from(RoomModel))
        user_count = session.scalar(select(func.count()).select_from(UserModel))

    assert room_count == 5
    assert user_count == 2


def test_running_seed_twice_does_not_duplicate_data(db_engine: Engine) -> None:
    init_db(db_engine)

    with Session(bind=db_engine) as session:
        seed(session)
        seed(session)

        room_count = session.scalar(select(func.count()).select_from(RoomModel))
        user_count = session.scalar(select(func.count()).select_from(UserModel))

    assert room_count == 5
    assert user_count == 2


def test_two_bookings_cannot_hold_the_same_room_and_slot(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    slot_start = datetime(2026, 9, 3, 10, 0)

    with Session(bind=db_engine) as session:
        room = RoomModel(name="A", capacity=4)
        user = UserModel(username="User1", password_hash="not-used")
        session.add_all([room, user])
        session.flush()

        first_booking = BookingModel(
            room_id=room.id,
            user_id=user.id,
            title="First booking",
            attendees=2,
            starts_at=slot_start,
            ends_at=slot_start + timedelta(minutes=30),
            status="active",
            created_at=slot_start,
        )
        second_booking = BookingModel(
            room_id=room.id,
            user_id=user.id,
            title="Second booking",
            attendees=2,
            starts_at=slot_start,
            ends_at=slot_start + timedelta(minutes=30),
            status="active",
            created_at=slot_start,
        )
        session.add_all([first_booking, second_booking])
        session.flush()

        session.add_all(
            [
                BookingSlotModel(
                    booking_id=first_booking.id,
                    room_id=room.id,
                    slot_start=slot_start,
                ),
                BookingSlotModel(
                    booking_id=second_booking.id,
                    room_id=room.id,
                    slot_start=slot_start,
                ),
            ]
        )

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()
