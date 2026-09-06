from unittest.mock import Mock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError
from sqlalchemy.orm import Session

import app.api.routes.chat as chat_module
from app.api.routes.chat import (
    ChatHistoryMessage,
    ChatRequest,
    _bookings_from_tool_results,
    _build_messages,
    _rooms_from_tool_results,
)
from app.config import AGENT_RECURSION_LIMIT
from app.infrastructure.models import UserModel


def test_chat_history_is_sent_before_the_current_message() -> None:
    request = ChatRequest(
        message="Sí, confirmo.",
        history=[
            ChatHistoryMessage(
                role="user",
                content="Quiero reservar la sala A mañana a las 10.",
            ),
            ChatHistoryMessage(
                role="assistant",
                content="¿Confirmás los datos de la reserva?",
            ),
        ],
    )

    messages = _build_messages(request)

    assert [type(message) for message in messages] == [
        HumanMessage,
        AIMessage,
        HumanMessage,
    ]
    assert [message.content for message in messages] == [
        "Quiero reservar la sala A mañana a las 10.",
        "¿Confirmás los datos de la reserva?",
        "Sí, confirmo.",
    ]


def test_chat_runs_tool_calls_sequentially(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = Mock()
    graph.invoke.return_value = {"messages": [AIMessage(content="Listo.")]}
    monkeypatch.setattr(
        chat_module,
        "build_graph",
        lambda service, user_id: graph,
    )

    response = chat_module.chat(
        request=ChatRequest(message="Cancelá mis dos reservas."),
        current_user=UserModel(
            id=1,
            username="User1",
            password_hash="unused",
        ),
        session=Mock(spec=Session),
    )

    assert response.response == "Listo."
    assert response.rooms == []
    assert response.bookings == []
    graph.invoke.assert_called_once()
    assert graph.invoke.call_args.kwargs["config"] == {
        "max_concurrency": 1,
        "recursion_limit": AGENT_RECURSION_LIMIT,
    }


def test_recursion_limit_error_returns_conversational_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = Mock()
    graph.invoke.side_effect = GraphRecursionError("limit reached")
    monkeypatch.setattr(
        chat_module,
        "build_graph",
        lambda service, user_id: graph,
    )

    response = chat_module.chat(
        request=ChatRequest(message="Intentá de nuevo para siempre."),
        current_user=UserModel(
            id=1,
            username="User1",
            password_hash="unused",
        ),
        session=Mock(spec=Session),
    )

    assert response.response == (
        "Detuve la solicitud porque tomó demasiados pasos. "
        "Pedime que revise tus reservas antes de intentarlo de nuevo."
    )


def test_available_rooms_are_extracted_from_a_successful_tool_result() -> None:
    messages = [
        ToolMessage(
            content=(
                "Status: success\n"
                "Result: Rooms available for the full range\n"
                "Room B: capacity 6\n"
                "Room D: capacity 12"
            ),
            tool_call_id="available-rooms",
        ),
    ]

    assert _rooms_from_tool_results(messages) == ["B", "D"]


def test_booking_creation_clears_intermediate_availability_images() -> None:
    messages = [
        ToolMessage(
            content=(
                "Status: success\n"
                "Result: Rooms available for the full range\n"
                "Room B: capacity 6\n"
                "Room D: capacity 12"
            ),
            tool_call_id="available-rooms",
        ),
        ToolMessage(
            content="Status: success\nResult: Booking created\nRoom: B",
            tool_call_id="created-booking",
        ),
    ]

    assert _rooms_from_tool_results(messages) == []


def test_room_schedule_clears_intermediate_room_images() -> None:
    messages = [
        ToolMessage(
            content=(
                "Status: success\n"
                "Result: Room details\n"
                "Room E: capacity 20"
            ),
            tool_call_id="room-details",
        ),
        ToolMessage(
            content=(
                "Status: success\n"
                "Result: Room schedule\n"
                "Room: E\n"
                "Date: 2026-09-07"
            ),
            tool_call_id="room-schedule",
        ),
    ]

    assert _rooms_from_tool_results(messages) == []


def test_room_catalog_results_are_available_for_visual_presentation() -> None:
    messages = [
        ToolMessage(
            content=(
                "Status: success\n"
                "Result: Meeting rooms\n"
                "Room A: capacity 4\n"
                "Room B: capacity 6\n"
                "Room C: capacity 8\n"
                "Room D: capacity 12\n"
                "Room E: capacity 20"
            ),
            tool_call_id="room-catalog",
        )
    ]

    assert _rooms_from_tool_results(messages) == ["A", "B", "C", "D", "E"]


def test_room_details_result_exposes_only_the_requested_room() -> None:
    messages = [
        ToolMessage(
            content=(
                "Status: success\n"
                "Result: Room details\n"
                "Room A: capacity 4"
            ),
            tool_call_id="room-details",
        )
    ]

    assert _rooms_from_tool_results(messages) == ["A"]


def test_active_bookings_are_extracted_for_visual_presentation() -> None:
    messages = [
        ToolMessage(
            content=(
                "Status: success\n"
                "Result: Active bookings\n"
                "Booking ID: 3\n"
                "Room: A\n"
                "Title: Planning\n"
                "Attendees: 4\n"
                "Time: 2026-09-07 10:00 to 2026-09-07 13:00\n"
                "Booking ID: 5\n"
                "Room: C\n"
                "Title: Daily\n"
                "Attendees: 3\n"
                "Time: 2026-09-08 09:00 to 2026-09-08 10:00"
            ),
            tool_call_id="active-bookings",
        )
    ]

    bookings = _bookings_from_tool_results(messages)

    assert [booking.model_dump() for booking in bookings] == [
        {
            "booking_id": 3,
            "room": "A",
            "title": "Planning",
            "attendees": 4,
            "time": "2026-09-07 10:00 to 2026-09-07 13:00",
        },
        {
            "booking_id": 5,
            "room": "C",
            "title": "Daily",
            "attendees": 3,
            "time": "2026-09-08 09:00 to 2026-09-08 10:00",
        },
    ]
