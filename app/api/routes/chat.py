import logging
import re
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)
from langgraph.errors import GraphRecursionError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.graph import build_graph
from app.api.deps import get_current_user
from app.config import (
    AGENT_RECURSION_LIMIT,
    MAX_HISTORY_MESSAGES,
    MAX_MESSAGE_LENGTH,
)
from app.infrastructure.database import get_session
from app.infrastructure.models import UserModel
from app.infrastructure.repositories.booking_repository import BookingRepository
from app.services.booking_service import BookingService


logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])
RoomName = Literal["A", "B", "C", "D", "E"]
ROOM_RESULT_PATTERN = re.compile(
    r"^Room(?::\s*|\s+)([A-E])(?::|$)",
    re.MULTILINE,
)
ROOM_VISUAL_RESULT_MARKERS = (
    "Result: Meeting rooms",
    "Result: Room details",
    "Result: Rooms available for the full range",
)
ROOM_VISUAL_RESET_RESULT_MARKERS = (
    "Result: Booking created",
    "Result: Booking cancelled",
    "Result: Room schedule",
    "Result: Active bookings",
    "Result: No active bookings",
)
BOOKING_RESULT_PATTERN = re.compile(
    r"^Booking ID: (?P<booking_id>\d+)\n"
    r"Room: (?P<room>[A-E])\n"
    r"Title: (?P<title>[^\r\n]+)\n"
    r"Attendees: (?P<attendees>\d+)\n"
    r"Time: (?P<time>[^\r\n]+)",
    re.MULTILINE,
)


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(
        max_length=MAX_MESSAGE_LENGTH,
        description=(
            f"Previous message, limited to {MAX_MESSAGE_LENGTH} characters."
        ),
    )


class ChatRequest(BaseModel):
    message: str = Field(
        max_length=MAX_MESSAGE_LENGTH,
        description=(
            f"New message written by the user, limited to "
            f"{MAX_MESSAGE_LENGTH} characters."
        ),
    )
    history: list[ChatHistoryMessage] = Field(
        default_factory=list,
        max_length=MAX_HISTORY_MESSAGES,
        description=(
            "Previous user and assistant messages in order. The client must "
            f"send them again with every request, up to "
            f"{MAX_HISTORY_MESSAGES} messages."
        ),
    )


class BookingSummary(BaseModel):
    booking_id: int
    room: RoomName
    title: str
    attendees: int
    time: str


class ChatResponse(BaseModel):
    response: str
    # Explicit presentation metadata lets clients render room photos without
    # trying to infer room names from the assistant's natural-language reply.
    rooms: list[RoomName] = Field(default_factory=list)
    bookings: list[BookingSummary] = Field(default_factory=list)


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> ChatResponse:
    repository = BookingRepository(session)
    service = BookingService(repository)
    graph = build_graph(service, current_user.id)
    messages = _build_messages(request)

    # Tool closures share this request's SQLAlchemy Session, which is not
    # thread-safe. Serialize tool calls when the model requests several.
    try:
        result = graph.invoke(
            {"messages": messages},
            config={
                "max_concurrency": 1,
                "recursion_limit": AGENT_RECURSION_LIMIT,
            },
        )
    except GraphRecursionError:
        logger.warning(
            "Agent stopped after reaching recursion limit=%s",
            AGENT_RECURSION_LIMIT,
        )
        return ChatResponse(
            response=(
                "Detuve la solicitud porque tomó demasiados pasos. "
                "Pedime que revise tus reservas antes de intentarlo de nuevo."
            )
        )
    final_message = result["messages"][-1]
    response_text = str(final_message.text)

    return ChatResponse(
        response=response_text,
        rooms=_rooms_from_tool_results(result["messages"]),
        bookings=_bookings_from_tool_results(result["messages"]),
    )


def _build_messages(request: ChatRequest) -> list[BaseMessage]:
    messages: list[BaseMessage] = []

    for message in request.history:
        if message.role == "user":
            messages.append(HumanMessage(content=message.content))
        else:
            messages.append(AIMessage(content=message.content))

    messages.append(HumanMessage(content=request.message))
    return messages


def _rooms_from_tool_results(messages: list[BaseMessage]) -> list[RoomName]:
    rooms: list[RoomName] = []

    for message in messages:
        if not isinstance(message, ToolMessage):
            continue

        result = str(message.text)
        if not result.startswith("Status: success"):
            continue

        if any(
            marker in result
            for marker in ROOM_VISUAL_RESET_RESULT_MARKERS
        ):
            rooms.clear()
            continue

        if not any(
            marker in result for marker in ROOM_VISUAL_RESULT_MARKERS
        ):
            continue

        for matched_room in ROOM_RESULT_PATTERN.findall(result):
            room: RoomName = matched_room
            if room not in rooms:
                rooms.append(room)

    return rooms


def _bookings_from_tool_results(
    messages: list[BaseMessage],
) -> list[BookingSummary]:
    bookings: list[BookingSummary] = []

    for message in messages:
        if not isinstance(message, ToolMessage):
            continue

        result = str(message.text)
        if not (
            result.startswith("Status: success")
            and "Result: Active bookings" in result
        ):
            continue

        for match in BOOKING_RESULT_PATTERN.finditer(result):
            bookings.append(
                BookingSummary(
                    booking_id=int(match.group("booking_id")),
                    room=match.group("room"),
                    title=match.group("title"),
                    attendees=int(match.group("attendees")),
                    time=match.group("time"),
                )
            )

    return bookings
