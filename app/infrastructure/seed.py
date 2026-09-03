import os

from passlib.context import CryptContext
from sqlalchemy import select

from app.config import ROOM_CAPACITIES
from app.infrastructure.database import SessionLocal
from app.infrastructure.models import RoomModel, UserModel


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed() -> None:
    """Insert missing rooms and users into an initialized database."""
    password = os.environ["SEED_USER_PASSWORD"]

    with SessionLocal() as session:
        existing_rooms = set(session.scalars(select(RoomModel.name)).all())
        for name, capacity in ROOM_CAPACITIES.items():
            if name not in existing_rooms:
                session.add(RoomModel(name=name, capacity=capacity))

        existing_users = set(session.scalars(select(UserModel.username)).all())
        for username in ("User1", "User2"):
            if username not in existing_users:
                session.add(
                    UserModel(
                        username=username,
                        password_hash=password_context.hash(password),
                    )
                )

        session.commit()
