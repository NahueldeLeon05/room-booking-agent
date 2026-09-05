from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.infrastructure.models import BookingModel, RoomModel, UserModel


def test_listing_bookings_without_token_is_rejected(
    client: TestClient,
) -> None:
    response = client.get("/bookings/me")

    assert response.status_code == 401


def test_user_only_sees_their_own_bookings(
    client: TestClient,
    db_engine: Engine,
) -> None:
    _add_booking(
        db_engine,
        username="User1",
        room_name="A",
        title="User 1 planning",
        status="active",
    )
    _add_booking(
        db_engine,
        username="User2",
        room_name="B",
        title="User 2 planning",
        status="active",
    )

    user_1_response = client.get(
        "/bookings/me",
        headers=_authorization_header(client, "User1"),
    )
    user_2_response = client.get(
        "/bookings/me",
        headers=_authorization_header(client, "User2"),
    )

    assert user_1_response.status_code == 200
    assert [item["title"] for item in user_1_response.json()] == [
        "User 1 planning"
    ]
    assert user_2_response.status_code == 200
    assert [item["title"] for item in user_2_response.json()] == [
        "User 2 planning"
    ]


def test_cancelled_bookings_are_not_listed(
    client: TestClient,
    db_engine: Engine,
) -> None:
    _add_booking(
        db_engine,
        username="User1",
        room_name="A",
        title="Active booking",
        status="active",
    )
    _add_booking(
        db_engine,
        username="User1",
        room_name="B",
        title="Cancelled booking",
        status="cancelled",
    )

    response = client.get(
        "/bookings/me",
        headers=_authorization_header(client, "User1"),
    )

    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == ["Active booking"]


def _authorization_header(
    client: TestClient,
    username: str,
) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": "test-password"},
    )
    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


def _add_booking(
    db_engine: Engine,
    username: str,
    room_name: str,
    title: str,
    status: str,
) -> None:
    with Session(bind=db_engine) as session:
        user = session.scalar(
            select(UserModel).where(UserModel.username == username)
        )
        room = session.scalar(
            select(RoomModel).where(RoomModel.name == room_name)
        )
        assert user is not None
        assert room is not None

        session.add(
            BookingModel(
                room_id=room.id,
                user_id=user.id,
                title=title,
                attendees=2,
                starts_at=datetime(2026, 9, 7, 10, 0),
                ends_at=datetime(2026, 9, 7, 11, 0),
                status=status,
                created_at=datetime(2026, 9, 5, 12, 0),
            )
        )
        session.commit()
