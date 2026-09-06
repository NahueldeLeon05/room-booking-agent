from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

import app.api.routes.chat as chat_module
from app.config import MAX_MESSAGE_LENGTH


def test_message_exceeding_length_limit_is_rejected(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    build_graph = Mock()
    monkeypatch.setattr(chat_module, "build_graph", build_graph)

    response = client.post(
        "/chat",
        json={"message": "x" * (MAX_MESSAGE_LENGTH + 1), "history": []},
        headers=_authorization_header(client),
    )

    assert response.status_code == 422
    assert str(MAX_MESSAGE_LENGTH) in response.text
    build_graph.assert_not_called()


def test_history_can_contain_more_than_twenty_messages(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = Mock()
    graph.invoke.return_value = {
        "messages": [AIMessage(content="Seguimos conversando.")]
    }
    monkeypatch.setattr(
        chat_module,
        "build_graph",
        lambda service, user_id: graph,
    )
    history = [
        {"role": "user", "content": "Hola."}
        for _ in range(21)
    ]

    response = client.post(
        "/chat",
        json={"message": "Hola.", "history": history},
        headers=_authorization_header(client),
    )

    assert response.status_code == 200
    sent_messages = graph.invoke.call_args.args[0]["messages"]
    assert len(sent_messages) == 22
    history_schema = chat_module.ChatRequest.model_json_schema()[
        "properties"
    ]["history"]
    assert "maxItems" not in history_schema


def test_message_within_limits_is_accepted(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = Mock()
    graph.invoke.return_value = {
        "messages": [AIMessage(content="Soy CUBO. ¿En qué puedo ayudarte?")]
    }
    monkeypatch.setattr(
        chat_module,
        "build_graph",
        lambda service, user_id: graph,
    )

    response = client.post(
        "/chat",
        json={"message": "x" * MAX_MESSAGE_LENGTH, "history": []},
        headers=_authorization_header(client),
    )

    assert response.status_code == 200
    assert response.json() == {
        "response": "Soy CUBO. ¿En qué puedo ayudarte?",
        "presentation": "message",
        "rooms": [],
        "bookings": [],
    }
    graph.invoke.assert_called_once()


def test_history_message_exceeding_length_limit_is_rejected(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    build_graph = Mock()
    monkeypatch.setattr(chat_module, "build_graph", build_graph)

    response = client.post(
        "/chat",
        json={
            "message": "Hola.",
            "history": [
                {
                    "role": "user",
                    "content": "x" * (MAX_MESSAGE_LENGTH + 1),
                }
            ],
        },
        headers=_authorization_header(client),
    )

    assert response.status_code == 422
    assert str(MAX_MESSAGE_LENGTH) in response.text
    build_graph.assert_not_called()


def _authorization_header(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": "User1", "password": "test-password"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
