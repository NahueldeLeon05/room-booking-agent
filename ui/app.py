import json
import os
from base64 import b64encode
from html import escape
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
API_TIMEOUT_SECONDS = 120
STYLES_PATH = Path(__file__).with_name("styles.css")
LOGO_PATH = Path(__file__).with_name("assets") / "cubo-itau-logo.svg"
LOGIN_VIDEO_PATH = (
    Path(__file__).with_name("assets") / "cubo-office-background.mp4"
)
_LOGO_SVG = LOGO_PATH.read_text(encoding="utf-8").replace(
    "currentColor",
    "#f7f6f2",
)
CUBO_LOGO_DATA_URI = (
    "data:image/svg+xml;base64,"
    + b64encode(_LOGO_SVG.encode("utf-8")).decode("ascii")
)
CUBO_LOGO_HTML = (
    '<span class="cubo-logo" role="img" aria-label="Cubo Itaú">Cubo Itaú</span>'
)
WELCOME_MESSAGE = (
    "Hola, soy **CUBO**. Puedo buscar salas libres, mostrarte la agenda de "
    "una sala, crear una reserva, listar las que tenés activas o cancelar "
    "alguna. Contame qué necesitás."
)


class ApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


def main() -> None:
    st.set_page_config(
        page_title="CUBO",
        page_icon="◻",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _load_styles()
    _initialize_session()

    if not st.session_state.token:
        _show_login()
        return

    _show_chat()


def _load_styles() -> None:
    styles = STYLES_PATH.read_text(encoding="utf-8").replace(
        "__CUBO_LOGO_DATA_URI__",
        CUBO_LOGO_DATA_URI,
    )
    # CSS-only st.html content is mounted outside the page layout, so loading
    # the stylesheet does not leave an empty block above the interface.
    st.html(f"<style>{styles}</style>")


def _compact_html(markup: str) -> str:
    return " ".join(line.strip() for line in markup.splitlines())


def _initialize_session() -> None:
    if "token" not in st.session_state:
        st.session_state.token = None
    if "username" not in st.session_state:
        st.session_state.username = None
    if "messages" not in st.session_state:
        st.session_state.messages = []


def _show_login() -> None:
    aside_column, form_column = st.columns([45, 55], gap=None)

    with aside_column:
        with st.container(key="cubo_login_aside"):
            st.video(
                str(LOGIN_VIDEO_PATH),
                autoplay=True,
                muted=True,
                loop=True,
                width="stretch",
            )
            st.markdown(
                _compact_html(_login_aside_markup()),
                unsafe_allow_html=True,
            )

    with form_column:
        with st.container(key="cubo_login_main"):
            st.markdown(
                """
                <div class="cubo-login-heading">
                    <h1 class="cubo-login-title">Iniciá sesión</h1>
                </div>
                """,
                unsafe_allow_html=True,
            )
            error_placeholder = st.empty()

            with st.form("login", border=False):
                username = st.text_input(
                    "Usuario",
                    autocomplete="username",
                )
                password = st.text_input(
                    "Contraseña",
                    type="password",
                    autocomplete="current-password",
                )
                submitted = st.form_submit_button(
                    "Entrar",
                    type="primary",
                    width="stretch",
                )

            loading_placeholder = st.empty()
            if submitted and username and password:
                loading_placeholder.markdown(
                    '<span class="cubo-login-loading" role="status" '
                    'aria-live="polite">Ingresando...</span>',
                    unsafe_allow_html=True,
                )

            st.markdown(
                """
                <p class="cubo-login-hint">
                    Cuentas de demostración: <strong>User1</strong> /
                    <strong>User2</strong>.
                </p>
                """,
                unsafe_allow_html=True,
            )

    if not submitted:
        return

    if not username or not password:
        error_placeholder.error("Ingresá tu usuario y contraseña.")
        return

    try:
        response = _post(
            "/auth/login",
            {"username": username, "password": password},
        )
    except ApiError as error:
        loading_placeholder.empty()
        if error.status_code == 401:
            error_placeholder.error("Usuario o contraseña incorrectos.")
        else:
            error_placeholder.error(str(error))
        return

    st.session_state.token = response["access_token"]
    st.session_state.username = username
    st.session_state.messages = []
    st.rerun()


def _show_chat() -> None:
    username = getattr(st.session_state, "username", None) or "Usuario"
    if _show_topbar(username):
        st.session_state.clear()
        st.rerun()

    is_new_conversation = not st.session_state.messages
    starter_prompt = None
    conversation = st.container(key="cubo_conversation")
    with conversation:
        st.markdown(
            '<div class="cubo-day-divider"><span>HOY</span></div>',
            unsafe_allow_html=True,
        )

        if is_new_conversation:
            with st.chat_message("assistant"):
                st.markdown(WELCOME_MESSAGE)
            starter_prompt = _show_quick_actions()

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    typed_prompt = st.chat_input(
        "Ej.: ¿qué salas hay libres mañana para 4 personas?"
    )
    prompt = starter_prompt or typed_prompt
    if not prompt:
        return

    history = list(st.session_state.messages)
    if is_new_conversation:
        history.append({"role": "assistant", "content": WELCOME_MESSAGE})
    with conversation:
        with st.container(key="cubo_message_enter_user"):
            with st.chat_message("user"):
                st.markdown(prompt)

        with st.container(key="cubo_message_enter_assistant"):
            with st.chat_message("assistant"):
                thinking_placeholder = st.empty()
                thinking_placeholder.markdown(
                    """
                    <div class="cubo-thinking" role="status">
                        <span class="cubo-thinking-cube" aria-hidden="true"></span>
                        <span class="cubo-thinking-label">
                            CUBO está pensando<span class="cubo-thinking-dots"
                            aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                try:
                    response = _post(
                        "/chat",
                        {"message": prompt, "history": history},
                        token=st.session_state.token,
                    )
                except ApiError as error:
                    thinking_placeholder.empty()
                    st.error(str(error))
                    return

                thinking_placeholder.empty()
                assistant_message = response["response"]
                st.markdown(assistant_message)

    if is_new_conversation:
        st.session_state.messages.append(
            {"role": "assistant", "content": WELCOME_MESSAGE}
        )
    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )
    st.session_state.messages.append(
        {"role": "assistant", "content": assistant_message}
    )
    st.rerun()


def _show_quick_actions() -> str | None:
    actions = (
        ("Buscar una sala", "Quiero buscar una sala disponible."),
        ("Ver mis reservas", "Mostrame mis reservas."),
        ("Consultar una agenda", "Quiero consultar la agenda de una sala."),
    )

    with st.container(key="cubo_quick_actions"):
        st.markdown(
            '<p class="cubo-quick-actions-label">Podés empezar por acá</p>',
            unsafe_allow_html=True,
        )
        columns = st.columns(len(actions), gap="small")
        for index, (label, prompt) in enumerate(actions):
            with columns[index]:
                if st.button(
                    label,
                    key=f"quick_action_{index}",
                    width="stretch",
                ):
                    return prompt

    return None


def _show_topbar(username: str) -> bool:
    safe_username = escape(username)
    initials = escape(_username_initials(username))

    with st.container(key="cubo_topbar"):
        brand_column, account_column, logout_column = st.columns(
            [5, 1.25, 1.25],
            gap="small",
            vertical_alignment="center",
        )
        with brand_column:
            st.markdown(
                _compact_html(
                    f"""
                    <div class="cubo-brand cubo-brand-topbar">
                        {CUBO_LOGO_HTML}
                        <span class="cubo-topbar-context">RESERVAS · DEMO</span>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )
        with account_column:
            st.markdown(
                f"""
                <div class="cubo-topbar-session" title="{safe_username}"
                     aria-label="Sesión de {safe_username}">
                    <span class="cubo-avatar" aria-hidden="true">{initials}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with logout_column:
            logout = st.button(
                "Cerrar sesión",
                key="topbar_logout",
                help="Cerrar sesión",
                type="tertiary",
                icon=":material/logout:",
                width="content",
            )

    return logout


def _login_aside_markup() -> str:
    return f"""
        <div class="cubo-login-aside-content">
            <div class="cubo-brand cubo-login-brand">
                {CUBO_LOGO_HTML}
                <span class="cubo-brand-context">RESERVAS · DEMO</span>
            </div>
            <div class="cubo-login-hero">
                <h2>Reservá una sala escribiendo, como se lo pedirías a alguien.</h2>
                <p>Cinco salas, bloques de 30 minutos, de 08:00 a 20:00. El
                asistente se ocupa de encontrar el hueco.</p>
            </div>
            <p class="cubo-login-meta">PISO 21 · PUNTA CARRETAS · MONTEVIDEO</p>
        </div>
    """


def _username_initials(username: str) -> str:
    normalized = username.strip()
    suffix = normalized[4:] if normalized.lower().startswith("user") else ""
    if suffix.isdigit():
        return f"U{suffix[0]}"
    return normalized[:2].upper() or "U"


def _post(
    path: str,
    payload: dict[str, Any],
    token: str | None = None,
) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(
        url=f"{API_BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(request, timeout=API_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise ApiError(
            _http_error_message(error),
            status_code=error.code,
        ) from error
    except (URLError, TimeoutError) as error:
        raise ApiError(
            "No se pudo conectar con la API. Verificá que esté funcionando."
        ) from error


def _http_error_message(error: HTTPError) -> str:
    try:
        body = json.loads(error.read().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return f"La API devolvió un error ({error.code})."

    detail = body.get("detail")
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return _validation_error_message(detail)

    return f"La API devolvió un error ({error.code})."


def _validation_error_message(details: list[Any]) -> str:
    for detail in details:
        if not isinstance(detail, dict):
            continue

        location = detail.get("loc", [])
        context = detail.get("ctx", {})
        max_length = context.get("max_length")

        if "message" in location and max_length is not None:
            return (
                "El mensaje puede tener como máximo "
                f"{max_length} caracteres."
            )
        if "history" in location and max_length is not None:
            return (
                "El historial puede tener como máximo "
                f"{max_length} mensajes."
            )

        message = detail.get("msg")
        if isinstance(message, str):
            return f"La solicitud no es válida: {message}"

    return "La solicitud no es válida."


if __name__ == "__main__":
    main()
