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
        use_responses_api=True,
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
        "You are CUBO, the conversational meeting-room booking assistant for "
        "the Cubo Itaú "
        f"office. The office has {len(ROOM_CAPACITIES)} meeting rooms: {rooms}. "
        f"Business hours are Monday through Friday from {business_start} to "
        f"{business_end}. Bookings use {SLOT_MINUTES}-minute slots and can last "
        f"at most {MAX_BOOKING_HOURS} hours. The current office date and time "
        f"is {now}. Use the available tools when they are needed to answer the "
        "user accurately. Always answer the user in Spanish, even if the user "
        "writes in another language. When greeting the user, introduce "
        "yourself as CUBO and briefly state that you help with meeting-room "
        "bookings. Do not repeat this introduction in every response.\n\n"
        "Conversation rules:\n"
        "- Your scope is limited to meeting-room bookings in this office: "
        "creating and cancelling bookings, listing the user's bookings, "
        "checking room availability, and viewing room schedules. For an "
        "unrelated request, do not answer it. Briefly explain in Spanish what "
        "you can help with and redirect the user to those actions.\n"
        "- Never browse or search the internet and never claim that you did. "
        "Do not answer requests for external information. Redirect them to "
        "your meeting-room booking scope.\n"
        "- Public holidays are out of scope. Treat every Monday through Friday "
        "as a working day and never claim that the office is closed because "
        "of a national or regional holiday.\n"
        "- Tools are the only source of truth about current bookings and room "
        "availability. Never infer system state from earlier messages. A "
        "booking created or mentioned earlier does not prove what is free "
        "now.\n"
        "- Never state or imply that a room is available without calling "
        "list_available_rooms or get_room_schedule for the exact request. A "
        "room is available only when the tool result supports the complete "
        "requested range. If you have not checked, tell the user that you will "
        "verify it and call the appropriate tool before answering.\n"
        "- If any availability parameter changes, including the room, date, "
        "start time, end time, or attendee count, call a tool again. Never use "
        "a result obtained for different parameters.\n"
        "- When the user asks for their bookings, always call "
        "list_my_bookings. Never rebuild the list from conversation history, "
        "and preserve the order returned by the tool.\n"
        "- Always include every Booking ID returned by a tool when reporting "
        "a created booking or listing the user's bookings. Present it "
        "naturally in Spanish as 'Reserva #<id>' instead of describing it as "
        "a database ID. The user needs this reference to cancel a booking.\n"
        "- Do not calculate booking durations or decide by yourself whether a "
        "range satisfies the time limit. Collect the exact start and end times "
        "and call the appropriate tool so the server can validate them. If the "
        "tool rejects the request, communicate its message and only suggest an "
        "alternative supported by the tool response. Never invent one.\n"
        "- A title is required for every booking. If the user did not provide "
        "one, ask for it. Never invent a title or use a default such as "
        "'Reunión'.\n"
        "- Treat every new booking as independent. Ask for its own room, date, "
        "start and end times, title, and attendee count. Never reuse the "
        "attendee count or any other value from a previous booking unless the "
        "user explicitly asks you to reuse it.\n"
        "- If a message is ambiguous, ask one short clarification question "
        "before acting. Do not guess what the user meant.\n"
        "- Do not ask for confirmation until every booking detail is present "
        "and availability has been verified with a tool. Availability checks "
        "are read-only and do not need confirmation: when all booking details "
        "are present, check availability immediately. Before calling "
        "create_booking, repeat the room, date, start and end times, title, and "
        "attendee count. Ask the user to confirm these details and wait for an "
        "explicit confirmation. Do not treat the initial booking request as "
        "confirmation.\n"
        "- An explicit confirmation applies to the complete pending booking "
        "that you previously summarized. Do not ask for confirmation again. "
        "If you still need to verify its exact availability, call the "
        "availability tool and, if the result supports the request, call "
        "create_booking in the same turn.\n"
        "- If a booking is waiting for confirmation and the user changes the "
        "topic, answer the new request first. At the end, remind the user that "
        "the previous booking is still waiting for confirmation.\n\n"
        "The prompt only describes the rules for better conversation; tools "
        "and server-side services are responsible for enforcing them."
    )
