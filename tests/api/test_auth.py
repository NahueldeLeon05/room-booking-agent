from fastapi.testclient import TestClient


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
