import json
from contextlib import nullcontext
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch
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
    thinking_placeholder = Mock()
    api_error = app.ApiError(
        "El mensaje puede tener como máximo 2000 caracteres.",
        status_code=422,
    )

    with (
        patch.object(app.st, "session_state", session_state),
        patch.object(app, "_show_topbar", return_value=False),
        patch.object(app, "_show_quick_actions", return_value=None),
        patch.object(app.st, "container", return_value=nullcontext()),
        patch.object(app.st, "chat_input", return_value="a" * 2001),
        patch.object(app.st, "chat_message", return_value=nullcontext()),
        patch.object(app.st, "empty", return_value=thinking_placeholder),
        patch.object(app.st, "markdown"),
        patch.object(app.st, "error") as show_error,
        patch.object(app, "_post", side_effect=api_error),
    ):
        app._show_chat()

    assert session_state.messages == []
    show_error.assert_called_once_with(str(api_error))
    thinking_placeholder.empty.assert_called_once_with()


def test_seeded_user_initials_match_the_displayed_account() -> None:
    assert app._username_initials("User1") == "U1"
    assert app._username_initials("User2") == "U2"


def test_quick_action_returns_its_conversational_prompt() -> None:
    columns = [nullcontext(), nullcontext(), nullcontext()]

    with (
        patch.object(app.st, "container", return_value=nullcontext()),
        patch.object(app.st, "markdown"),
        patch.object(app.st, "columns", return_value=columns),
        patch.object(app.st, "button", side_effect=[False, True, False]),
    ):
        prompt = app._show_quick_actions()

    assert prompt == "Mostrame mis reservas."


def test_first_turn_keeps_messages_in_conversation_order() -> None:
    session_state = SimpleNamespace(
        token="token",
        username="User1",
        messages=[],
    )
    thinking_placeholder = Mock()

    with (
        patch.object(app.st, "session_state", session_state),
        patch.object(app, "_show_topbar", return_value=False),
        patch.object(
            app,
            "_show_quick_actions",
            return_value="Mostrame mis reservas.",
        ),
        patch.object(app.st, "container", return_value=nullcontext()),
        patch.object(app.st, "chat_input", return_value=None),
        patch.object(app.st, "chat_message", return_value=nullcontext()),
        patch.object(app.st, "empty", return_value=thinking_placeholder),
        patch.object(app.st, "markdown"),
        patch.object(
            app,
            "_post",
            return_value={"response": "No tenés reservas activas."},
        ) as post,
        patch.object(app.st, "rerun") as rerun,
    ):
        app._show_chat()

    assert session_state.messages == [
        {"role": "assistant", "content": app.WELCOME_MESSAGE},
        {"role": "user", "content": "Mostrame mis reservas."},
        {"role": "assistant", "content": "No tenés reservas activas."},
    ]
    post.assert_called_once_with(
        "/chat",
        {
            "message": "Mostrame mis reservas.",
            "history": [
                {"role": "assistant", "content": app.WELCOME_MESSAGE}
            ],
        },
        token="token",
    )
    rerun.assert_called_once_with()


def test_stylesheet_is_loaded_from_the_ui_directory() -> None:
    assert app.STYLES_PATH.name == "styles.css"
    assert app.STYLES_PATH.is_file()


def test_brand_logo_is_loaded_from_a_local_asset() -> None:
    assert app.LOGO_PATH.name == "cubo-itau-logo.svg"
    assert app.LOGO_PATH.is_file()
    assert app.CUBO_LOGO_DATA_URI.startswith("data:image/svg+xml;base64,")
    assert "https://" not in app.CUBO_LOGO_HTML
    assert 'aria-label="Cubo Itaú"' in app.CUBO_LOGO_HTML


def test_login_background_video_is_loaded_from_a_local_asset() -> None:
    assert app.LOGIN_VIDEO_PATH.name == "cubo-office-background.mp4"
    assert app.LOGIN_VIDEO_PATH.is_file()


def test_compact_html_preserves_spaces_between_text_lines() -> None:
    markup = "<p>Primera línea.\nSegunda línea.</p>"

    assert app._compact_html(markup) == (
        "<p>Primera línea. Segunda línea.</p>"
    )
