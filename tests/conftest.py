from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.infrastructure.models import Base


@pytest.fixture
def db_engine(monkeypatch: pytest.MonkeyPatch) -> Generator[Engine, None, None]:
    monkeypatch.setenv("SEED_USER_PASSWORD", "test-password")
    test_engine = create_engine("sqlite:///:memory:")

    try:
        yield test_engine
    finally:
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()
