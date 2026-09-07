# Tool contracts

## Overview

Tools are the boundary between the model and the booking service. The model can
choose a tool and provide its arguments, but the service still validates every
request. A tool does not make business decisions by itself.

## Tool inventory

| Tool | When it is used | Arguments |
|---|---|---|
| `list_rooms` | The user asks which rooms exist or wants to browse the catalog | None |
| `get_room_details` | The user asks to see or learn about one specific room | `room` |
| `list_my_bookings` | The user asks for their active bookings | None |
| `create_booking` | The user confirms all booking details | `room`, `starts_at`, `ends_at`, `title`, `attendees` |
| `list_available_rooms` | The user has not selected a room and asks which ones are free for a complete range | `starts_at`, `ends_at`, `attendees` |
| `check_room_availability` | The user already selected a room and its exact range must be verified | `room`, `starts_at`, `ends_at`, `attendees` |
| `get_room_schedule` | The user asks for the free and occupied ranges of one room on a date | `room`, `date` |
| `cancel_booking` | The user confirms cancellation of an identified booking | `booking_id` |

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
structured JSON because the application needs to parse them. Every tool return
uses LangChain's `content_and_artifact` format: content is read by the model,
while the artifact is consumed only by the API and UI.

### Decision

I decided to keep model-facing results as short, consistent text and attach a
typed `PresentationArtifact`. It has one of three explicit modes: `message`,
`room_gallery`, or `booking_list`, plus the corresponding room names or booking
summaries.

### Rationale

Text uses fewer tokens and gives the model less work before answering the user.
The artifact lets the UI render photographs and booking summaries without
parsing natural language or repeating visuals based on stale conversational
context. This preserves the interaction decision in
[04-architecture.md](04-architecture.md): visuals are supporting information,
not controls required to continue the booking flow.

### Trade-off considered

Short and flat JSON would also work. The problem appears with deeply nested
JSON and long responses. JSON would be better if the model needed to make
precise calculations with the data, but the service already does that work
here.

## Presentation behavior

- `list_rooms` and `get_room_details` request a room gallery.
- `list_available_rooms` requests a gallery only when it finds candidate rooms.
- `check_room_availability` returns no gallery when the selected room is free;
  if it is unavailable, it requests a gallery only for valid alternatives.
- `list_my_bookings` requests a booking list.
- Creation, cancellation, schedules, validation errors, and ordinary messages
  use the `message` presentation.

This contract is the source of truth for visuals. The UI does not search for
room names or headings in assistant prose.

## Schedule scope

`get_room_schedule` accepts a room and date and returns the complete assumed
working day, 08:00 to 20:00, grouped into free and occupied ranges. A requested
subrange is therefore included in the answer, along with adjacent options that
may help the user choose another time.

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
