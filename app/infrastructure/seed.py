import os

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import ROOM_CAPACITIES
from app.infrastructure.database import SessionLocal
from app.infrastructure.models import RoomModel, UserModel


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed(session: Session | None = None) -> None:
    """Insert missing rooms and users into an initialized database."""
    password = os.environ["SEED_USER_PASSWORD"]
    db_session = session if session is not None else SessionLocal()

    try:
        existing_rooms = set(db_session.scalars(select(RoomModel.name)).all())
        for name, capacity in ROOM_CAPACITIES.items():
            if name not in existing_rooms:
                db_session.add(RoomModel(name=name, capacity=capacity))

        existing_users = set(db_session.scalars(select(UserModel.username)).all())
        for username in ("User1", "User2"):
            if username not in existing_users:
                db_session.add(
                    UserModel(
                        username=username,
                        password_hash=password_context.hash(password),
                    )
                )

        db_session.commit()
    finally:
        if session is None:
            db_session.close()
