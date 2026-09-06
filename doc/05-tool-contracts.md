# Tool contracts

## Overview

Tools are the boundary between the model and the booking service. The model can
choose a tool and provide its arguments, but the service still validates every
request. A tool does not make business decisions by itself.

## Tool inventory

| Tool | When it is used | Arguments |
|---|---|---|
| `list_my_bookings` | The user asks for their active bookings | None |
| `create_booking` | The user confirms all booking details | `room`, `starts_at`, `ends_at`, `title`, `attendees` |
| `list_available_rooms` | The user asks which rooms are free for a complete range | `starts_at`, `ends_at`, `attendees` |
| `get_room_schedule` | The user asks for the free and occupied ranges of one room | `room`, `date` |
| `cancel_booking` | The user asks to cancel one of their bookings | `booking_id` |

## Schemas

Tool arguments use Pydantic schemas. The descriptions are written for the
model, because they become part of the tool schema it receives.

- `room` is one uppercase letter from A to E.
- `starts_at` and `ends_at` use ISO 8601 with the UTC-3 offset, for example
  `2026-09-07T10:00:00-03:00`.
- Booking times must fall on a 30-minute boundary.
- `title` is provided by the user and cannot be empty.
- `attendees` is an integer validated against the minimum and room capacity by
  the service.
- `date` uses `YYYY-MM-DD`.
- `booking_id` comes from `list_my_bookings`; the model must not invent it.

The schemas validate types and formats. Business rules such as capacity,
working days, availability, and maximum duration remain in the domain and
service layers.

## Tool return format

### Arguments vs return values

Tool arguments and return values have different purposes. Arguments use
structured JSON because the application needs to parse them. Return values are
read by the model.

### Decision

I decided to return structured and consistent text instead of JSON. Each tool
uses the same format and includes the booking ID when it is needed.

### Rationale

Text uses fewer tokens and gives the model less work before answering the user.
It is also consistent with the conversational interface decision in
[04-architecture.md](04-architecture.md).

### Trade-off considered

Short and flat JSON would also work. The problem appears with deeply nested
JSON and long responses. JSON would be better if the model needed to make
precise calculations with the data, but the service already does that work
here.

## Error responses

A successful result starts with `Status: success`. A rejected result starts
with `Status: error` and includes an actionable message that the model can
explain to the user.

Domain errors are returned as text instead of escaping into the graph. For
example, an unavailable room can include its occupied slots and alternative
rooms. Invalid tool arguments return a format error. Unexpected errors are
logged by the application and return a generic message without exposing
internal details.

## Security considerations

`user_id` never appears in a tool schema. FastAPI obtains it from the JWT and
passes it to `build_tools`, where every tool captures it as a closure. The model
cannot choose another identity through a tool call.

Cancellation also filters by both `booking_id` and `user_id` in the repository
query. A booking that belongs to another user is treated in the same way as a
booking that does not exist, so the system does not reveal another user's data.
