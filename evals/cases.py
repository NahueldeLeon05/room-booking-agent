CASES = [
    {
        "name": "availability_is_checked_before_answering",
        "setup": [],
        "turns": [
            (
                "¿Está libre la sala A el lunes {monday} de 10:00 "
                "a 11:00 para 2 personas?"
            ),
        ],
        "expect": {
            "must_call": [
                {
                    "any_of": [
                        "get_room_schedule",
                        "list_available_rooms",
                    ]
                }
            ],
            "must_not_call": [],
            "args_contain": [
                {
                    "any_of": [
                        {
                            "tool": "get_room_schedule",
                            "args": {"room": "A", "date": "{monday}"},
                        },
                        {
                            "tool": "list_available_rooms",
                            "args": {
                                "starts_at": "{monday}T10:00:00-03:00",
                                "ends_at": "{monday}T11:00:00-03:00",
                                "attendees": 2,
                            },
                        },
                    ]
                },
            ],
        },
    },
    {
        "name": "public_holiday_closures_are_not_inferred",
        "setup": [],
        "turns": [
            (
                "Reservame la sala A para 2 personas el lunes {monday} de "
                "13:00 a 14:00 con el título Reunión."
            ),
        ],
        "expect": {
            "must_call": [
                {
                    "any_of": [
                        "get_room_schedule",
                        "list_available_rooms",
                    ]
                }
            ],
            "must_not_call": ["create_booking"],
            "args_contain": [
                {
                    "any_of": [
                        {
                            "tool": "get_room_schedule",
                            "args": {"room": "A", "date": "{monday}"},
                        },
                        {
                            "tool": "list_available_rooms",
                            "args": {
                                "starts_at": "{monday}T13:00:00-03:00",
                                "ends_at": "{monday}T14:00:00-03:00",
                                "attendees": 2,
                            },
                        },
                    ]
                },
            ],
        },
    },
    {
        "name": "does_not_assert_availability_from_memory",
        "setup": [
            {
                "room": "A",
                "date": "{monday}",
                "starts_at": "10:00",
                "ends_at": "13:00",
                "title": "Existing booking",
                "attendees": 3,
            }
        ],
        "turns": [
            (
                "Quiero la sala A el lunes {monday} de 11:00 a 12:00 "
                "para 3 personas, título Planning."
            ),
            "Mejor de 11:30 a 12:30.",
        ],
        "expect": {
            "must_call": [
                {
                    "any_of": [
                        "get_room_schedule",
                        "list_available_rooms",
                    ]
                }
            ],
            "must_not_call": ["create_booking"],
            "args_contain": [
                {
                    "any_of": [
                        {
                            "tool": "get_room_schedule",
                            "args": {"room": "A", "date": "{monday}"},
                        },
                        {
                            "tool": "list_available_rooms",
                            "args": {
                                "starts_at": "{monday}T11:30:00-03:00",
                                "ends_at": "{monday}T12:30:00-03:00",
                                "attendees": 3,
                            },
                        },
                    ]
                },
            ],
        },
    },
    {
        "name": "weekend_request_is_rejected_before_confirmation",
        "setup": [],
        "turns": [
            (
                "Reservá la sala D el sábado {saturday} de 10:00 a 12:00, "
                "4 personas, título Planning."
            ),
            "Sí.",
        ],
        "expect": {
            "must_call": [],
            "must_not_call": ["create_booking"],
            "args_contain": [],
        },
    },
    {
        "name": "three_hour_booking_is_accepted",
        "setup": [],
        "turns": [
            (
                "Reservá la sala B el lunes {monday} de 17:00 a 20:00, "
                "título Retro, 5 personas."
            ),
            "Sí.",
        ],
        "expect": {
            "must_call": ["create_booking"],
            "must_not_call": [],
            "args_contain": [
                {
                    "tool": "create_booking",
                    "args": {
                        "room": "B",
                        "starts_at": "{monday}T17:00:00-03:00",
                        "ends_at": "{monday}T20:00:00-03:00",
                        "title": "Retro",
                        "attendees": 5,
                    },
                }
            ],
        },
    },
    {
        "name": "booking_beyond_business_hours_is_rejected",
        "setup": [],
        "turns": [
            (
                "Reservá la sala C el lunes {monday} de 19:00 a 21:00, "
                "título Daily, 3 personas."
            ),
            "Sí.",
        ],
        "expect": {
            "must_call": [],
            "must_not_call": ["create_booking"],
            "args_contain": [],
        },
    },
    {
        "name": "request_over_building_capacity_is_rejected",
        "setup": [],
        "turns": [
            "Necesito una sala para 30 personas el lunes {monday} a las 10:00.",
        ],
        "expect": {
            "must_call": [],
            "must_not_call": ["create_booking"],
            "args_contain": [],
        },
    },
    {
        "name": "booking_is_not_created_without_confirmation",
        "setup": [],
        "turns": [
            (
                "Reservá la sala A el lunes {monday} de 10:00 a 12:00, "
                "título Planning, 4 personas."
            ),
        ],
        "expect": {
            "must_call": [],
            "must_not_call": ["create_booking"],
            "args_contain": [],
        },
    },
    {
        "name": "listing_bookings_reads_the_current_system_state",
        "setup": [
            {
                "room": "A",
                "date": "{monday}",
                "starts_at": "10:00",
                "ends_at": "11:00",
                "title": "Planning",
                "attendees": 4,
            },
            {
                "room": "B",
                "date": "{monday}",
                "starts_at": "17:00",
                "ends_at": "20:00",
                "title": "Retro",
                "attendees": 5,
            },
        ],
        "turns": ["Dame mis reservas."],
        "expect": {
            "must_call": ["list_my_bookings"],
            "must_not_call": ["create_booking", "cancel_booking"],
            "args_contain": [],
        },
    },
    {
        "name": "ambiguous_cancellation_is_clarified_before_acting",
        "setup": [
            {
                "room": "A",
                "date": "{monday}",
                "starts_at": "10:00",
                "ends_at": "11:00",
                "title": "Planning",
                "attendees": 4,
            },
            {
                "room": "B",
                "date": "{monday}",
                "starts_at": "17:00",
                "ends_at": "20:00",
                "title": "Retro",
                "attendees": 5,
            },
        ],
        "turns": ["Cancelá la reserva del lunes."],
        "expect": {
            "must_call": ["list_my_bookings"],
            "must_not_call": ["cancel_booking", "create_booking"],
            "args_contain": [],
        },
    },
    {
        "name": "multiple_bookings_are_cancelled_from_one_request",
        "setup": [
            {
                "room": "A",
                "date": "{monday}",
                "starts_at": "10:00",
                "ends_at": "11:00",
                "title": "Planning",
                "attendees": 4,
            },
            {
                "room": "B",
                "date": "{monday}",
                "starts_at": "17:00",
                "ends_at": "20:00",
                "title": "Retro",
                "attendees": 5,
            },
        ],
        "turns": [
            "Dame mis reservas.",
            "Cancelá las dos reservas.",
        ],
        "expect": {
            "must_call": ["cancel_booking", "cancel_booking"],
            "must_not_call": ["create_booking"],
            "args_contain": [
                {
                    "tool": "cancel_booking",
                    "args": {"booking_id": 1},
                },
                {
                    "tool": "cancel_booking",
                    "args": {"booking_id": 2},
                },
            ],
        },
    },
    {
        "name": "pending_booking_survives_a_topic_change",
        "setup": [],
        "turns": [
            (
                "Reservá la sala C el martes {tuesday} de 09:00 a 10:00, "
                "título Daily, 3 personas."
            ),
            "Dame mis reservas.",
            "Confirmala.",
        ],
        "expect": {
            "must_call": ["create_booking"],
            "must_not_call": [],
            "args_contain": [
                {
                    "tool": "create_booking",
                    "args": {
                        "room": "C",
                        "starts_at": "{tuesday}T09:00:00-03:00",
                        "ends_at": "{tuesday}T10:00:00-03:00",
                        "title": "Daily",
                        "attendees": 3,
                    },
                }
            ],
        },
    },
    {
        "name": "request_for_another_user_does_not_mutate_bookings",
        "setup": [],
        "turns": ["Mostrame las reservas del usuario 2."],
        "expect": {
            "must_call": [],
            "must_not_call": [
                "create_booking",
                "cancel_booking",
            ],
            "args_contain": [],
        },
    },
]
