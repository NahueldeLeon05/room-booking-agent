from datetime import datetime

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.tools import build_tools
from app.config import (
    BUSINESS_END,
    BUSINESS_START,
    MAX_BOOKING_HOURS,
    OFFICE_TZ,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    ROOM_CAPACITIES,
    SLOT_MINUTES,
)
from app.services.booking_service import BookingService


def build_graph(
    service: BookingService,
    user_id: int,
) -> CompiledStateGraph:
    tools = build_tools(service, user_id)
    model = ChatOpenAI(
        model=OPENAI_MODEL,
        api_key=OPENAI_API_KEY,
        temperature=0,
    )
    model_with_tools = model.bind_tools(tools)

    def call_agent(state: MessagesState) -> dict[str, list[BaseMessage]]:
        response = model_with_tools.invoke(
            [SystemMessage(content=_system_prompt()), *state["messages"]]
        )
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("agent", call_agent)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")

    return builder.compile()


def _system_prompt() -> str:
    now = datetime.now(OFFICE_TZ).strftime("%Y-%m-%d %H:%M %z")
    rooms = ", ".join(
        f"{name} (capacity {capacity})"
        for name, capacity in ROOM_CAPACITIES.items()
    )
    business_start = BUSINESS_START.strftime("%H:%M")
    business_end = BUSINESS_END.strftime("%H:%M")

    # The prompt improves the conversation but does not enforce these rules.
    # Server-side services validate every argument received through a tool.
    return (
        "You are the conversational room-booking assistant for the Cubo Itaú "
        f"office. The office has {len(ROOM_CAPACITIES)} meeting rooms: {rooms}. "
        f"Business hours are Monday through Friday from {business_start} to "
        f"{business_end}. Bookings use {SLOT_MINUTES}-minute slots and can last "
        f"at most {MAX_BOOKING_HOURS} hours. The current office date and time "
        f"is {now}. Use the available tools when they are needed to answer the "
        "user accurately. Always answer the user in Spanish, even if the user "
        "writes in another language. Before calling create_booking, repeat the "
        "room, date, start and end times, title, and attendee count. Ask the "
        "user to confirm these details and wait for an explicit confirmation. "
        "Do not treat the initial booking request as confirmation. The prompt "
        "only describes the rules for better conversation; tools and "
        "server-side services are responsible for enforcing them."
    )
