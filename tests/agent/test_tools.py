import logging
from datetime import date, datetime

import pytest
from langchain_core.tools import BaseTool

from app.agent.tools import build_tools
from app.config import OFFICE_TZ
from app.domain.booking import Booking
from app.domain.exceptions import RoomNotFound
from app.domain.room import Room
from app.domain.time_range import TimeRange


class FakeBookingService:
    def __init__(self) -> None:
        self.created_for_user: int | None = None
        self.cancelled_for_user: int | None = None

    def list_my_bookings(self, user_id: int) -> list[Booking]:
        return [_booking(user_id)]

    def create_booking(
        self,
        user_id: int,
        room_name: str,
        title: str,
        attendees: int,
        starts_at: datetime,
        ends_at: datetime,
    ) -> Booking:
        self.created_for_user = user_id
        return Booking(
            id=7,
            room_name=room_name,
            user_id=user_id,
            title=title,
            attendees=attendees,
            time_range=TimeRange(starts_at, ends_at),
            status="active",
        )

    def list_available_rooms(
        self,
        time_range: TimeRange,
        attendees: int,
    ) -> list[Room]:
        return [Room(id=1, name="A", capacity=4)]

    def get_room_schedule(
        self,
        room_name: str,
        day: date,
    ) -> tuple[list[TimeRange], list[TimeRange]]:
        return (
            [TimeRange(_at(10, 0), _at(11, 30))],
            [
                TimeRange(_at(8, 0), _at(10, 0)),
                TimeRange(_at(11, 30), _at(20, 0)),
            ],
        )

    def cancel_booking(self, user_id: int, booking_id: int) -> None:
        self.cancelled_for_user = user_id


def test_tool_schemas_do_not_expose_user_id() -> None:
    tools = build_tools(FakeBookingService(), user_id=42)

    assert {built_tool.name for built_tool in tools} == {
        "list_rooms",
        "get_room_details",
        "list_my_bookings",
        "create_booking",
        "list_available_rooms",
        "get_room_schedule",
        "cancel_booking",
    }
    for built_tool in tools:
        properties = built_tool.args_schema.model_json_schema().get(
            "properties",
            {},
        )
        assert "user_id" not in properties


def test_tool_schemas_explain_the_model_facing_formats() -> None:
    tools = {
        built_tool.name: built_tool
        for built_tool in build_tools(FakeBookingService(), user_id=42)
    }
    create_properties = tools[
        "create_booking"
    ].args_schema.model_json_schema()["properties"]
    schedule_properties = tools[
        "get_room_schedule"
    ].args_schema.model_json_schema()["properties"]
    cancel_properties = tools[
        "cancel_booking"
    ].args_schema.model_json_schema()["properties"]

    assert "2026-09-07T10:00:00-03:00" in create_properties[
        "starts_at"
    ]["description"]
    assert "30-minute slot" in create_properties["ends_at"]["description"]
    assert create_properties["room"]["enum"] == ["A", "B", "C", "D", "E"]
    assert "2026-09-07" in schedule_properties["date"]["description"]
    assert "list_my_bookings" in cancel_properties[
        "booking_id"
    ]["description"]


def test_invalid_tool_arguments_are_returned_as_plain_text() -> None:
    service = FakeBookingService()
    create_booking = _tool_named(service, "create_booking", user_id=42)

    result = create_booking.invoke(
        {
            "room": "Z",
            "starts_at": "2026-09-07T10:00:00-03:00",
            "ends_at": "2026-09-07T11:30:00-03:00",
            "title": "Planning",
            "attendees": 4,
        }
    )

    assert result.startswith("Status: error")
    assert "Invalid arguments for create_booking" in result


def test_create_booking_uses_authenticated_user_and_returns_booking_id() -> None:
    service = FakeBookingService()
    create_booking = _tool_named(service, "create_booking", user_id=42)

    result = create_booking.invoke(
        {
            "room": "A",
            "starts_at": "2026-09-07T10:00:00-03:00",
            "ends_at": "2026-09-07T11:30:00-03:00",
            "title": "Planning",
            "attendees": 4,
        }
    )

    assert service.created_for_user == 42
    assert "Status: success" in result
    assert "Booking ID: 7" in result


def test_list_my_bookings_returns_booking_id() -> None:
    service = FakeBookingService()
    list_my_bookings = _tool_named(
        service,
        "list_my_bookings",
        user_id=42,
    )

    result = list_my_bookings.invoke({})

    assert "Status: success" in result
    assert "Booking ID: 7" in result


def test_list_rooms_returns_the_configured_catalog() -> None:
    service = FakeBookingService()
    list_rooms = _tool_named(service, "list_rooms", user_id=42)

    result = list_rooms.invoke({})

    assert "Status: success" in result
    assert "Result: Meeting rooms" in result
    assert "Room A: capacity 4" in result
    assert "Room E: capacity 20" in result


def test_get_room_details_returns_only_the_requested_room() -> None:
    service = FakeBookingService()
    get_room_details = _tool_named(service, "get_room_details", user_id=42)

    result = get_room_details.invoke({"room": "C"})

    assert "Status: success" in result
    assert "Result: Room details" in result
    assert "Room C: capacity 8" in result
    assert "Room A:" not in result


def test_cancel_booking_uses_authenticated_user_and_returns_booking_id() -> None:
    service = FakeBookingService()
    cancel_booking = _tool_named(service, "cancel_booking", user_id=42)

    result = cancel_booking.invoke({"booking_id": 7})

    assert service.cancelled_for_user == 42
    assert "Status: success" in result
    assert "Booking ID: 7" in result


def test_domain_errors_are_returned_as_plain_text() -> None:
    service = FakeBookingService()

    def raise_room_not_found(
        room_name: str,
        day: date,
    ) -> tuple[list[TimeRange], list[TimeRange]]:
        raise RoomNotFound(room_name)

    service.get_room_schedule = raise_room_not_found  # type: ignore[method-assign]
    get_room_schedule = _tool_named(
        service,
        "get_room_schedule",
        user_id=42,
    )

    result = get_room_schedule.invoke({"room": "A", "date": "2026-09-07"})

    assert result.startswith("Status: error")
    assert "Room A does not exist" in result


def test_unexpected_errors_are_logged_and_hidden(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = FakeBookingService()

    def raise_unexpected_error(user_id: int) -> list[Booking]:
        raise RuntimeError("database password must stay hidden")

    service.list_my_bookings = raise_unexpected_error  # type: ignore[method-assign]
    list_my_bookings = _tool_named(
        service,
        "list_my_bookings",
        user_id=42,
    )

    with caplog.at_level(logging.INFO, logger="app.agent.tools"):
        result = list_my_bookings.invoke({})

    assert result.startswith("Status: error")
    assert "database password" not in result
    assert "Unexpected error in tool name=list_my_bookings" in caplog.text


def test_room_schedule_returns_grouped_ranges() -> None:
    service = FakeBookingService()
    get_room_schedule = _tool_named(
        service,
        "get_room_schedule",
        user_id=42,
    )

    result = get_room_schedule.invoke({"room": "A", "date": "2026-09-07"})

    assert "Taken ranges:\n- 2026-09-07 10:00 to 2026-09-07 11:30" in result
    assert "Free ranges:\n- 2026-09-07 08:00 to 2026-09-07 10:00" in result


def _tool_named(
    service: FakeBookingService,
    name: str,
    user_id: int,
) -> BaseTool:
    return next(
        built_tool
        for built_tool in build_tools(service, user_id)
        if built_tool.name == name
    )


def _booking(user_id: int) -> Booking:
    return Booking(
        id=7,
        room_name="A",
        user_id=user_id,
        title="Planning",
        attendees=4,
        time_range=TimeRange(_at(10, 0), _at(11, 30)),
        status="active",
    )


def _at(hour: int, minute: int) -> datetime:
    return datetime(2026, 9, 7, hour, minute, tzinfo=OFFICE_TZ)
