import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.infrastructure.models import Base


def pytest_configure() -> None:
    os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret")


@pytest.fixture
def db_engine(monkeypatch: pytest.MonkeyPatch) -> Generator[Engine, None, None]:
    monkeypatch.setenv("SEED_USER_PASSWORD", "test-password")
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    try:
        yield test_engine
    finally:
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


@pytest.fixture
def client(
    db_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    import app.main as main_module
    from app.infrastructure.database import get_session, init_db
    from app.infrastructure.seed import seed

    init_db(db_engine)
    with Session(bind=db_engine) as session:
        seed(session)

    def override_get_session() -> Generator[Session, None, None]:
        with Session(bind=db_engine) as session:
            yield session

    app = main_module.app
    app.dependency_overrides[get_session] = override_get_session
    monkeypatch.setattr(main_module, "init_db", lambda: None)
    monkeypatch.setattr(main_module, "seed", lambda: None)

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
