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


## Interval semantics
The example in the challenge (an appointment from 10:00 to 11:30 prevents another one from starting before 11:30) confirms that the room is available starting at 11:30.
It follows that the interval is half-open: [start, end), with the start included and the end excluded. The consequences for overlap detection are detailed in [03-business-rules.md](03-business-rules.md).

## Additional tools
The challenge lists four actions and does not include "List my bookings." Without this option, the
user cannot know what to cancel. Therefore, it will be implemented.

## Out of scope
The implementations that remain outside this scope are:

Recurring bookings, participant invitations, editing existing bookings, and notifications.

These are deliberate exclusions due to the scope of the challenge, not pending features.
