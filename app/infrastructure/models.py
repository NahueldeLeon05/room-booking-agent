from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))


class RoomModel(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(1), unique=True)
    capacity: Mapped[int] = mapped_column()


class BookingModel(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))
    attendees: Mapped[int] = mapped_column()
    starts_at: Mapped[datetime] = mapped_column()
    ends_at: Mapped[datetime] = mapped_column()
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column()


class BookingSlotModel(Base):
    __tablename__ = "booking_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"))
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    slot_start: Mapped[datetime] = mapped_column()

    __table_args__ = (
        UniqueConstraint("room_id", "slot_start"),
    )
