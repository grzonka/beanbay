"""Shared test fixtures for BrewFlow."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Bean, Measurement  # noqa: F401 — registers models with Base
from app.services.optimizer import OptimizerService


@pytest.fixture(scope="session")
def db_engine():
    """Session-scoped in-memory SQLite engine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Function-scoped database session with rollback after each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture()
def tmp_campaigns_dir(tmp_path: Path) -> Path:
    """Temporary campaigns directory."""
    d = tmp_path / "campaigns"
    d.mkdir()
    return d


@pytest.fixture()
def optimizer_service(tmp_campaigns_dir: Path) -> OptimizerService:
    """OptimizerService with temporary storage."""
    return OptimizerService(tmp_campaigns_dir)
