import json
from contextlib import nullcontext
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError

from ui import app


def _validation_http_error(
    location: str,
    max_length: int,
) -> HTTPError:
    body = {
        "detail": [
            {
                "type": "too_long",
                "loc": ["body", location],
                "msg": "Value exceeds the maximum length",
                "ctx": {"max_length": max_length},
            }
        ]
    }
    return HTTPError(
        url="http://api/chat",
        code=422,
        msg="Unprocessable Entity",
        hdrs=None,
        fp=BytesIO(json.dumps(body).encode("utf-8")),
    )


def test_message_length_error_shows_the_allowed_limit() -> None:
    error = _validation_http_error("message", 2000)

    message = app._http_error_message(error)

    assert message == "El mensaje puede tener como máximo 2000 caracteres."


def test_history_length_error_shows_the_allowed_limit() -> None:
    error = _validation_http_error("history", 20)

    message = app._http_error_message(error)

    assert message == "El historial puede tener como máximo 20 mensajes."


def test_rejected_message_is_not_kept_in_chat_history() -> None:
    session_state = SimpleNamespace(token="token", messages=[])
    api_error = app.ApiError(
        "El mensaje puede tener como máximo 2000 caracteres.",
        status_code=422,
    )

    with (
        patch.object(app.st, "session_state", session_state),
        patch.object(
            app.st,
            "columns",
            return_value=(nullcontext(), nullcontext()),
        ),
        patch.object(app.st, "button", return_value=False),
        patch.object(app.st, "chat_input", return_value="a" * 2001),
        patch.object(app.st, "chat_message", return_value=nullcontext()),
        patch.object(app.st, "spinner", return_value=nullcontext()),
        patch.object(app.st, "title"),
        patch.object(app.st, "caption"),
        patch.object(app.st, "markdown"),
        patch.object(app.st, "error") as show_error,
        patch.object(app, "_post", side_effect=api_error),
    ):
        app._show_chat()

    assert session_state.messages == []
    show_error.assert_called_once_with(str(api_error))
