"""Tests for insights router — optimization progress, convergence, and trust signals."""

import uuid

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models.bean import Bean
from app.models.measurement import Measurement


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    """FastAPI test client."""
    return TestClient(app, follow_redirects=False)


@pytest.fixture()
def db():
    """Direct DB session for test setup."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def sample_bean(db):
    """Create a sample bean."""
    bean = Bean(name="Test Ethiopian", roaster="Onyx", origin="Yirgacheffe")
    db.add(bean)
    db.commit()
    db.refresh(bean)
    return bean


@pytest.fixture()
def mock_optimizer():
    """Patch app.state.optimizer with a mock that satisfies insights route needs."""
    from baybe.recommenders.pure.nonpredictive.sampling import RandomRecommender
    from baybe.recommenders import TwoPhaseMetaRecommender

    # Build a real RandomRecommender so isinstance checks work
    random_rec = RandomRecommender()

    mock_campaign = MagicMock()
    mock_campaign.recommender = MagicMock(spec=TwoPhaseMetaRecommender)
    mock_campaign.recommender.select_recommender.return_value = random_rec
    mock_campaign.searchspace = MagicMock()
    mock_campaign.objective = MagicMock()
    mock_campaign.measurements = MagicMock()

    mock_opt = MagicMock()
    mock_opt.get_or_create_campaign.return_value = mock_campaign

    original_optimizer = getattr(app.state, "optimizer", None)
    app.state.optimizer = mock_opt
    yield mock_opt
    # Restore
    if original_optimizer is not None:
        app.state.optimizer = original_optimizer


def _seed_shot(
    db,
    bean_id: str,
    taste: float = 7.0,
    is_failed: bool = False,
) -> Measurement:
    """Insert a measurement directly into the DB."""
    m = Measurement(
        bean_id=bean_id,
        recommendation_id=str(uuid.uuid4()),
        grind_setting=20.0,
        temperature=93.0,
        preinfusion_pct=75.0,
        dose_in=19.0,
        target_yield=40.0,
        saturation="yes",
        taste=taste,
        is_failed=is_failed,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_insights_requires_active_bean(client, mock_optimizer):
    """GET /insights without active bean cookie → redirect to /beans (303)."""
    response = client.get("/insights")
    assert response.status_code == 303
    assert response.headers["location"] == "/beans"


def test_insights_empty_bean(client, sample_bean, mock_optimizer):
    """GET /insights with active bean that has 0 measurements → shows 'Getting started'."""
    client.cookies.set("active_bean_id", sample_bean.id)
    response = client.get("/insights")
    assert response.status_code == 200
    # Shows bean name
    assert "Test Ethiopian" in response.text
    # Shows 0 shots
    assert "0 shots" in response.text
    # Shows getting started convergence status
    assert "Getting started" in response.text
    # No chart canvas (not enough data)
    assert "progressChart" not in response.text


def test_insights_with_measurements(client, sample_bean, db, mock_optimizer):
    """Create bean + 3 measurements, GET /insights → shows convergence status, shot count, best taste."""
    _seed_shot(db, sample_bean.id, taste=6.5)
    _seed_shot(db, sample_bean.id, taste=7.5)
    _seed_shot(db, sample_bean.id, taste=8.0)

    client.cookies.set("active_bean_id", sample_bean.id)
    response = client.get("/insights")
    assert response.status_code == 200
    # Shot count
    assert "3 shots" in response.text
    # Best taste shown
    assert "8.0" in response.text
    # Convergence label (3 shots → "Early exploration")
    assert "Early exploration" in response.text
    # Bean name
    assert "Test Ethiopian" in response.text


def test_insights_chart_data_present(client, sample_bean, db, mock_optimizer):
    """Create bean + 3 measurements, GET /insights → response contains 'progressChart' canvas element."""
    _seed_shot(db, sample_bean.id, taste=6.0)
    _seed_shot(db, sample_bean.id, taste=7.0)
    _seed_shot(db, sample_bean.id, taste=8.0)

    client.cookies.set("active_bean_id", sample_bean.id)
    response = client.get("/insights")
    assert response.status_code == 200
    # Chart canvas rendered
    assert "progressChart" in response.text
    # Chart.js CDN loaded
    assert "chart.js" in response.text.lower()


def test_insights_convergence_early_exploration(client, sample_bean, db, mock_optimizer):
    """Bean with 4 non-failed measurements → 'Early exploration' status."""
    for taste in [6.0, 6.5, 7.0, 7.5]:
        _seed_shot(db, sample_bean.id, taste=taste)

    client.cookies.set("active_bean_id", sample_bean.id)
    response = client.get("/insights")
    assert response.status_code == 200
    assert "Early exploration" in response.text
    # 4 shots recorded
    assert "4 shots" in response.text


def test_insights_nav_link(client, mock_optimizer):
    """GET /beans → response contains href='/insights' nav link."""
    response = client.get("/beans")
    assert response.status_code == 200
    assert 'href="/insights"' in response.text
