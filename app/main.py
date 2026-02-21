"""BrewFlow — FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.routers import beans
from app.services.optimizer import OptimizerService

# Import models so they're registered with Base
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    # Startup: ensure directories exist
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.campaigns_dir  # property creates dir on access

    # Create tables if they don't exist (no-op if Alembic already ran)
    Base.metadata.create_all(bind=engine)

    # Initialize optimizer service
    app.state.optimizer = OptimizerService(settings.campaigns_dir)

    yield
    # Shutdown: nothing to clean up


app = FastAPI(title="BrewFlow", lifespan=lifespan)

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir, check_dir=False), name="static")

# Include routers
app.include_router(beans.router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "brewflow"}


@app.get("/")
async def root():
    """Redirect to bean list — the home screen."""
    return RedirectResponse(url="/beans", status_code=303)
