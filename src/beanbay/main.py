from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from beanbay.config import settings
from beanbay.routers.lookup import (
    bean_variety_router,
    brew_method_router,
    flavor_tag_router,
    origin_router,
    process_method_router,
    roaster_router,
    stop_mode_router,
    storage_type_router,
    vendor_router,
)
from beanbay.routers.beans import router as beans_router
from beanbay.routers.brew_setups import router as brew_setups_router
from beanbay.routers.brews import router as brews_router
from beanbay.routers.equipment import router as equipment_router
from beanbay.routers.people import router as people_router
from beanbay.routers.ratings import router as ratings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    Run Alembic migrations to head, then seed default lookup data
    and the default person record.

    Parameters
    ----------
    app : FastAPI
        The FastAPI application instance.
    """
    from alembic import command
    from alembic.config import Config as AlembicConfig

    from beanbay.database import engine
    from beanbay.seed import seed_brew_methods, seed_default_person, seed_stop_modes

    alembic_cfg = AlembicConfig("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    with Session(engine) as session:
        seed_brew_methods(session)
        seed_stop_modes(session)
        seed_default_person(session, settings.default_person_name)
        session.commit()
    yield


app = FastAPI(title="BeanBay", lifespan=lifespan)

_routers = [
    flavor_tag_router, origin_router, roaster_router,
    process_method_router, bean_variety_router,
    brew_method_router, stop_mode_router,
    vendor_router, storage_type_router,
    people_router, equipment_router, beans_router,
    brew_setups_router, brews_router, ratings_router,
]
for _router in _routers:
    app.include_router(_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    """Return a simple health check response."""
    return {"status": "ok"}
