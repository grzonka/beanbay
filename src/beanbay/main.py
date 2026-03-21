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


@app.get("/health")
def health():
    """Return a simple health check response."""
    return {"status": "ok"}
