# Overview
The challenge leaves several points undefined: room capacities, operating hours, and the handling of past dates. This document records each adopted assumption along with its justification and its impact on the system.

## Room capacities
The challenge states that the rooms have a maximum capacity, but it does not specify what that maximum is or whether all rooms have the same maximum.
Therefore, I assigned a maximum capacity to each room:
A=4, B=6, C=8, D=12, E=20
This allows me to represent a real office while also creating a more meaningful constraint, since a request for a room for 10 people leaves only 2 candidate rooms, forcing the search to filter by capacity in addition to time.

## Business hours
The challenge does not define them, so I decided to use office hours from 08:00 to 20:00.
Without a time limit, displaying the schedule to the user would show 48 slots, half of which would be during the early morning, making the conversational experience less convenient for the user.

## Past bookings
I assume that bookings cannot be made for times that have already passed.
This also requires the system to know the current date and time, which has a concrete consequence for the agent because it does not know them and they must be injected into it.

## Timezone
The challenge does not define a timezone. I use a fixed UTC-3 offset instead of `America/Montevideo` because Uruguay does not currently observe daylight saving time.
SQLite stores booking datetimes as local values without timezone information. The repository adds `OFFICE_TZ` when it maps them back to the domain. This restores the known offset without changing the stored clock time.

## Interval semantics
The example in the challenge (an appointment from 10:00 to 11:30 prevents another one from starting before 11:30) confirms that the room is available starting at 11:30.
It follows that the interval is half-open: [start, end), with the start included and the end excluded. The consequences for overlap detection are detailed in [03-business-rules.md](03-business-rules.md).

## Working days
The challenge defines the business hours, but it does not specify which days the office operates.
I assume that bookings can only be made from Monday to Friday. This is consistent with the 08:00 to 20:00 office hours and with a corporate office that does not operate on weekends.
Therefore, slot generation and booking validation must reject Saturdays and Sundays.

## Booking horizon
The challenge does not define how far in advance a booking can be made.
I assume that bookings can be made up to 90 days in advance. Without a limit, availability searches could receive unreasonable ranges, and booking more than three months ahead has little operational value.
This limit must live in the configuration instead of being repeated as a magic number.

## Minimum attendees
The challenge requires the number of attendees, but it does not define a minimum.
I assume that a booking must have at least one attendee because a booking for zero people does not represent a real meeting.
If someone requests a room for more than 20 people, no room can satisfy the request. The error must state the maximum room capacity instead of returning a generic message.

## Cancellation of past bookings
I assume that a booking cannot be cancelled if its `starts_at` time has already passed. Once the meeting has started, cancelling it does not free any useful time.
The cutoff is the start time, not the end time or the day. This means that a booking already in progress cannot be cancelled.
The system needs to know the current time to enforce this rule, just as it does when rejecting bookings in the past.

## Meaning of "available" for a time range
I assume that a room is available only if it is free for the entire requested time range.
Someone asking what is available from 14:00 to 17:00 wants to schedule a three-hour meeting. A room with separate free slots during that range is not useful and listing it would add noise.
The `get_room_schedule` tool covers the other case by showing the occupied and free slots for one room.
If no room is free for the complete range, the result is empty. The system must compensate for this with an actionable error that suggests alternatives.

## Additional tools
The challenge lists four actions and does not include "List my bookings." Without this option, the
user cannot know what to cancel. Therefore, it will be implemented.

## Out of scope
The implementations that remain outside this scope are:

Recurring bookings, participant invitations, editing existing bookings, and notifications.

These are deliberate exclusions due to the scope of the challenge, not pending features.
