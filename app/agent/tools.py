from langchain_core.tools import BaseTool, tool

from app.services.booking_service import BookingService


def build_tools(service: BookingService, user_id: int) -> list[BaseTool]:
    @tool
    def list_my_bookings() -> str:
        """Use when the user asks to see or recall their active bookings."""
        bookings = service.list_my_bookings(user_id)

        if not bookings:
            return "The authenticated user has no active bookings."

        lines = ["The authenticated user's active bookings are:"]
        for booking in bookings:
            starts_at = booking.time_range.starts_at.strftime("%Y-%m-%d %H:%M")
            ends_at = booking.time_range.ends_at.strftime("%Y-%m-%d %H:%M")
            lines.append(
                f'- Booking ID {booking.id}: "{booking.title}" in room '
                f"{booking.room_name}, for {booking.attendees} attendees, "
                f"from {starts_at} to {ends_at}."
            )

        return "\n".join(lines)

    return [list_my_bookings]
