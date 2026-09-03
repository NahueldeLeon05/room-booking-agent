from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app.infrastructure.database import init_db


def test_init_db_creates_all_tables(db_engine: Engine) -> None:
    init_db(db_engine)

    table_names = set(inspect(db_engine).get_table_names())

    assert table_names == {"users", "rooms", "bookings", "booking_slots"}
