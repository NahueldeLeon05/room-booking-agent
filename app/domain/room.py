from dataclasses import dataclass


@dataclass(frozen=True)
class Room:
    id: int
    name: str
    capacity: int
