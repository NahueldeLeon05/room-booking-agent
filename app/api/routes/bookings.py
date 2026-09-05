from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.infrastructure.database import get_session
from app.infrastructure.models import UserModel
from app.infrastructure.repositories.booking_repository import BookingRepository
from app.services.booking_service import BookingService


router = APIRouter(prefix="/bookings", tags=["bookings"])


class BookingResponse(BaseModel):
    id: int
    room: str
    title: str
    attendees: int
    starts_at: datetime
    ends_at: datetime


@router.get("/me", response_model=list[BookingResponse])
def list_my_bookings(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[BookingResponse]:
    repository = BookingRepository(session)
    service = BookingService(repository)
    bookings = service.list_my_bookings(current_user.id)

    return [
        BookingResponse(
            id=booking.id,
            room=booking.room_name,
            title=booking.title,
            attendees=booking.attendees,
            starts_at=booking.time_range.starts_at,
            ends_at=booking.time_range.ends_at,
        )
        for booking in bookings
    ]
