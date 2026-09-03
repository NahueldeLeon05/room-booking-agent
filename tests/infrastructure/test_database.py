from datetime import datetime

import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.database import init_db
from app.infrastructure.models import BookingSlotModel


def test_init_db_creates_all_tables(db_engine: Engine) -> None:
    init_db(db_engine)

    table_names = set(inspect(db_engine).get_table_names())

    assert table_names == {"users", "rooms", "bookings", "booking_slots"}


def test_foreign_keys_reject_rows_with_missing_parents(
    db_engine: Engine,
) -> None:
    init_db(db_engine)

    with Session(bind=db_engine) as session:
        session.add(
            BookingSlotModel(
                booking_id=999,
                room_id=999,
                slot_start=datetime(2026, 9, 3, 10, 0),
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()
