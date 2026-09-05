from dataclasses import dataclass

from app.domain.time_range import TimeRange


@dataclass
class Booking:
    id: int
    room_name: str
    user_id: int
    title: str
    attendees: int
    time_range: TimeRange
    status: str
