# Purpose
This journal records the work completed each day, the decisions made, the obstacles encountered, and how they were resolved during the seven-day challenge.

## Entries

### 2026-08-31 — Day 1: Setup and stack selection

**Done**

- Repository created (`room-booking-agent`), Python virtual environment, and `.gitignore`.
- Stack selected and OpenAI API key configured through an environment variable.

**Decisions**

- OpenAI was selected over Ollama and Groq because I already had API credits, the specification presents it as the first option, and it avoids the cloud RAM requirements that the specification warns about for Ollama.
- FastAPI, SQLAlchemy, and LangGraph were selected as the standard Python stack for the API, persistence, and agent workflow. LangGraph also keeps the implementation within the LangChain ecosystem suggested by the specification.

**Obstacles**

- None.

### 2026-09-01 — Day 2: Interaction model

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

### 2026-09-02 — Day 3: Persistence and early deployment

**Done**

- ORM models, configuration, database session, idempotent seed.
- Minimal FastAPI app with /health.
- Deployed to Railway with a persistent volume.
- Refactored `init_db()` and `seed()` to accept an isolated engine or session for tests while keeping their default behavior.
- Added four persistence tests for schema creation, seed data, seed idempotency, and duplicate room slots.
- Verified that the database rejects two bookings that try to hold the same room and time slot.
- Enabled SQLite foreign key enforcement and verified that rows with missing parents are rejected.
- Documented the remaining booking assumptions in `01-assumptions.md`.
- Documented the data model, concurrency strategy, and business-rule catalogue.

**Obstacles**

- Railpack did not detect the deprecated Procfile, so the deployment had no start command.
- First deploy crashed in init_db(): DATABASE_URL pointed to /data but
  no volume was mounted yet.

**Resolution**

- Replaced the Procfile with `railpack.json`, which keeps the start command versioned in the repository.
- Mounted a Railway volume at `/data` and configured `DATABASE_URL` to use `/data/app.db`.

### 2026-09-05 — Day 4: Domain, service layer and first agent

**Done**

- Added the `TimeRange` value object with half-open interval semantics.
- Added JWT authentication. The `user_id` is resolved only from the token.
- Added the booking domain entity, repository, service, and listing endpoint.
- Added booking-rule validation with explicit boundary tests.
- Added booking creation, cancellation, availability, and room schedule queries.
- Added a LangGraph agent with one tool and tested the full flow from Swagger.
- Reached 66 passing tests.

**Decisions**

- Access tokens expire after 24 hours. This is enough for the demo and limits the lifetime of a leaked token.
- Built the agent with one tool before implementing the rest to validate the loop early. This follows the same reasoning as the early deployment.
- The `user_id` is injected through a closure and is never exposed as a tool parameter. The model cannot choose another identity.
- Booking creation inserts without a prior availability query. The database unique constraint decides the conflict and prevents a check-then-act window.
- A booking that does not belong to the user returns `BookingNotFound`, just like a missing booking. This does not reveal the existence of other users' bookings.
- Test-only dependencies live in `requirements-dev.txt`, so Railway does not install them in production.

**Obstacles**

- The application failed during local startup when `JWT_SECRET` and `SEED_USER_PASSWORD` were missing.
- SQLite returned stored datetimes without timezone information.
- While testing the real conversation, I asked the agent to cancel two
  bookings in one message. LangGraph tried to run both tools at the same time.
  Both tools shared the same SQLAlchemy session, so one cancellation failed
  halfway and left its slots behind. The same problem could happen when a user
  asks to create or cancel several bookings in one message.

**Resolution**

- Kept the environment variables required and configured them locally and in Railway.
- The repository restores `OFFICE_TZ` when mapping database values to the domain.
- Tool calls now run one at a time inside each chat request. This avoids using
  the same session from two threads, similar to not sharing one `DbContext`
  between parallel operations. I added a test that cancels two bookings in one
  turn and verifies that both bookings are cancelled and no slots are left
  behind.
- Requests from different users are still independent. The database
  `UNIQUE(room_id, slot_start)` constraint continues to handle conflicts
  between simultaneous booking requests.

**Dependencies**

- `python-jose[cryptography]` signs and validates JWT access tokens.
- `httpx` is used only by FastAPI's `TestClient` during tests.
- `langgraph` manages the agent and tool loop.
- `langchain-openai` connects the agent to OpenAI.
