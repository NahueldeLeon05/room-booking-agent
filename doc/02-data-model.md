# Overview
The persistence model uses four SQLAlchemy tables: users, rooms, bookings, and booking slots. Bookings store the complete time range, while booking slots make room conflicts enforceable by the database.

## Entities

- `UserModel` stores a username and a password hash. Plain-text passwords are never stored.
- `RoomModel` represents a meeting room and its maximum capacity.
- `BookingModel` stores the room, user, title, attendees, time range, status, and creation time of a reservation.
- `BookingSlotModel` represents one 30-minute slot held by a booking.

## Relationships

- One user can own many bookings through `BookingModel.user_id`.
- One room can have many bookings through `BookingModel.room_id`.
- One booking can hold many slots through `BookingSlotModel.booking_id`.
- Each slot belongs to one room through `BookingSlotModel.room_id`.

The relationships are represented with foreign keys only. ORM relationship attributes are not needed at this stage.

## Schema

| Table | Main fields | Constraints |
|---|---|---|
| `users` | `id`, `username`, `password_hash` | `username` is unique |
| `rooms` | `id`, `name`, `capacity` | `name` is unique |
| `bookings` | `id`, `room_id`, `user_id`, `title`, `attendees`, `starts_at`, `ends_at`, `status`, `created_at` | `room_id` and `user_id` are foreign keys |
| `booking_slots` | `id`, `booking_id`, `room_id`, `slot_start` | foreign keys and unique `(room_id, slot_start)` |

The valid booking statuses are `active` and `cancelled`. This is a domain rule and is not currently enforced with a database check constraint.

## Concurrency strategy

Each booking interval is divided into consecutive 30-minute rows in `booking_slots`. The unique constraint on `(room_id, slot_start)` prevents two bookings from holding the same room at the same time.

If two requests try to reserve the same slot concurrently, only one transaction can commit. The other receives an `IntegrityError`. The application layer will roll back that transaction and return an actionable availability error.

This guarantee is enforced by the database instead of relying only on an availability check in Python. A persistence test verifies the constraint directly.

## Trade-offs considered

Storing individual slots adds rows to the database, but it makes conflicts simple and safe to enforce with a unique constraint. Checking overlap only with `starts_at` and `ends_at` would use fewer rows, but SQLite could not protect the complete check-and-insert operation with the same simple constraint.

`Base.metadata.create_all()` is used to initialize the challenge database.
