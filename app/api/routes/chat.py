import logging
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)
from langgraph.errors import GraphRecursionError
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.agent.artifacts import (
    PRESENTATION_MODES,
    ROOM_NAMES,
    PresentationMode,
    RoomName,
)
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
    presentation: PresentationMode = "message"
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
    presentation, rooms, bookings = _presentation_from_tool_results(
        result["messages"]
    )

    return ChatResponse(
        response=response_text,
        presentation=presentation,
        rooms=rooms,
        bookings=bookings,
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


def _presentation_from_tool_results(
    messages: list[BaseMessage],
) -> tuple[PresentationMode, list[RoomName], list[BookingSummary]]:
    presentation: PresentationMode = "message"
    rooms: list[RoomName] = []
    bookings: list[BookingSummary] = []

    for message in messages:
        if not isinstance(message, ToolMessage):
            continue

        artifact = message.artifact
        if not isinstance(artifact, dict):
            continue

        artifact_presentation = artifact.get("presentation")
        if artifact_presentation not in PRESENTATION_MODES:
            continue

        presentation = cast(PresentationMode, artifact_presentation)
        rooms = []
        bookings = []

        if presentation == "room_gallery":
            rooms = [
                room
                for room in artifact.get("rooms", [])
                if room in ROOM_NAMES
            ]
        elif presentation == "booking_list":
            for booking in artifact.get("bookings", []):
                try:
                    bookings.append(BookingSummary.model_validate(booking))
                except ValidationError:
                    logger.warning("Ignored malformed booking artifact")

    return presentation, rooms, bookings
