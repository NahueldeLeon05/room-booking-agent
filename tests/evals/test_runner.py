from evals.runner import _evaluate


def _expect(**response_expectations: list[str]) -> dict[str, object]:
    return {
        "must_call": [],
        "must_not_call": [],
        "args_contain": [],
        **response_expectations,
    }


def test_required_response_text_is_checked_case_insensitively() -> None:
    failures = _evaluate(
        _expect(response_must_contain=["cubo", "reserv"]),
        [],
        "Soy CUBO y puedo ayudarte con reservas.",
    )

    assert failures == []


def test_forbidden_response_text_is_rejected() -> None:
    failures = _evaluate(
        _expect(response_must_not_contain=["1 taza"]),
        [],
        "Para el flan necesitás 1 taza de azúcar.",
    )

    assert failures == ["Expected response not to contain '1 taza'."]
