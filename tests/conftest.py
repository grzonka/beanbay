import pytest
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

import beanbay.models  # noqa: F401 — register all models with metadata
from beanbay.database import get_session
from beanbay.main import app


@pytest.fixture(name="engine", scope="session")
def engine_fixture():
    """Create a shared in-memory SQLite engine for the test session."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    """Provide a transactional session with SAVEPOINT isolation.

    Each test gets a session that rolls back all changes after the test
    completes, ensuring full isolation without mocks.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(name="client")
def client_fixture(session):
    """Provide a FastAPI TestClient wired to the transactional session."""
    from fastapi.testclient import TestClient

    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
