import logging
from collections.abc import Callable
from datetime import date as Date
from datetime import datetime
from typing import cast

from langchain_core.tools import BaseTool, tool
from pydantic import AwareDatetime, BaseModel, Field, ValidationError

from app.agent.artifacts import (
    BookingArtifact,
    PresentationArtifact,
    RoomName,
    presentation_artifact,
)
from app.config import OFFICE_TZ, ROOM_CAPACITIES
from app.domain.booking import Booking
from app.domain.exceptions import DomainError
from app.domain.time_range import TimeRange
from app.services.booking_service import BookingService


logger = logging.getLogger(__name__)

ToolOutput = tuple[str, PresentationArtifact]
DATETIME_DESCRIPTION = (
    "ISO 8601 date and time in YYYY-MM-DDTHH:MM:SS-03:00 format, for example "
    "2026-09-07T10:00:00-03:00. It must align to a 30-minute slot, at :00 or "
    ":30, with seconds and microseconds set to zero."
)


class CreateBookingInput(BaseModel):
    room: RoomName = Field(
        description="One room written as a single uppercase letter from A to E."
    )
    starts_at: AwareDatetime = Field(description=DATETIME_DESCRIPTION)
    ends_at: AwareDatetime = Field(description=DATETIME_DESCRIPTION)
    title: str = Field(description="Short title provided by the user.")
    attendees: int = Field(
        description="Total number of people attending the meeting."
    )


class ListAvailableRoomsInput(BaseModel):
    starts_at: AwareDatetime = Field(description=DATETIME_DESCRIPTION)
    ends_at: AwareDatetime = Field(description=DATETIME_DESCRIPTION)
    attendees: int = Field(
        description="Total number of people who need space in the room."
    )


class CheckRoomAvailabilityInput(ListAvailableRoomsInput):
    room: RoomName = Field(
        description="The room already selected by the user."
    )


class GetRoomDetailsInput(BaseModel):
    room: RoomName = Field(
        description="One room written as a single uppercase letter from A to E."
    )


class GetRoomScheduleInput(BaseModel):
    room: RoomName = Field(
        description="One room written as a single uppercase letter from A to E."
    )
    date: Date = Field(
        description=(
            "ISO 8601 date in YYYY-MM-DD format, for example 2026-09-07."
        )
    )


class CancelBookingInput(BaseModel):
    booking_id: int = Field(
        description=(
            "Existing booking ID obtained from list_my_bookings. Never invent "
            "or guess this value."
        )
    )


def build_tools(service: BookingService, user_id: int) -> list[BaseTool]:
    @tool(response_format="content_and_artifact")
    def list_rooms() -> ToolOutput:
        """Use when the user asks which rooms exist or wants the catalog."""

        def action() -> ToolOutput:
            room_lines = [
                f"Room {name}: capacity {capacity}"
                for name, capacity in ROOM_CAPACITIES.items()
            ]
            return (
                _success("Result: Meeting rooms", *room_lines),
                presentation_artifact(
                    "room_gallery",
                    rooms=[cast(RoomName, name) for name in ROOM_CAPACITIES],
                ),
            )

        return _execute_tool("list_rooms", {}, action)

    @tool(
        args_schema=GetRoomDetailsInput,
        response_format="content_and_artifact",
    )
    def get_room_details(room: str) -> ToolOutput:
        """Use when the user asks to see or learn about one specific room."""

        def action() -> ToolOutput:
            return (
                _success(
                    "Result: Room details",
                    f"Room {room}: capacity {ROOM_CAPACITIES[room]}",
                ),
                presentation_artifact(
                    "room_gallery",
                    rooms=[cast(RoomName, room)],
                ),
            )

        return _execute_tool("get_room_details", {"room": room}, action)

    @tool(response_format="content_and_artifact")
    def list_my_bookings() -> ToolOutput:
        """Use when the user asks to see or recall their active bookings."""

        def action() -> ToolOutput:
            bookings = service.list_my_bookings(user_id)
            if not bookings:
                return (
                    _success("Result: No active bookings."),
                    presentation_artifact("booking_list"),
                )

            lines = ["Result: Active bookings"]
            for booking in bookings:
                lines.extend(_booking_lines(booking))
            return (
                _success(*lines),
                presentation_artifact(
                    "booking_list",
                    bookings=[
                        _booking_artifact(booking) for booking in bookings
                    ],
                ),
            )

        return _execute_tool("list_my_bookings", {}, action)

    @tool(
        args_schema=CreateBookingInput,
        response_format="content_and_artifact",
    )
    def create_booking(
        room: str,
        starts_at: datetime,
        ends_at: datetime,
        title: str,
        attendees: int,
    ) -> ToolOutput:
        """Use only after the user explicitly confirms all booking details."""
        arguments = {
            "room": room,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "title": title,
            "attendees": attendees,
        }

        def action() -> ToolOutput:
            office_start = starts_at.astimezone(OFFICE_TZ)
            office_end = ends_at.astimezone(OFFICE_TZ)
            booking = service.create_booking(
                user_id=user_id,
                room_name=room,
                starts_at=office_start,
                ends_at=office_end,
                title=title,
                attendees=attendees,
            )
            return (
                _success(
                    "Result: Booking created",
                    *_booking_lines(booking),
                ),
                presentation_artifact(),
            )

        return _execute_tool("create_booking", arguments, action)

    @tool(
        args_schema=ListAvailableRoomsInput,
        response_format="content_and_artifact",
    )
    def list_available_rooms(
        starts_at: datetime,
        ends_at: datetime,
        attendees: int,
    ) -> ToolOutput:
        """Use to discover free rooms before the user selects one."""
        arguments = {
            "starts_at": starts_at,
            "ends_at": ends_at,
            "attendees": attendees,
        }

        def action() -> ToolOutput:
            time_range = TimeRange(
                starts_at=starts_at.astimezone(OFFICE_TZ),
                ends_at=ends_at.astimezone(OFFICE_TZ),
            )
            rooms = service.list_available_rooms(time_range, attendees)
            request_line = f"Requested time: {_format_range(time_range)}"
            attendee_line = f"Attendees: {attendees}"

            if not rooms:
                return (
                    _success(
                        "Result: No rooms are available for the full range.",
                        request_line,
                        attendee_line,
                    ),
                    presentation_artifact(),
                )

            room_lines = [
                f"Room {room.name}: capacity {room.capacity}"
                for room in rooms
            ]
            return (
                _success(
                    "Result: Rooms available for the full range",
                    request_line,
                    attendee_line,
                    *room_lines,
                ),
                presentation_artifact(
                    "room_gallery",
                    rooms=[cast(RoomName, room.name) for room in rooms],
                ),
            )

        return _execute_tool("list_available_rooms", arguments, action)

    @tool(
        args_schema=CheckRoomAvailabilityInput,
        response_format="content_and_artifact",
    )
    def check_room_availability(
        room: str,
        starts_at: datetime,
        ends_at: datetime,
        attendees: int,
    ) -> ToolOutput:
        """Use to verify an exact room the user has already selected."""
        arguments = {
            "room": room,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "attendees": attendees,
        }

        def action() -> ToolOutput:
            time_range = TimeRange(
                starts_at=starts_at.astimezone(OFFICE_TZ),
                ends_at=ends_at.astimezone(OFFICE_TZ),
            )
            available_rooms = service.list_available_rooms(
                time_range,
                attendees,
            )
            available_names = [
                cast(RoomName, available_room.name)
                for available_room in available_rooms
            ]
            request_lines = [
                f"Selected room: {room}",
                f"Requested time: {_format_range(time_range)}",
                f"Attendees: {attendees}",
            ]

            if room in available_names:
                return (
                    _success(
                        "Result: Selected room is available",
                        *request_lines,
                    ),
                    presentation_artifact(),
                )

            alternatives = [
                available_room
                for available_room in available_rooms
                if available_room.name != room
            ]
            alternative_lines = [
                f"Room {available_room.name}: "
                f"capacity {available_room.capacity}"
                for available_room in alternatives
            ]
            return (
                _success(
                    "Result: Selected room is not available",
                    *request_lines,
                    "Available alternatives:",
                    *alternative_lines,
                ),
                presentation_artifact(
                    "room_gallery" if alternatives else "message",
                    rooms=[
                        cast(RoomName, available_room.name)
                        for available_room in alternatives
                    ],
                ),
            )

        return _execute_tool(
            "check_room_availability",
            arguments,
            action,
        )

    @tool(
        args_schema=GetRoomScheduleInput,
        response_format="content_and_artifact",
    )
    def get_room_schedule(room: str, date: Date) -> ToolOutput:
        """Use when the user asks for the occupied and free times of one room."""
        arguments = {"room": room, "date": date}

        def action() -> ToolOutput:
            taken_ranges, free_ranges = service.get_room_schedule(room, date)
            return (
                _success(
                    "Result: Room schedule",
                    f"Room: {room}",
                    f"Date: {date.isoformat()}",
                    "Taken ranges:",
                    *_range_lines(taken_ranges),
                    "Free ranges:",
                    *_range_lines(free_ranges),
                ),
                presentation_artifact(),
            )

        return _execute_tool("get_room_schedule", arguments, action)

    @tool(
        args_schema=CancelBookingInput,
        response_format="content_and_artifact",
    )
    def cancel_booking(booking_id: int) -> ToolOutput:
        """Use only after the user confirms cancelling an identified booking."""
        arguments = {"booking_id": booking_id}

        def action() -> ToolOutput:
            service.cancel_booking(user_id=user_id, booking_id=booking_id)
            return (
                _success(
                    "Result: Booking cancelled",
                    f"Booking ID: {booking_id}",
                ),
                presentation_artifact(),
            )

        return _execute_tool("cancel_booking", arguments, action)

    built_tools = [
        list_rooms,
        get_room_details,
        list_my_bookings,
        create_booking,
        list_available_rooms,
        check_room_availability,
        get_room_schedule,
        cancel_booking,
    ]
    for built_tool in built_tools:
        built_tool.handle_validation_error = _validation_error_handler(
            built_tool.name
        )

    return built_tools


def _execute_tool(
    name: str,
    arguments: dict[str, object],
    action: Callable[[], ToolOutput],
) -> ToolOutput:
    logger.info("Tool call name=%s arguments=%s", name, arguments)

    try:
        content, artifact = action()
    except DomainError as error:
        content = _error(str(error))
        artifact = presentation_artifact()
    except Exception:
        logger.exception("Unexpected error in tool name=%s", name)
        content = _error(
            "Something went wrong while processing the request. Try again."
        )
        artifact = presentation_artifact()

    summary = content.splitlines()[1] if "\n" in content else content
    logger.info("Tool result name=%s summary=%s", name, summary)
    return content, artifact


def _validation_error_handler(
    name: str,
) -> Callable[[ValidationError], str]:
    def handle(error: ValidationError) -> str:
        logger.info(
            "Tool call name=%s arguments=invalid validation=%s",
            name,
            error.errors(include_url=False),
        )
        result = _error(
            f"Invalid arguments for {name}. Use the formats described in the "
            "tool schema and try again."
        )
        logger.info(
            "Tool result name=%s summary=argument validation failed",
            name,
        )
        return result

    return handle


def _success(*lines: str) -> str:
    return "\n".join(["Status: success", *lines])


def _error(message: str) -> str:
    return "\n".join(["Status: error", f"Message: {message}"])


def _booking_lines(booking: Booking) -> list[str]:
    return [
        f"Booking ID: {booking.id}",
        f"Room: {booking.room_name}",
        f"Title: {booking.title}",
        f"Attendees: {booking.attendees}",
        f"Time: {_format_range(booking.time_range)}",
    ]


def _booking_artifact(booking: Booking) -> BookingArtifact:
    return {
        "booking_id": booking.id,
        "room": cast(RoomName, booking.room_name),
        "title": booking.title,
        "attendees": booking.attendees,
        "time": _format_range(booking.time_range),
    }


def _range_lines(ranges: list[TimeRange]) -> list[str]:
    if not ranges:
        return ["- None"]

    return [f"- {_format_range(time_range)}" for time_range in ranges]


def _format_range(time_range: TimeRange) -> str:
    starts_at = time_range.starts_at.strftime("%Y-%m-%d %H:%M")
    ends_at = time_range.ends_at.strftime("%Y-%m-%d %H:%M")
    return f"{starts_at} to {ends_at}"
