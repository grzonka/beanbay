"""BeanBay — FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.routers import analytics, beans, brew, equipment, history, insights
from app.routers.beans import _get_active_bean
from app.services.migration import (
    migrate_campaigns_to_db,
    migrate_legacy_campaign_files,
    migrate_pending_to_db,
)
from app.services.optimizer import OptimizerService

# Import models so they're registered with Base
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    import logging as _logging

    _log = _logging.getLogger(__name__)

    # Startup: ensure data directory exists
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    # Create tables if they don't exist (no-op if Alembic already ran)
    Base.metadata.create_all(bind=engine)

    # Rename legacy campaign files (bare bean_id → new key format) before DB migration
    campaigns_dir = settings.data_dir / "campaigns"
    _migrated_files = migrate_legacy_campaign_files(campaigns_dir)
    if _migrated_files:
        _log.info("Renamed %d legacy campaign file(s) to new key format", _migrated_files)

    # Migrate campaign files from disk into DB (idempotent)
    _migrated_campaigns = migrate_campaigns_to_db(SessionLocal, campaigns_dir)
    if _migrated_campaigns:
        _log.info("Migrated %d campaign(s) from disk to DB", _migrated_campaigns)

    # Migrate pending recommendations from disk into DB (idempotent)
    _migrated_pending = migrate_pending_to_db(SessionLocal, settings.data_dir)
    if _migrated_pending:
        _log.info("Migrated %d pending recommendation(s) from disk to DB", _migrated_pending)

    # Initialize optimizer service with DB-backed session factory
    app.state.optimizer = OptimizerService(SessionLocal)

    yield
    # Shutdown: nothing to clean up


app = FastAPI(title="BeanBay", lifespan=lifespan)

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir, check_dir=False), name="static")

# Include routers
app.include_router(beans.router)
app.include_router(brew.router)
app.include_router(equipment.router)
app.include_router(history.router)
app.include_router(insights.router)
app.include_router(analytics.router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "beanbay"}


templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, db: Session = Depends(get_db)):
    """Show welcome page if no beans exist, otherwise show the home dashboard."""
    from app.models.bean import Bean
    from app.models.brew_setup import BrewSetup
    from app.models.measurement import Measurement

    bean_count = db.query(Bean).count()
    if bean_count == 0:
        return templates.TemplateResponse(request, "welcome.html")

    # --- Aggregate stats ---
    total_brews = db.query(Measurement).count()
    total_beans = bean_count

    avg_taste = None
    best_taste = None
    best_bean_name = None

    if total_brews > 0:
        non_failed_tastes = (
            db.query(Measurement.taste, Measurement.bean_id)
            .filter(Measurement.is_failed.is_(False))
            .all()
        )
        if non_failed_tastes:
            avg_taste = round(
                sum(row.taste for row in non_failed_tastes) / len(non_failed_tastes), 1
            )
            best_row = max(non_failed_tastes, key=lambda r: r.taste)
            best_taste = best_row.taste
            best_bean = db.query(Bean).filter(Bean.id == best_row.bean_id).first()
            best_bean_name = best_bean.name if best_bean else "Unknown"

    stats = {
        "total_brews": total_brews,
        "total_beans": total_beans,
        "avg_taste": avg_taste,
        "best_taste": best_taste,
        "best_bean_name": best_bean_name,
    }

    # --- Recent brews (last 5) ---
    from sqlalchemy.orm import joinedload

    recent_measurements = (
        db.query(Measurement)
        .options(joinedload(Measurement.bean), joinedload(Measurement.brew_setup))
        .order_by(Measurement.created_at.desc())
        .limit(5)
        .all()
    )

    recent_brews = []
    for m in recent_measurements:
        brew_method = "espresso"
        brew_setup_name = None
        if m.brew_setup:
            brew_setup_name = m.brew_setup.name
            if m.brew_setup.brew_method:
                brew_method = m.brew_setup.brew_method.name
        recent_brews.append(
            {
                "id": m.id,
                "bean_name": m.bean.name if m.bean else "",
                "taste": m.taste,
                "grind_setting": m.grind_setting,
                "is_failed": m.is_failed,
                "is_manual": getattr(m, "is_manual", False) or False,
                "created_at": m.created_at,
                "brew_method": brew_method,
                "brew_setup_name": brew_setup_name,
            }
        )

    # --- Active bean info ---
    active_bean = _get_active_bean(request, db)
    active_bean_shots = None
    active_bean_best = None
    if active_bean:
        active_bean_shots = (
            db.query(func.count(Measurement.id))
            .filter(Measurement.bean_id == active_bean.id)
            .scalar()
            or 0
        )
        best_non_failed = (
            db.query(func.max(Measurement.taste))
            .filter(Measurement.bean_id == active_bean.id, Measurement.is_failed.is_(False))
            .scalar()
        )
        active_bean_best = best_non_failed

    # --- Equipment counts ---
    setup_count = db.query(BrewSetup).filter(BrewSetup.is_retired.is_(False)).count()

    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "active_bean": active_bean,
            "stats": stats,
            "recent_brews": recent_brews,
            "active_bean_shots": active_bean_shots,
            "active_bean_best": active_bean_best,
            "setup_count": setup_count,
        },
    )
