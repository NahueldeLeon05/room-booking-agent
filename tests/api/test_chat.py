from langchain_core.messages import AIMessage, HumanMessage

from app.api.routes.chat import (
    ChatHistoryMessage,
    ChatRequest,
    _build_messages,
)


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
