"""Tests for insights router — optimization progress, convergence, and trust signals."""

import uuid

import pytest
from unittest.mock import MagicMock

from app.main import app
from app.models.bean import Bean
from app.models.measurement import Measurement


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_bean(db_session):
    """Create a sample bean."""
    bean = Bean(name="Test Ethiopian", roaster="Onyx", origin="Yirgacheffe")
    db_session.add(bean)
    db_session.commit()
    db_session.refresh(bean)
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
    db_session,
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
        preinfusion_pressure_pct=75.0,
        dose_in=19.0,
        target_yield=40.0,
        saturation="yes",
        taste=taste,
        is_failed=is_failed,
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    return m


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_insights_requires_active_bean(client, mock_optimizer):
    """GET /insights without active bean cookie -> redirect to /beans (303)."""
    response = client.get("/insights", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/beans"


def test_insights_empty_bean(client, sample_bean, mock_optimizer):
    """GET /insights with active bean that has 0 measurements -> shows 'Getting started'."""
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


def test_insights_with_measurements(client, sample_bean, db_session, mock_optimizer):
    """Create bean + 3 measurements, GET /insights -> shows convergence status, shot count, best taste."""
    _seed_shot(db_session, sample_bean.id, taste=6.5)
    _seed_shot(db_session, sample_bean.id, taste=7.5)
    _seed_shot(db_session, sample_bean.id, taste=8.0)

    client.cookies.set("active_bean_id", sample_bean.id)
    response = client.get("/insights")
    assert response.status_code == 200
    # Shot count
    assert "3 shots" in response.text
    # Best taste shown
    assert "8.0" in response.text
    # Convergence label (3 shots -> "Early exploration")
    assert "Early exploration" in response.text
    # Bean name
    assert "Test Ethiopian" in response.text


def test_insights_chart_data_present(client, sample_bean, db_session, mock_optimizer):
    """Create bean + 3 measurements, GET /insights -> response contains 'progressChart' canvas element."""
    _seed_shot(db_session, sample_bean.id, taste=6.0)
    _seed_shot(db_session, sample_bean.id, taste=7.0)
    _seed_shot(db_session, sample_bean.id, taste=8.0)

    client.cookies.set("active_bean_id", sample_bean.id)
    response = client.get("/insights")
    assert response.status_code == 200
    # Chart canvas rendered
    assert "progressChart" in response.text
    # Chart.js CDN loaded
    assert "chart.js" in response.text.lower()


def test_insights_convergence_early_exploration(client, sample_bean, db_session, mock_optimizer):
    """Bean with 4 non-failed measurements -> 'Early exploration' status."""
    for taste in [6.0, 6.5, 7.0, 7.5]:
        _seed_shot(db_session, sample_bean.id, taste=taste)

    client.cookies.set("active_bean_id", sample_bean.id)
    response = client.get("/insights")
    assert response.status_code == 200
    assert "Early exploration" in response.text
    # 4 shots recorded
    assert "4 shots" in response.text


def test_insights_nav_link(client, mock_optimizer):
    """GET /beans -> response contains href='/insights' nav link."""
    response = client.get("/beans")
    assert response.status_code == 200
    assert 'href="/insights"' in response.text


# ---------------------------------------------------------------------------
# Heatmap tests
# ---------------------------------------------------------------------------


def test_insights_heatmap_no_data(client, sample_bean, db_session, mock_optimizer):
    """Bean with < 3 shots -> heatmap shows empty state message, not chart canvas."""
    # Seed 2 shots (below the 3-shot threshold)
    _seed_shot(db_session, sample_bean.id, taste=6.5)
    _seed_shot(db_session, sample_bean.id, taste=7.0)

    client.cookies.set("active_bean_id", sample_bean.id)
    response = client.get("/insights")
    assert response.status_code == 200
    # Heatmap empty state shown
    assert "Pull at least 3 shots to see the parameter map." in response.text
    # Heatmap canvas NOT present
    assert "heatmapChart" not in response.text


def test_insights_heatmap_with_data(client, sample_bean, db_session, mock_optimizer):
    """Bean with 4+ shots -> heatmap chart rendered with correct canvas and section title."""
    _seed_shot(db_session, sample_bean.id, taste=5.0)
    _seed_shot(db_session, sample_bean.id, taste=7.5)
    _seed_shot(db_session, sample_bean.id, taste=8.5)
    _seed_shot(db_session, sample_bean.id, taste=9.0)

    client.cookies.set("active_bean_id", sample_bean.id)
    response = client.get("/insights")
    assert response.status_code == 200
    # Heatmap canvas rendered
    assert "heatmapChart" in response.text
    # Section title present
    assert "Parameter Map" in response.text
    # Grind and temperature values from seeded measurements appear in heatmap_data JSON blob
    assert '"x": 20.0' in response.text
    assert '"y": 93.0' in response.text


def test_insights_heatmap_failed_shots_distinct(client, sample_bean, db_session, mock_optimizer):
    """Bean with normal + failed shots -> heatmap_data JSON includes a point with is_failed: true."""
    _seed_shot(db_session, sample_bean.id, taste=7.0, is_failed=False)
    _seed_shot(db_session, sample_bean.id, taste=8.0, is_failed=False)
    _seed_shot(db_session, sample_bean.id, taste=9.0, is_failed=False)
    _seed_shot(db_session, sample_bean.id, taste=1.0, is_failed=True)

    client.cookies.set("active_bean_id", sample_bean.id)
    response = client.get("/insights")
    assert response.status_code == 200
    # The heatmap canvas is present (4 shots total)
    assert "heatmapChart" in response.text
    # The JSON data blob contains a failed point
    assert '"is_failed": true' in response.text
