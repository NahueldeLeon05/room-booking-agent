from collections.abc import Generator
from datetime import datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import OFFICE_TZ
from app.domain.exceptions import (
    InvalidTitle,
    RoomCapacityExceeded,
    RoomNotAvailable,
    RoomNotFound,
)
from app.infrastructure.database import init_db
from app.infrastructure.models import BookingModel, BookingSlotModel, UserModel
from app.infrastructure.repositories.booking_repository import BookingRepository
from app.infrastructure.seed import seed
from app.services.booking_service import BookingService


NOW = datetime(2026, 9, 7, 10, 0, tzinfo=OFFICE_TZ)


@pytest.fixture
def service_and_session(
    db_engine: Engine,
) -> Generator[tuple[BookingService, Session], None, None]:
    init_db(db_engine)

    with Session(bind=db_engine) as session:
        seed(session)
        repository = BookingRepository(session)
        service = BookingService(repository, clock=lambda: NOW)
        yield service, session


def test_valid_booking_is_created_with_its_slots(
    service_and_session: tuple[BookingService, Session],
) -> None:
    service, session = service_and_session

    booking = service.create_booking(
        user_id=_user_id(session, "User1"),
        room_name="A",
        title="Planning",
        attendees=4,
        starts_at=datetime(2026, 9, 7, 10, 30, tzinfo=OFFICE_TZ),
        ends_at=datetime(2026, 9, 7, 11, 30, tzinfo=OFFICE_TZ),
    )

    slots = session.scalars(
        select(BookingSlotModel)
        .where(BookingSlotModel.booking_id == booking.id)
        .order_by(BookingSlotModel.slot_start.asc())
    ).all()

    assert booking.room_name == "A"
    assert [slot.slot_start.strftime("%H:%M") for slot in slots] == [
        "10:30",
        "11:00",
    ]


def test_booking_overlapping_an_existing_one_is_rejected(
    service_and_session: tuple[BookingService, Session],
) -> None:
    service, session = service_and_session
    user_id = _user_id(session, "User1")
    service.create_booking(
        user_id=user_id,
        room_name="A",
        title="First booking",
        attendees=2,
        starts_at=datetime(2026, 9, 7, 10, 30, tzinfo=OFFICE_TZ),
        ends_at=datetime(2026, 9, 7, 11, 30, tzinfo=OFFICE_TZ),
    )

    with pytest.raises(RoomNotAvailable) as raised:
        service.create_booking(
            user_id=user_id,
            room_name="A",
            title="Overlapping booking",
            attendees=2,
            starts_at=datetime(2026, 9, 7, 11, 0, tzinfo=OFFICE_TZ),
            ends_at=datetime(2026, 9, 7, 12, 0, tzinfo=OFFICE_TZ),
        )

    assert [
        slot.strftime("%H:%M") for slot in raised.value.taken_slots
    ] == ["11:00"]
    assert raised.value.alternative_rooms == ["B", "C", "D", "E"]
    assert "Occupied slots" in str(raised.value)
    assert "Available rooms for the full range" in str(raised.value)


def test_booking_starting_when_another_ends_is_accepted(
    service_and_session: tuple[BookingService, Session],
) -> None:
    service, session = service_and_session
    user_id = _user_id(session, "User1")
    service.create_booking(
        user_id=user_id,
        room_name="A",
        title="First booking",
        attendees=2,
        starts_at=datetime(2026, 9, 7, 10, 30, tzinfo=OFFICE_TZ),
        ends_at=datetime(2026, 9, 7, 11, 30, tzinfo=OFFICE_TZ),
    )

    booking = service.create_booking(
        user_id=user_id,
        room_name="A",
        title="Following booking",
        attendees=2,
        starts_at=datetime(2026, 9, 7, 11, 30, tzinfo=OFFICE_TZ),
        ends_at=datetime(2026, 9, 7, 12, 0, tzinfo=OFFICE_TZ),
    )

    assert booking.title == "Following booking"


def test_booking_in_unknown_room_is_rejected(
    service_and_session: tuple[BookingService, Session],
) -> None:
    service, session = service_and_session

    with pytest.raises(RoomNotFound):
        service.create_booking(
            user_id=_user_id(session, "User1"),
            room_name="Z",
            title="Unknown room",
            attendees=2,
            starts_at=datetime(2026, 9, 7, 10, 30, tzinfo=OFFICE_TZ),
            ends_at=datetime(2026, 9, 7, 11, 0, tzinfo=OFFICE_TZ),
        )


def test_booking_exceeding_room_capacity_is_rejected(
    service_and_session: tuple[BookingService, Session],
) -> None:
    service, session = service_and_session

    with pytest.raises(RoomCapacityExceeded):
        service.create_booking(
            user_id=_user_id(session, "User1"),
            room_name="A",
            title="Too many attendees",
            attendees=5,
            starts_at=datetime(2026, 9, 7, 10, 30, tzinfo=OFFICE_TZ),
            ends_at=datetime(2026, 9, 7, 11, 0, tzinfo=OFFICE_TZ),
        )


def test_booking_with_blank_title_is_rejected_before_persistence(
    service_and_session: tuple[BookingService, Session],
) -> None:
    service, session = service_and_session

    with pytest.raises(InvalidTitle):
        service.create_booking(
            user_id=_user_id(session, "User1"),
            room_name="A",
            title="   ",
            attendees=2,
            starts_at=datetime(2026, 9, 7, 10, 30, tzinfo=OFFICE_TZ),
            ends_at=datetime(2026, 9, 7, 11, 0, tzinfo=OFFICE_TZ),
        )

    booking_count = session.scalar(
        select(func.count()).select_from(BookingModel)
    )
    slot_count = session.scalar(
        select(func.count()).select_from(BookingSlotModel)
    )

    assert booking_count == 0
    assert slot_count == 0


def test_failed_booking_leaves_no_orphan_rows(
    service_and_session: tuple[BookingService, Session],
) -> None:
    service, session = service_and_session
    user_id = _user_id(session, "User1")
    service.create_booking(
        user_id=user_id,
        room_name="A",
        title="Existing booking",
        attendees=2,
        starts_at=datetime(2026, 9, 7, 10, 30, tzinfo=OFFICE_TZ),
        ends_at=datetime(2026, 9, 7, 11, 30, tzinfo=OFFICE_TZ),
    )

    with pytest.raises(RoomNotAvailable):
        service.create_booking(
            user_id=user_id,
            room_name="A",
            title="Failed booking",
            attendees=2,
            starts_at=datetime(2026, 9, 7, 10, 0, tzinfo=OFFICE_TZ),
            ends_at=datetime(2026, 9, 7, 11, 0, tzinfo=OFFICE_TZ),
        )

    booking_count = session.scalar(
        select(func.count()).select_from(BookingModel)
    )
    slot_count = session.scalar(
        select(func.count()).select_from(BookingSlotModel)
    )
    bookings_without_slots = session.scalar(
        select(func.count())
        .select_from(BookingModel)
        .outerjoin(
            BookingSlotModel,
            BookingSlotModel.booking_id == BookingModel.id,
        )
        .where(BookingSlotModel.id.is_(None))
    )
    slots_without_bookings = session.scalar(
        select(func.count())
        .select_from(BookingSlotModel)
        .outerjoin(
            BookingModel,
            BookingModel.id == BookingSlotModel.booking_id,
        )
        .where(BookingModel.id.is_(None))
    )

    assert booking_count == 1
    assert slot_count == 2
    assert bookings_without_slots == 0
    assert slots_without_bookings == 0


def _user_id(session: Session, username: str) -> int:
    user_id = session.scalar(
        select(UserModel.id).where(UserModel.username == username)
    )
    assert user_id is not None
    return user_id
