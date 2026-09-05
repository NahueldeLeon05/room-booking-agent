from collections.abc import Generator
from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import OFFICE_TZ
from app.domain.exceptions import NonWorkingDay, RoomCapacityExceeded
from app.domain.time_range import TimeRange
from app.infrastructure.database import init_db
from app.infrastructure.models import UserModel
from app.infrastructure.repositories.booking_repository import BookingRepository
from app.infrastructure.seed import seed
from app.services.booking_service import BookingService


NOW = datetime(2026, 9, 7, 9, 0, tzinfo=OFFICE_TZ)


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


def test_rooms_occupied_for_part_of_the_range_are_excluded(
    service_and_session: tuple[BookingService, Session],
) -> None:
    service, session = service_and_session
    _create_booking(service, session, "A", _at(10, 30), _at(11, 30))

    rooms = service.list_available_rooms(
        TimeRange(_at(11, 0), _at(12, 0)),
        attendees=2,
    )

    assert [room.name for room in rooms] == ["B", "C", "D", "E"]


def test_room_free_for_the_whole_range_is_included(
    service_and_session: tuple[BookingService, Session],
) -> None:
    service, session = service_and_session
    _create_booking(service, session, "A", _at(10, 0), _at(10, 30))

    rooms = service.list_available_rooms(
        TimeRange(_at(10, 30), _at(11, 0)),
        attendees=2,
    )

    assert "A" in [room.name for room in rooms]


def test_rooms_below_required_capacity_are_excluded(
    service_and_session: tuple[BookingService, Session],
) -> None:
    service, _ = service_and_session

    rooms = service.list_available_rooms(
        TimeRange(_at(10, 0), _at(11, 0)),
        attendees=7,
    )

    assert [room.name for room in rooms] == ["C", "D", "E"]


def test_request_exceeding_building_capacity_is_rejected(
    service_and_session: tuple[BookingService, Session],
) -> None:
    service, _ = service_and_session

    with pytest.raises(RoomCapacityExceeded, match="20"):
        service.list_available_rooms(
            TimeRange(_at(10, 0), _at(11, 0)),
            attendees=21,
        )


def test_availability_on_a_weekend_is_rejected(
    service_and_session: tuple[BookingService, Session],
) -> None:
    service, _ = service_and_session
    saturday = TimeRange(
        datetime(2026, 9, 12, 10, 0, tzinfo=OFFICE_TZ),
        datetime(2026, 9, 12, 11, 0, tzinfo=OFFICE_TZ),
    )

    with pytest.raises(NonWorkingDay):
        service.list_available_rooms(saturday, attendees=2)


def test_room_schedule_returns_merged_taken_and_free_ranges(
    service_and_session: tuple[BookingService, Session],
) -> None:
    service, session = service_and_session
    _create_booking(service, session, "A", _at(10, 0), _at(11, 0))
    _create_booking(service, session, "A", _at(11, 0), _at(11, 30))
    _create_booking(service, session, "A", _at(15, 0), _at(15, 30))

    taken_ranges, free_ranges = service.get_room_schedule(
        "A",
        NOW.date(),
    )

    assert taken_ranges == [
        TimeRange(_at(10, 0), _at(11, 30)),
        TimeRange(_at(15, 0), _at(15, 30)),
    ]
    assert free_ranges == [
        TimeRange(_at(8, 0), _at(10, 0)),
        TimeRange(_at(11, 30), _at(15, 0)),
        TimeRange(_at(15, 30), _at(20, 0)),
    ]


def _create_booking(
    service: BookingService,
    session: Session,
    room_name: str,
    starts_at: datetime,
    ends_at: datetime,
) -> None:
    service.create_booking(
        user_id=_user_id(session),
        room_name=room_name,
        title="Planning",
        attendees=2,
        starts_at=starts_at,
        ends_at=ends_at,
    )


def _user_id(session: Session) -> int:
    user_id = session.scalar(
        select(UserModel.id).where(UserModel.username == "User1")
    )
    assert user_id is not None
    return user_id


def _at(hour: int, minute: int) -> datetime:
    return datetime(2026, 9, 7, hour, minute, tzinfo=OFFICE_TZ)
