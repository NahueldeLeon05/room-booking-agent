from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.graph import build_graph
from app.api.deps import get_current_user
from app.infrastructure.database import get_session
from app.infrastructure.models import UserModel
from app.infrastructure.repositories.booking_repository import BookingRepository
from app.services.booking_service import BookingService


router = APIRouter(tags=["chat"])


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(description="New message written by the user.")
    history: list[ChatHistoryMessage] = Field(
        default_factory=list,
        description=(
            "Previous user and assistant messages in order. The client must "
            "send them again with every request."
        ),
    )


class ChatResponse(BaseModel):
    response: str


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

    result = graph.invoke({"messages": messages})
    final_message = result["messages"][-1]

    return ChatResponse(response=str(final_message.text))


def _build_messages(request: ChatRequest) -> list[BaseMessage]:
    messages: list[BaseMessage] = []

    for message in request.history:
        if message.role == "user":
            messages.append(HumanMessage(content=message.content))
        else:
            messages.append(AIMessage(content=message.content))

    messages.append(HumanMessage(content=request.message))
    return messages
