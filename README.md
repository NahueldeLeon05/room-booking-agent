# CUBO — Room Booking Agent

A conversational assistant for booking meeting rooms at Cubo Itaú, with tool
calling and server-side validation.

## Live demo

[Open the deployed Streamlit application](https://room-booking-ui-production.up.railway.app/)

| Username | Password |
|---|---|
| `User1` or `User2` | `TechnicalChallengePromtior` |

## Ejemplos de uso

> ¿Qué salas están disponibles el próximo lunes de 10:00 a 12:00 para 6 personas?

> Reservá la sala C con el título "Entrevista".

## Stack

| Area | Technology |
|---|---|
| API | Python, FastAPI, Uvicorn |
| Agent | LangGraph, OpenAI API |
| Persistence | SQLAlchemy, SQLite |
| Authentication | JWT, Passlib, bcrypt |
| Interface | Streamlit |
| Deployment | Railway |

## Run locally

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/NahueldeLeon05/room-booking-agent.git
cd room-booking-agent
python -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Or on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the application and test dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Set the required environment variables. The values below are placeholders for
the real secrets.

macOS or Linux:

```bash
export SEED_USER_PASSWORD="TechnicalChallengePromtior"
export JWT_SECRET="<generate-a-long-random-secret>"
export OPENAI_API_KEY="<your-openai-api-key>"
```

Windows PowerShell:

```powershell
$env:SEED_USER_PASSWORD = "TechnicalChallengePromtior"
$env:JWT_SECRET = "<generate-a-long-random-secret>"
$env:OPENAI_API_KEY = "<your-openai-api-key>"
```

The remaining variables are optional for local development:

| Variable | Default |
|---|---|
| `DATABASE_URL` | `sqlite:///./app.db` |
| `OPENAI_MODEL` | `gpt-5.6-terra` |
| `API_BASE_URL` | `http://localhost:8000` |

Start the API:

```bash
uvicorn app.main:app --reload
```

The API documentation is available at <http://127.0.0.1:8000/docs>.

In a second terminal, activate the same virtual environment and start the UI:

```bash
streamlit run ui/app.py
```

Streamlit opens at <http://localhost:8501>.

## Tests and evaluations

Run the deterministic test suite:

```bash
python -m pytest
```

Agent evaluations are separate from pytest because they use real OpenAI
responses, consume tokens, and are not deterministic:

```bash
python -m evals.run
```

See [evals/README.md](evals/README.md) for the cases and recorded model
comparison.

## Repository structure

- `app/` — domain rules, services, persistence, API, and LangGraph agent.
- `ui/` — Streamlit login and conversational interface.
- `tests/` — deterministic domain, service, infrastructure, API, and UI tests.
- `evals/` — real-model conversational evaluation cases and runner.
- `doc/` — assumptions, data model, business rules, architecture, and journal.

## Documentation

Start with the [project overview and component diagram](doc/00-overview.md).
The [technology notebook](notebook.ipynb) explains the stack with code from
this project.
