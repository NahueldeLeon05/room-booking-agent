from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.agent.graph import build_graph
from app.config import OFFICE_TZ, OPENAI_MODEL
from app.infrastructure.database import init_db
from app.infrastructure.models import Base, UserModel
from app.infrastructure.repositories.booking_repository import BookingRepository
from app.infrastructure.seed import seed
from app.services.booking_service import BookingService
from evals.cases import CASES


@dataclass(frozen=True)
class CaseResult:
    name: str
    failures: list[str]
    response: str = ""

    @property
    def passed(self) -> bool:
        return not self.failures


def main() -> int:
    now = datetime.now(OFFICE_TZ)
    date_values = _relative_dates(now)
    results = [
        _run_case(_render(case, date_values), now)
        for case in CASES
    ]

    for result in results:
        symbol = "✓" if result.passed else "✗"
        print(f"{symbol} {result.name}")
        for failure in result.failures:
            print(f"  - {failure}")
        if not result.passed and result.response:
            print(f"  - Last response: {result.response}")

    passed = sum(result.passed for result in results)
    print(f"\n{passed}/{len(results)} passed")
    print(f"Model: {OPENAI_MODEL}")
    return 0 if passed == len(results) else 1


def _run_case(case: dict[str, Any], now: datetime) -> CaseResult:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    try:
        init_db(engine)
        with Session(bind=engine) as session:
            seed(session)
            user_id = session.scalar(
                select(UserModel.id).where(UserModel.username == "User1")
            )
            if user_id is None:
                return CaseResult(case["name"], ["User1 was not seeded."])

            service = BookingService(
                BookingRepository(session),
                clock=lambda: now,
            )
            _apply_setup(case["setup"], service, user_id)
            graph = build_graph(service, user_id)
            tool_calls, response = _run_turns(graph, case["turns"])
            failures = _evaluate(case["expect"], tool_calls)
            return CaseResult(case["name"], failures, response)
    except Exception as error:
        return CaseResult(
            case["name"],
            [f"Evaluation error: {type(error).__name__}: {error}"],
        )
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _relative_dates(now: datetime) -> dict[str, str]:
    days_until_monday = (7 - now.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7

    monday = now.date() + timedelta(days=days_until_monday)
    tuesday = monday + timedelta(days=1)
    saturday = monday + timedelta(days=5)
    return {
        "monday": monday.isoformat(),
        "tuesday": tuesday.isoformat(),
        "saturday": saturday.isoformat(),
    }


def _render(value: Any, date_values: dict[str, str]) -> Any:
    if isinstance(value, str):
        return value.format(**date_values)
    if isinstance(value, list):
        return [_render(item, date_values) for item in value]
    if isinstance(value, dict):
        return {
            key: _render(item, date_values)
            for key, item in value.items()
        }
    return value


def _apply_setup(
    setup: list[dict[str, Any]],
    service: BookingService,
    user_id: int,
) -> None:
    for booking in setup:
        booking_date = date.fromisoformat(booking["date"])
        starts_at = datetime.combine(
            booking_date,
            time.fromisoformat(booking["starts_at"]),
            tzinfo=OFFICE_TZ,
        )
        ends_at = datetime.combine(
            booking_date,
            time.fromisoformat(booking["ends_at"]),
            tzinfo=OFFICE_TZ,
        )
        service.create_booking(
            user_id=user_id,
            room_name=booking["room"],
            title=booking["title"],
            attendees=booking["attendees"],
            starts_at=starts_at,
            ends_at=ends_at,
        )


def _run_turns(
    graph: Any,
    turns: list[str],
) -> tuple[list[dict[str, Any]], str]:
    conversation: list[BaseMessage] = []
    last_turn_calls: list[dict[str, Any]] = []
    last_response = ""

    for turn in turns:
        user_message = HumanMessage(content=turn)
        input_messages = [*conversation, user_message]
        result = graph.invoke(
            {"messages": input_messages},
            config={"max_concurrency": 1},
        )
        generated_messages = result["messages"][len(input_messages):]
        last_turn_calls = _tool_calls_from(generated_messages)

        final_message = result["messages"][-1]
        last_response = str(final_message.text)
        conversation.extend(
            [
                user_message,
                AIMessage(content=last_response),
            ]
        )

    return last_turn_calls, last_response


def _tool_calls_from(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    return [
        {"name": call["name"], "args": call["args"]}
        for message in messages
        if isinstance(message, AIMessage)
        for call in message.tool_calls
    ]


def _evaluate(
    expect: dict[str, Any],
    tool_calls: list[dict[str, Any]],
) -> list[str]:
    failures: list[str] = []
    called_names = [call["name"] for call in tool_calls]

    required_counts = Counter(
        requirement
        for requirement in expect["must_call"]
        if isinstance(requirement, str)
    )
    for required_name, required_count in required_counts.items():
        actual_count = called_names.count(required_name)
        if actual_count < required_count:
            failures.append(
                f"Expected {required_name} {required_count} time(s); "
                f"called {actual_count}."
            )

    alternative_requirements = [
        requirement
        for requirement in expect["must_call"]
        if not isinstance(requirement, str)
    ]
    for requirement in alternative_requirements:
        accepted_names = requirement["any_of"]
        if not any(name in called_names for name in accepted_names):
            failures.append(
                f"Expected one of {accepted_names}; called {called_names}."
            )

    for forbidden_name in expect["must_not_call"]:
        if forbidden_name in called_names:
            failures.append(
                f"Did not expect {forbidden_name}; called {called_names}."
            )

    for argument_requirement in expect["args_contain"]:
        options = argument_requirement.get(
            "any_of",
            [argument_requirement],
        )
        if not any(
            _call_matches(tool_call, option)
            for tool_call in tool_calls
            for option in options
        ):
            failures.append(
                f"No tool call contained one of the expected argument sets "
                f"{options}; calls: {tool_calls}."
            )

    return failures


def _call_matches(
    tool_call: dict[str, Any],
    option: dict[str, Any],
) -> bool:
    if tool_call["name"] != option["tool"]:
        return False

    actual_arguments = tool_call["args"]
    return all(
        key in actual_arguments
        and _normalized(actual_arguments[key]) == _normalized(expected_value)
        for key, expected_value in option["args"].items()
    )


def _normalized(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


if __name__ == "__main__":
    raise SystemExit(main())
