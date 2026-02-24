"""Shared test fixtures for BeanBay."""

import os

# Force in-memory SQLite for the production engine (created at import time in app.database).
# This prevents CI failures when data/ directory doesn't exist.
# Must be set BEFORE importing app modules.
os.environ.setdefault("BEANBAY_DATABASE_URL", "sqlite:///:memory:")

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import Base, engine, get_db
from app.main import app
from app.models import Bean, BrewMethod, BrewSetup, Brewer, Grinder, Measurement, Paper, WaterRecipe  # noqa: F401 — registers models with Base
from app.models import Bag  # noqa: F401 — registers Bag with Base
from app.models import CampaignState, PendingRecommendation  # noqa: F401 — registers with Base
from app.services.optimizer import OptimizerService

# Create tables once on the (in-memory) engine.
Base.metadata.create_all(bind=engine)


@pytest.fixture()
def db_session():
    """Function-scoped database session with rollback after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """FastAPI test client with get_db overridden to use the test session."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def tmp_campaigns_dir(tmp_path: Path) -> Path:
    """Temporary campaigns directory."""
    d = tmp_path / "campaigns"
    d.mkdir()
    return d


@pytest.fixture()
def optimizer_service(db_session) -> OptimizerService:
    """OptimizerService with test DB session factory."""

    def _test_session_factory():
        return db_session

    return OptimizerService(_test_session_factory)
