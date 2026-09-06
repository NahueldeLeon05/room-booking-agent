from app.agent.graph import _system_prompt


def test_system_prompt_requires_confirmation_before_booking_creation() -> None:
    prompt = _system_prompt()

    assert "Before calling create_booking" in prompt
    assert "wait for an explicit confirmation" in prompt


def test_system_prompt_requires_answers_in_spanish() -> None:
    prompt = _system_prompt()

    assert "Always answer the user in Spanish" in prompt


def test_system_prompt_presents_booking_ids_as_user_facing_references() -> None:
    prompt = _system_prompt()

    assert "Reserva #<id>" in prompt
