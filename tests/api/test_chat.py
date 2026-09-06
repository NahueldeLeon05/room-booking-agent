from unittest.mock import Mock

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.orm import Session

import app.api.routes.chat as chat_module
from app.api.routes.chat import (
    ChatHistoryMessage,
    ChatRequest,
    _build_messages,
)
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
    graph.invoke.assert_called_once()
    assert graph.invoke.call_args.kwargs["config"] == {"max_concurrency": 1}
