from contextlib import asynccontextmanager

from fastapi import FastAPI

from beanbay.routers.lookup import (
    bean_variety_router,
    brew_method_router,
    flavor_tag_router,
    origin_router,
    process_method_router,
    roaster_router,
    stop_mode_router,
)
from beanbay.routers.beans import router as beans_router
from beanbay.routers.equipment import router as equipment_router
from beanbay.routers.people import router as people_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    Parameters
    ----------
    app : FastAPI
        The FastAPI application instance.
    """
    # TODO: Alembic migrations, seeding
    yield


app = FastAPI(title="BeanBay", lifespan=lifespan)

# Lookup-table routers
for _router in (
    flavor_tag_router,
    origin_router,
    roaster_router,
    process_method_router,
    bean_variety_router,
    brew_method_router,
    stop_mode_router,
):
    app.include_router(_router, prefix="/api/v1")

# People router
app.include_router(people_router, prefix="/api/v1")

# Equipment router
app.include_router(equipment_router, prefix="/api/v1")

# Beans router
app.include_router(beans_router, prefix="/api/v1")


@app.get("/health")
def health():
    """Return a simple health check response."""
    return {"status": "ok"}
