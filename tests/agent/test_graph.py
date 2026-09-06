from unittest.mock import Mock

import pytest

import app.agent.graph as graph_module
from app.agent.graph import _system_prompt


def test_graph_uses_responses_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_options: dict[str, object] = {}

    class FakeChatOpenAI:
        def __init__(self, **options: object) -> None:
            model_options.update(options)

        def bind_tools(self, tools: list[object]) -> "FakeChatOpenAI":
            return self

    monkeypatch.setattr(graph_module, "ChatOpenAI", FakeChatOpenAI)

    graph_module.build_graph(Mock(), user_id=1)

    assert model_options["use_responses_api"] is True
    assert "temperature" not in model_options


def test_system_prompt_requires_confirmation_before_booking_creation() -> None:
    prompt = _system_prompt()

    assert "Before calling create_booking" in prompt
    assert "wait for an explicit confirmation" in prompt


def test_system_prompt_checks_availability_without_requesting_confirmation() -> None:
    prompt = _system_prompt()

    assert "Availability checks are read-only and do not need confirmation" in prompt
    assert "check availability immediately" in prompt


def test_system_prompt_does_not_request_repeated_confirmation() -> None:
    prompt = _system_prompt()

    assert "Do not ask for confirmation again" in prompt
    assert "call create_booking in the same turn" in prompt


def test_system_prompt_requires_answers_in_spanish() -> None:
    prompt = _system_prompt()

    assert "Always answer the user in Spanish" in prompt


def test_system_prompt_identifies_the_assistant_as_cubo() -> None:
    prompt = _system_prompt()

    assert "You are CUBO" in prompt
    assert "introduce yourself as CUBO" in prompt


def test_system_prompt_rejects_requests_outside_booking_scope() -> None:
    prompt = _system_prompt()

    assert "Your scope is limited to meeting-room bookings" in prompt
    assert "For an unrelated request, do not answer it" in prompt


def test_system_prompt_forbids_internet_searches() -> None:
    prompt = _system_prompt()

    assert "Never browse or search the internet" in prompt
    assert "Do not answer requests for external information" in prompt


def test_system_prompt_presents_booking_ids_as_user_facing_references() -> None:
    prompt = _system_prompt()

    assert "Reserva #<id>" in prompt


def test_system_prompt_does_not_infer_public_holiday_closures() -> None:
    prompt = _system_prompt()

    assert "Public holidays are out of scope" in prompt
    assert "every Monday through Friday as a working day" in prompt


def test_system_prompt_requests_safe_readable_markdown() -> None:
    prompt = _system_prompt()

    assert "Use concise Markdown" in prompt
    assert "Do not use HTML, tables, or code fences" in prompt
    assert "**Reserva #<id> — Sala <room>**" in prompt
