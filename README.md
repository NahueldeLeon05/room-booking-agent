# room-booking-agent
Conversational meeting-room booking assistant with LLM tool calling. FastAPI + LangGraph.

## Deployment

The application is deployed on Railway with a persistent volume mounted at `/data`. Set `DATABASE_URL=sqlite:////data/app.db` and configure `SEED_USER_PASSWORD` in the Railway environment.

Database initialization and seeding run when the application starts because Railway mounts the persistent volume at container startup, not during the build.
