# Overview
<!-- Summarize the business rules documented in this file. -->

## Rule catalogue

### R1 — Bookings must be in the future

- The next valid slot is accepted.
- A slot in the past is rejected.

### R2 — Bookings are allowed Monday through Friday

- Friday is accepted.
- Saturday and Sunday are rejected.

### R3 — Bookings must be within business hours

- A booking starting at 08:00 is accepted.
- A booking ending at 20:00 is accepted.
- A booking outside those limits is rejected.

### R4 — Bookings must have a positive duration and align to 30-minute slots

- A booking from 10:00 to 10:30 is accepted.
- A booking starting at 10:15 is rejected.
- A booking with the same start and end time is rejected.

### R5 — Maximum booking duration is 3 hours

- A booking lasting exactly 3 hours is accepted.
- A booking lasting 3 hours and one slot is rejected.

### R6 — A booking must have at least one attendee

- A booking for 1 attendee is accepted.
- A booking for 0 attendees is rejected.

### R7 — Room capacity must cover all attendees

- A number of attendees equal to the room capacity is accepted.
- A number of attendees above the room capacity rejects that room.
- A request for more than 20 attendees is rejected and reports the maximum room capacity.

### R8 — The complete requested range must be available

- A range where all requested slots are free is accepted.
- A range where one requested slot is occupied is rejected.
- A booking starting exactly when another booking ends is accepted.

### R9 — Users can only cancel their own active bookings

- Cancelling an active booking owned by the user is accepted.
- Cancelling another user's booking is rejected.
- Cancelling an already cancelled booking is rejected.

### R10 — Bookings cannot be cancelled after they start

- Cancelling before `starts_at` is accepted.
- Cancelling exactly at `starts_at` is rejected.
- Cancelling a booking already in progress is rejected.

### R11 — All slots in a booking must be contiguous

- A one-slot booking is accepted.
- A multi-slot booking generates every consecutive slot in its interval.
- Separate free gaps cannot form one booking.

Contiguity is satisfied by construction because a booking is represented by one continuous `[start, end)` interval. The system generates every 30-minute slot inside that interval, so callers cannot provide an arbitrary list with gaps.

### R12 — Bookings can be made up to 90 days ahead

- A booking exactly 90 days ahead is accepted.
- A booking 90 days and one slot ahead is rejected.

## Validation layer

The domain and application service will validate these rules before writing to the database. The tools and the system prompt can describe the rules, but they are not responsible for enforcing them.

The authenticated session provides `user_id`; the model cannot choose it. The database unique constraint on `(room_id, slot_start)` is the final protection against concurrent reservations. If it raises `IntegrityError`, the application must roll back the transaction and return an actionable error.

## Edge cases
<!-- Document boundary conditions and exceptional scenarios. -->
