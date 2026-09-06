# Project overview

I built a meeting-room booking assistant for Cubo Itaú. The stack is Python,
FastAPI, SQLAlchemy with SQLite, LangGraph for the agent, the OpenAI API for the
model, Streamlit for the interface, and Railway for hosting. My goal was to
build a well-separated system where the chatbot could be removed and the
booking system would still work.

Business rules are validated in the backend, never in the prompt. The user ID
comes from the authenticated session and is never provided by the model,
preventing a hallucination from operating on another user's bookings. Booking
overlaps are prevented by a unique database constraint instead of a check in
application code.

I wanted to build something well thought out, with clear tests, golden cases,
agent evaluations, and a model comparison. The main challenges were deploying
to Railway for the first time, including problems with persistent volumes;
using Streamlit for the first interface; and, especially, controlling the
model's behavior. During manual testing, the model treated the conversation as
a source of truth and sometimes invented restrictions that did not exist. I
turned those failures into repeatable evaluation cases instead of continuing
to test them only by hand.

Another problem appeared when a user requested two cancellations in one
message. LangGraph tried to execute both tools in parallel while they shared
the same SQLAlchemy session, causing one operation to fail halfway. I
serialized tool calls inside each request and added a test that verifies that
both bookings are cancelled without leaving occupied slots behind.

I ran the same 16 evaluation cases three times with each model.
`gpt-5.6-terra` passed 48 out of 48 cases, while `gpt-4o-mini` passed 45 out of
48. The smaller model failed the exact three-hour booking boundary in every
run, which gave me a concrete reason to select Terra for the deployed demo.

Public holidays, recurring bookings, booking edits, and notifications are
outside the scope of this solution. They were not required for the core booking
flow and would introduce additional rules and infrastructure that do not
contribute to the main goal of the challenge.

I first designed the interface with cards and time-slot buttons in Claude
Design. After reviewing it, I realized that it behaved like a form with a chat
placed on top. I removed those controls and kept the booking flow entirely in
natural language.

## Component diagram

<!-- Add the diagram showing the flow from the interface to the response. -->

Further documentation: [assumptions](01-assumptions.md), [data model](02-data-model.md), [business rules](03-business-rules.md), [architecture](04-architecture.md), [tool contracts](05-tool-contracts.md), and [development journal](06-journal.md).
