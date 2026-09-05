import logging
from collections.abc import Callable
from datetime import date as Date
from datetime import datetime
from typing import Literal

from langchain_core.tools import BaseTool, tool
from pydantic import AwareDatetime, BaseModel, Field, ValidationError

from app.config import OFFICE_TZ
from app.domain.booking import Booking
from app.domain.exceptions import DomainError
from app.domain.time_range import TimeRange
from app.services.booking_service import BookingService


logger = logging.getLogger(__name__)

RoomName = Literal["A", "B", "C", "D", "E"]
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
    @tool
    def list_my_bookings() -> str:
        """Use when the user asks to see or recall their active bookings."""

        def action() -> str:
            bookings = service.list_my_bookings(user_id)
            if not bookings:
                return _success("Result: No active bookings.")

            lines = ["Result: Active bookings"]
            for booking in bookings:
                lines.extend(_booking_lines(booking))
            return _success(*lines)

        return _execute_tool("list_my_bookings", {}, action)

    @tool(args_schema=CreateBookingInput)
    def create_booking(
        room: str,
        starts_at: datetime,
        ends_at: datetime,
        title: str,
        attendees: int,
    ) -> str:
        """Use only after the user explicitly confirms all booking details."""
        arguments = {
            "room": room,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "title": title,
            "attendees": attendees,
        }

        def action() -> str:
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
            return _success("Result: Booking created", *_booking_lines(booking))

        return _execute_tool("create_booking", arguments, action)

    @tool(args_schema=ListAvailableRoomsInput)
    def list_available_rooms(
        starts_at: datetime,
        ends_at: datetime,
        attendees: int,
    ) -> str:
        """Use when the user asks which rooms are free for a complete range."""
        arguments = {
            "starts_at": starts_at,
            "ends_at": ends_at,
            "attendees": attendees,
        }

        def action() -> str:
            time_range = TimeRange(
                starts_at=starts_at.astimezone(OFFICE_TZ),
                ends_at=ends_at.astimezone(OFFICE_TZ),
            )
            rooms = service.list_available_rooms(time_range, attendees)
            request_line = f"Requested time: {_format_range(time_range)}"
            attendee_line = f"Attendees: {attendees}"

            if not rooms:
                return _success(
                    "Result: No rooms are available for the full range.",
                    request_line,
                    attendee_line,
                )

            room_lines = [
                f"Room {room.name}: capacity {room.capacity}"
                for room in rooms
            ]
            return _success(
                "Result: Rooms available for the full range",
                request_line,
                attendee_line,
                *room_lines,
            )

        return _execute_tool("list_available_rooms", arguments, action)

    @tool(args_schema=GetRoomScheduleInput)
    def get_room_schedule(room: str, date: Date) -> str:
        """Use when the user asks for the occupied and free times of one room."""
        arguments = {"room": room, "date": date}

        def action() -> str:
            taken_ranges, free_ranges = service.get_room_schedule(room, date)
            return _success(
                "Result: Room schedule",
                f"Room: {room}",
                f"Date: {date.isoformat()}",
                "Taken ranges:",
                *_range_lines(taken_ranges),
                "Free ranges:",
                *_range_lines(free_ranges),
            )

        return _execute_tool("get_room_schedule", arguments, action)

    @tool(args_schema=CancelBookingInput)
    def cancel_booking(booking_id: int) -> str:
        """Use when the user asks to cancel a booking identified from their list."""
        arguments = {"booking_id": booking_id}

        def action() -> str:
            service.cancel_booking(user_id=user_id, booking_id=booking_id)
            return _success(
                "Result: Booking cancelled",
                f"Booking ID: {booking_id}",
            )

        return _execute_tool("cancel_booking", arguments, action)

    built_tools = [
        list_my_bookings,
        create_booking,
        list_available_rooms,
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
    action: Callable[[], str],
) -> str:
    logger.info("Tool call name=%s arguments=%s", name, arguments)

    try:
        result = action()
    except DomainError as error:
        result = _error(str(error))
    except Exception:
        logger.exception("Unexpected error in tool name=%s", name)
        result = _error(
            "Something went wrong while processing the request. Try again."
        )

    summary = result.splitlines()[1] if "\n" in result else result
    logger.info("Tool result name=%s summary=%s", name, summary)
    return result


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


def _range_lines(ranges: list[TimeRange]) -> list[str]:
    if not ranges:
        return ["- None"]

    return [f"- {_format_range(time_range)}" for time_range in ranges]


def _format_range(time_range: TimeRange) -> str:
    starts_at = time_range.starts_at.strftime("%Y-%m-%d %H:%M")
    ends_at = time_range.ends_at.strftime("%Y-%m-%d %H:%M")
    return f"{starts_at} to {ends_at}"
