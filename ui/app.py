import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
API_TIMEOUT_SECONDS = 120


class ApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


def main() -> None:
    st.set_page_config(page_title="CUBO")
    _initialize_session()

    if not st.session_state.token:
        _show_login()
        return

    _show_chat()


def _initialize_session() -> None:
    if "token" not in st.session_state:
        st.session_state.token = None
    if "messages" not in st.session_state:
        st.session_state.messages = []


def _show_login() -> None:
    st.title("CUBO")
    st.caption("Asistente de reservas de salas de reuniones")

    with st.form("login"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Ingresar")

    if not submitted:
        return

    if not username or not password:
        st.error("Ingresá tu usuario y contraseña.")
        return

    try:
        with st.spinner("Iniciando sesión..."):
            response = _post(
                "/auth/login",
                {"username": username, "password": password},
            )
    except ApiError as error:
        if error.status_code == 401:
            st.error("Usuario o contraseña incorrectos.")
        else:
            st.error(str(error))
        return

    st.session_state.token = response["access_token"]
    st.session_state.messages = []
    st.rerun()


def _show_chat() -> None:
    title_column, logout_column = st.columns([4, 1])
    with title_column:
        st.title("CUBO")
        st.caption("Asistente de reservas de salas de reuniones")
    with logout_column:
        if st.button("Cerrar sesión"):
            st.session_state.clear()
            st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Escribí tu mensaje")
    if not prompt:
        return

    history = list(st.session_state.messages)
    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Pensando..."):
                response = _post(
                    "/chat",
                    {"message": prompt, "history": history},
                    token=st.session_state.token,
                )
        except ApiError as error:
            st.error(str(error))
            return

        assistant_message = response["response"]
        st.markdown(assistant_message)

    st.session_state.messages.append(
        {"role": "assistant", "content": assistant_message}
    )


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

    return f"La API devolvió un error ({error.code})."


if __name__ == "__main__":
    main()
