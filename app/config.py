import os
from datetime import time, timedelta, timezone


SLOT_MINUTES = 30
MAX_BOOKING_HOURS = 3
BUSINESS_START = time(8, 0)
BUSINESS_END = time(20, 0)
ROOM_CAPACITIES = {"A": 4, "B": 6, "C": 8, "D": 12, "E": 20}
OFFICE_TZ = timezone(timedelta(hours=-3))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
