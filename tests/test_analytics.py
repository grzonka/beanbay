"""Tests for analytics router — aggregate brew stats and cross-bean recipe comparison."""

import uuid

import pytest

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
def second_bean(db_session):
    """Create a second bean for multi-bean tests."""
    bean = Bean(name="Brazil Natural", roaster="Counter Culture", origin="Brazil")
    db_session.add(bean)
    db_session.commit()
    db_session.refresh(bean)
    return bean


def _seed_shot(
    db_session,
    bean_id: str,
    taste: float = 7.0,
    is_failed: bool = False,
    grind_setting: float = 20.0,
    temperature: float = 93.0,
    preinfusion_pressure_pct: float = 75.0,
    dose_in: float = 19.0,
    target_yield: float = 40.0,
    saturation: str = "yes",
) -> Measurement:
    """Insert a measurement directly into the DB."""
    m = Measurement(
        bean_id=bean_id,
        recommendation_id=str(uuid.uuid4()),
        grind_setting=grind_setting,
        temperature=temperature,
        preinfusion_pressure_pct=preinfusion_pressure_pct,
        dose_in=dose_in,
        target_yield=target_yield,
        saturation=saturation,
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


def test_analytics_no_data(client):
    """GET /analytics with zero shots -> empty state shown."""
    response = client.get("/analytics")
    assert response.status_code == 200
    assert "No shots yet" in response.text
    assert "Start Brewing" in response.text
    # Stats grid should NOT be rendered
    assert "stats-grid" not in response.text


def test_analytics_with_stats(client, sample_bean, db_session):
    """GET /analytics with some shots -> stats card shows correct counts."""
    _seed_shot(db_session, sample_bean.id, taste=7.0)
    _seed_shot(db_session, sample_bean.id, taste=8.5)
    _seed_shot(db_session, sample_bean.id, taste=6.0, is_failed=True)

    response = client.get("/analytics")
    assert response.status_code == 200
    # Total shots: 3 (including failed)
    assert "3" in response.text
    # Best taste: 8.5
    assert "8.5" in response.text
    # Bean name appears in best taste context
    assert "Test Ethiopian" in response.text
    # Failed shot count: 1
    assert "1" in response.text
    # Stats grid rendered
    assert "stats-grid" in response.text


def test_analytics_multiple_beans_comparison(client, sample_bean, second_bean, db_session):
    """GET /analytics with two beans -> comparison shows best recipe per bean, sorted by taste."""
    # Ethiopian: best taste 8.0
    _seed_shot(db_session, sample_bean.id, taste=7.0)
    _seed_shot(db_session, sample_bean.id, taste=8.0)

    # Brazil: best taste 9.0
    _seed_shot(db_session, second_bean.id, taste=6.5)
    _seed_shot(db_session, second_bean.id, taste=9.0)

    response = client.get("/analytics")
    assert response.status_code == 200

    # Both bean names appear
    assert "Test Ethiopian" in response.text
    assert "Brazil Natural" in response.text

    # Comparison section heading
    assert "Best Recipes by Bean" in response.text

    # Brazil (9.0) should appear before Ethiopian (8.0) — check order in HTML
    pos_brazil = response.text.index("Brazil Natural")
    pos_ethiopian = response.text.index("Test Ethiopian")
    assert pos_brazil < pos_ethiopian, "Higher-taste bean should appear first"


def test_analytics_excludes_failed_from_best(client, sample_bean, db_session):
    """Best taste stats must exclude failed shots."""
    # A very high taste score, but it's failed
    _seed_shot(db_session, sample_bean.id, taste=9.9, is_failed=True)
    # Real best: 7.5
    _seed_shot(db_session, sample_bean.id, taste=7.5, is_failed=False)
    _seed_shot(db_session, sample_bean.id, taste=6.0, is_failed=False)

    response = client.get("/analytics")
    assert response.status_code == 200

    # Best taste shown should be 7.5, NOT 9.9
    assert "7.5" in response.text
    assert "9.9" not in response.text


def test_analytics_improvement_rate(client, sample_bean, db_session):
    """With >=10 non-failed shots, improvement_rate shows up/down direction."""
    # Need 20 shots so first 10 and last 10 don't overlap:
    # first 10 at taste 4.0, last 10 at taste 8.0 -> should show up
    for _ in range(10):
        _seed_shot(db_session, sample_bean.id, taste=4.0)
    for _ in range(10):
        _seed_shot(db_session, sample_bean.id, taste=8.0)

    response = client.get("/analytics")
    assert response.status_code == 200

    # Improvement rate arrow should appear
    assert "\u2191" in response.text
    # "first vs last 10" label
    assert "first vs last 10" in response.text


def test_analytics_with_bean_filter(client, sample_bean, second_bean, db_session):
    """GET /analytics?bean_id={id} returns per-bean stats only."""
    _seed_shot(db_session, sample_bean.id, taste=7.0)
    _seed_shot(db_session, sample_bean.id, taste=8.5)
    _seed_shot(db_session, second_bean.id, taste=9.0)

    response = client.get(f"/analytics?bean_id={sample_bean.id}")
    assert response.status_code == 200
    # Should show Ethiopian stats
    assert "Test Ethiopian" in response.text
    # Should NOT show cross-bean comparison heading
    assert "Best Recipes by Bean" not in response.text
    # Stats should reflect only Ethiopian (2 shots)
    assert "2" in response.text


def test_analytics_all_beans_default(client, sample_bean, db_session):
    """GET /analytics without params still shows aggregate (existing behavior)."""
    _seed_shot(db_session, sample_bean.id, taste=7.0)

    response = client.get("/analytics")
    assert response.status_code == 200
    # Cross-bean comparison visible
    assert "Best Recipes by Bean" in response.text


def test_analytics_bean_filter_invalid_id(client, sample_bean, db_session):
    """GET /analytics?bean_id=nonexistent shows empty stats gracefully."""
    _seed_shot(db_session, sample_bean.id, taste=7.0)

    response = client.get("/analytics?bean_id=nonexistent")
    assert response.status_code == 200
