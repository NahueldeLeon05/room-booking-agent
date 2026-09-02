# Purpose
This journal records the work completed each day, the decisions made, the obstacles encountered, and how they were resolved during the seven-day challenge.

## Entries

## 2026-08-31 — Day 1: Setup and stack selection

**Done**

- Repository created (`room-booking-agent`), Python virtual environment, and `.gitignore`.
- Stack selected and OpenAI API key configured through an environment variable.

**Decisions**

- OpenAI was selected over Ollama and Groq because I already had API credits, the specification presents it as the first option, and it avoids the cloud RAM requirements that the specification warns about for Ollama.
- FastAPI, SQLAlchemy, and LangGraph were selected as the standard Python stack for the API, persistence, and agent workflow. LangGraph also keeps the implementation within the LangChain ecosystem suggested by the specification.

**Obstacles**

- None.

## 2026-09-01 — Day 2: Interaction model

**Done**

- Exploratory UI mockup created in Claude Design.
- Documentation skeletons created for files `01` through `06`.
- Project assumptions documented in `01-assumptions.md`.

**Obstacle**

- The mockup presented rooms as cards and time slots as buttons. When I reviewed it, I realized that the user had to click to advance through the booking flow instead of continuing the conversation through natural language.

**Resolution**

- Use text-only responses with no interactive components. The conversation advances entirely through natural language.
- If the user has to click to advance, the result is a form with a chat interface placed on top rather than a conversational interface.

**Impact**

- Tools must return information that the model can verbalize, not structures designed to be rendered.
- Bookings need short, human-referenceable identifiers because the user has to name one in the conversation to cancel it.

