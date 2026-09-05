from dataclasses import dataclass
from datetime import datetime, timedelta

from app.config import SLOT_MINUTES
from app.domain.exceptions import InvalidTimeRange


@dataclass(frozen=True)
class TimeRange:
    starts_at: datetime
    ends_at: datetime

    def __post_init__(self) -> None:
        if self.ends_at <= self.starts_at:
            raise InvalidTimeRange("ends_at must be after starts_at")

    @property
    def duration(self) -> timedelta:
        return self.ends_at - self.starts_at

    def is_slot_aligned(self) -> bool:
        # Both boundaries must fall exactly on the configured slot grid.
        return (
            self._is_boundary_aligned(self.starts_at)
            and self._is_boundary_aligned(self.ends_at)
        )

    def overlaps(self, other: "TimeRange") -> bool:
        # Half-open ranges may touch at an end boundary without overlapping.
        return (
            self.starts_at < other.ends_at
            and other.starts_at < self.ends_at
        )

    def slot_starts(self) -> list[datetime]:
        slots: list[datetime] = []
        current = self.starts_at
        slot_duration = timedelta(minutes=SLOT_MINUTES)

        # The end boundary is excluded because the range is half-open.
        while current < self.ends_at:
            slots.append(current)
            current += slot_duration

        return slots

    @staticmethod
    def _is_boundary_aligned(boundary: datetime) -> bool:
        return (
            boundary.minute % SLOT_MINUTES == 0
            and boundary.second == 0
            and boundary.microsecond == 0
        )
