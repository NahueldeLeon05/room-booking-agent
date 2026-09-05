from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.bookings import router as bookings_router
from app.infrastructure.database import init_db
from app.infrastructure.seed import seed


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Initialize the database before the application starts serving requests."""
    init_db()
    seed()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)
app.include_router(bookings_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
