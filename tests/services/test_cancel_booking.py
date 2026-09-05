from collections.abc import Generator
from datetime import datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import OFFICE_TZ
from app.domain.booking import Booking
from app.domain.exceptions import BookingAlreadyStarted, BookingNotFound
from app.infrastructure.database import init_db
from app.infrastructure.models import (
    BookingModel,
    BookingSlotModel,
    UserModel,
)
from app.infrastructure.repositories.booking_repository import BookingRepository
from app.infrastructure.seed import seed
from app.services.booking_service import BookingService


NOW = datetime(2026, 9, 7, 10, 0, tzinfo=OFFICE_TZ)
STARTS_AT = datetime(2026, 9, 7, 10, 30, tzinfo=OFFICE_TZ)
ENDS_AT = datetime(2026, 9, 7, 11, 30, tzinfo=OFFICE_TZ)


@pytest.fixture
def service_repository_and_session(
    db_engine: Engine,
) -> Generator[
    tuple[BookingService, BookingRepository, Session],
    None,
    None,
]:
    init_db(db_engine)

    with Session(bind=db_engine) as session:
        seed(session)
        repository = BookingRepository(session)
        service = BookingService(repository, clock=lambda: NOW)
        yield service, repository, session


def test_user_can_cancel_their_own_booking(
    service_repository_and_session: tuple[
        BookingService,
        BookingRepository,
        Session,
    ],
) -> None:
    service, _, session = service_repository_and_session
    booking = _create_booking(service, session, "User1")

    service.cancel_booking(
        user_id=_user_id(session, "User1"),
        booking_id=booking.id,
    )

    booking_model = session.get(BookingModel, booking.id)
    remaining_slots = session.scalar(
        select(func.count())
        .select_from(BookingSlotModel)
        .where(BookingSlotModel.booking_id == booking.id)
    )
    assert booking_model is not None
    assert booking_model.status == "cancelled"
    assert remaining_slots == 0


def test_user_cannot_cancel_another_users_booking(
    service_repository_and_session: tuple[
        BookingService,
        BookingRepository,
        Session,
    ],
) -> None:
    service, _, session = service_repository_and_session
    booking = _create_booking(service, session, "User1")

    with pytest.raises(BookingNotFound):
        service.cancel_booking(
            user_id=_user_id(session, "User2"),
            booking_id=booking.id,
        )

    booking_model = session.get(BookingModel, booking.id)
    assert booking_model is not None
    assert booking_model.status == "active"


def test_cancelling_unknown_booking_is_rejected(
    service_repository_and_session: tuple[
        BookingService,
        BookingRepository,
        Session,
    ],
) -> None:
    service, _, session = service_repository_and_session

    with pytest.raises(BookingNotFound):
        service.cancel_booking(
            user_id=_user_id(session, "User1"),
            booking_id=999,
        )


def test_cancelling_twice_is_rejected(
    service_repository_and_session: tuple[
        BookingService,
        BookingRepository,
        Session,
    ],
) -> None:
    service, _, session = service_repository_and_session
    user_id = _user_id(session, "User1")
    booking = _create_booking(service, session, "User1")
    service.cancel_booking(user_id=user_id, booking_id=booking.id)

    with pytest.raises(BookingNotFound):
        service.cancel_booking(user_id=user_id, booking_id=booking.id)


def test_cannot_cancel_a_booking_that_has_already_started(
    service_repository_and_session: tuple[
        BookingService,
        BookingRepository,
        Session,
    ],
) -> None:
    service, repository, session = service_repository_and_session
    booking = _create_booking(service, session, "User1")
    service_after_start = BookingService(
        repository,
        clock=lambda: datetime(2026, 9, 7, 11, 0, tzinfo=OFFICE_TZ),
    )

    with pytest.raises(BookingAlreadyStarted):
        service_after_start.cancel_booking(
            user_id=_user_id(session, "User1"),
            booking_id=booking.id,
        )


def test_cancelling_frees_the_room_for_the_same_time_range(
    service_repository_and_session: tuple[
        BookingService,
        BookingRepository,
        Session,
    ],
) -> None:
    service, _, session = service_repository_and_session
    user_id = _user_id(session, "User1")
    original_booking = _create_booking(service, session, "User1")
    service.cancel_booking(
        user_id=user_id,
        booking_id=original_booking.id,
    )

    replacement_booking = _create_booking(service, session, "User1")

    assert replacement_booking.id != original_booking.id
    assert replacement_booking.room_name == "A"


def _create_booking(
    service: BookingService,
    session: Session,
    username: str,
) -> Booking:
    return service.create_booking(
        user_id=_user_id(session, username),
        room_name="A",
        title="Planning",
        attendees=2,
        starts_at=STARTS_AT,
        ends_at=ENDS_AT,
    )


def _user_id(session: Session, username: str) -> int:
    user_id = session.scalar(
        select(UserModel.id).where(UserModel.username == username)
    )
    assert user_id is not None
    return user_id
