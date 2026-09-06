from datetime import datetime

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.agent.tools import build_tools
from app.config import OFFICE_TZ
from app.infrastructure.database import init_db
from app.infrastructure.models import BookingModel, BookingSlotModel, UserModel
from app.infrastructure.repositories.booking_repository import BookingRepository
from app.infrastructure.seed import seed
from app.services.booking_service import BookingService


NOW = datetime(2026, 9, 7, 10, 0, tzinfo=OFFICE_TZ)


def test_multiple_cancellations_leave_no_active_bookings_or_slots(
    db_engine: Engine,
) -> None:
    init_db(db_engine)

    with Session(bind=db_engine) as session:
        seed(session)
        user_id = session.scalar(
            select(UserModel.id).where(UserModel.username == "User1")
        )
        assert user_id is not None

        service = BookingService(
            BookingRepository(session),
            clock=lambda: NOW,
        )
        first = service.create_booking(
            user_id=user_id,
            room_name="A",
            title="First meeting",
            attendees=2,
            starts_at=datetime(2026, 9, 7, 10, 30, tzinfo=OFFICE_TZ),
            ends_at=datetime(2026, 9, 7, 11, 30, tzinfo=OFFICE_TZ),
        )
        second = service.create_booking(
            user_id=user_id,
            room_name="B",
            title="Second meeting",
            attendees=2,
            starts_at=datetime(2026, 9, 7, 12, 0, tzinfo=OFFICE_TZ),
            ends_at=datetime(2026, 9, 7, 13, 0, tzinfo=OFFICE_TZ),
        )

        graph_builder = StateGraph(MessagesState)
        graph_builder.add_node("tools", ToolNode(build_tools(service, user_id)))
        graph_builder.add_edge(START, "tools")
        graph_builder.add_edge("tools", END)
        graph = graph_builder.compile()

        result = graph.invoke(
            {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "cancel_booking",
                                "args": {"booking_id": first.id},
                                "id": "cancel-first",
                                "type": "tool_call",
                            },
                            {
                                "name": "cancel_booking",
                                "args": {"booking_id": second.id},
                                "id": "cancel-second",
                                "type": "tool_call",
                            },
                        ],
                    )
                ]
            },
            config={"max_concurrency": 1},
        )

        tool_messages = [
            message
            for message in result["messages"]
            if isinstance(message, ToolMessage)
        ]
        assert len(tool_messages) == 2
        assert all(
            message.content.startswith("Status: success")
            for message in tool_messages
        )
        statuses = session.scalars(
            select(BookingModel.status)
            .where(BookingModel.id.in_([first.id, second.id]))
            .order_by(BookingModel.id)
        ).all()
        remaining_slots = session.scalar(
            select(func.count())
            .select_from(BookingSlotModel)
            .where(BookingSlotModel.booking_id.in_([first.id, second.id]))
        )

        assert statuses == ["cancelled", "cancelled"]
        assert remaining_slots == 0
