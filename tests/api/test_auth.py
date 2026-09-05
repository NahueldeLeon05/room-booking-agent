from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import app.main as main_module
from app.infrastructure.database import get_session, init_db
from app.infrastructure.seed import seed
from app.main import app


@pytest.fixture
def client(
    db_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    init_db(db_engine)
    with Session(bind=db_engine) as session:
        seed(session)

    def override_get_session() -> Generator[Session, None, None]:
        with Session(bind=db_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    monkeypatch.setattr(main_module, "init_db", lambda: None)
    monkeypatch.setattr(main_module, "seed", lambda: None)

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_login_with_valid_credentials_returns_token(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"username": "User1", "password": "test-password"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"


def test_login_with_wrong_password_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"username": "User1", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_login_with_unknown_user_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"username": "Unknown", "password": "test-password"},
    )

    assert response.status_code == 401


def test_protected_endpoint_without_token_is_rejected(
    client: TestClient,
) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_protected_endpoint_with_invalid_token_is_rejected(
    client: TestClient,
) -> None:
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_protected_endpoint_with_valid_token_returns_current_user(
    client: TestClient,
) -> None:
    login_response = client.post(
        "/auth/login",
        json={"username": "User1", "password": "test-password"},
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"id": 1, "username": "User1"}
