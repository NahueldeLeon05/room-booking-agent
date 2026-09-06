from typing import Literal, TypedDict


RoomName = Literal["A", "B", "C", "D", "E"]
PresentationMode = Literal["message", "room_gallery", "booking_list"]
ROOM_NAMES: frozenset[RoomName] = frozenset({"A", "B", "C", "D", "E"})
PRESENTATION_MODES: frozenset[PresentationMode] = frozenset(
    {"message", "room_gallery", "booking_list"}
)


class BookingArtifact(TypedDict):
    booking_id: int
    room: RoomName
    title: str
    attendees: int
    time: str


class PresentationArtifact(TypedDict):
    presentation: PresentationMode
    rooms: list[RoomName]
    bookings: list[BookingArtifact]


def presentation_artifact(
    presentation: PresentationMode = "message",
    *,
    rooms: list[RoomName] | None = None,
    bookings: list[BookingArtifact] | None = None,
) -> PresentationArtifact:
    return {
        "presentation": presentation,
        "rooms": list(rooms or []),
        "bookings": list(bookings or []),
    }
