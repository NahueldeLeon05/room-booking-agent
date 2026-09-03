from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import DATABASE_URL
from app.infrastructure.models import Base


connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(db_engine: Engine | None = None) -> None:
    """Create database tables that do not already exist."""
    target_engine = db_engine if db_engine is not None else engine
    Base.metadata.create_all(bind=target_engine)


def get_session() -> Generator[Session, None, None]:
    """Provide a database session and close it after the request finishes."""
    with SessionLocal() as session:
        yield session
