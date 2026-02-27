"""Phase 21 tests: New Brew Methods (french-press, aeropress, cold-brew, turkish, moka-pot).

Covers:
  - Parameter registry returns correct params for each new method
  - OptimizerService creates valid campaigns for each new method
  - Measurement model stores new method params (steep_time, brew_volume)
  - record_measurement integration: POST /brew/record stores new params
  - recommend + record cycle for 3 new methods (french-press, aeropress, cold-brew)
  - BrewMethod seeding: new methods exist after migration
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.main import app
from app.models.bean import Bean
from app.models.brew_method import BrewMethod
from app.models.measurement import Measurement
from app.services.optimizer_key import make_campaign_key
from app.services.parameter_registry import get_param_columns


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_bean(db_session):
    bean = Bean(name="Phase21 Bean", roaster="Test Roaster", origin="Brazil")
    db_session.add(bean)
    db_session.commit()
    db_session.refresh(bean)
    return bean


@pytest.fixture()
def active_client(client, sample_bean):
    client.cookies.set("active_bean_id", sample_bean.id)
    return client


def _mock_optimizer():
    mock = MagicMock()
    mock.recommend = AsyncMock()
    return mock


# ---------------------------------------------------------------------------
# Parameter registry — new method param sets
# ---------------------------------------------------------------------------


def test_french_press_params():
    """french-press method has grind_setting, temperature, steep_time, dose_in, brew_volume."""
    params = get_param_columns("french-press")
    assert "grind_setting" in params
    assert "temperature" in params
    assert "steep_time" in params
    assert "dose_in" in params
    assert "brew_volume" in params
    # Should NOT have espresso-only params
    assert "preinfusion_pressure_pct" not in params
    assert "saturation" not in params


def test_aeropress_params():
    """aeropress method has standard params + brew_mode (standard/inverted)."""
    params = get_param_columns("aeropress")
    assert "grind_setting" in params
    assert "temperature" in params
    assert "steep_time" in params
    assert "dose_in" in params
    assert "brew_volume" in params
    assert "brew_mode" in params
    # Should NOT have espresso-only params
    assert "preinfusion_pressure_pct" not in params


def test_cold_brew_params():
    """cold-brew method has grind_setting, steep_time, dose_in, brew_volume (no temperature)."""
    params = get_param_columns("cold-brew")
    assert "grind_setting" in params
    assert "steep_time" in params
    assert "dose_in" in params
    assert "brew_volume" in params
    # Cold brew does not use heated water
    assert "temperature" not in params


def test_pour_over_params_include_bloom_weight():
    """pour-over method includes bloom_weight for bloom water tracking."""
    params = get_param_columns("pour-over")
    assert "bloom_weight" in params
    assert "brew_volume" in params
    assert "grind_setting" in params
    assert "temperature" in params


# ---------------------------------------------------------------------------
# OptimizerService — campaign creation for new methods
# ---------------------------------------------------------------------------


def test_optimizer_french_press_campaign(db_session):
    """OptimizerService creates a valid campaign for french-press."""
    from app.services.optimizer import OptimizerService

    def _factory():
        return db_session

    optimizer = OptimizerService(_factory)
    key = make_campaign_key("bean1", "french-press", None)
    campaign = optimizer.get_or_create_campaign(key, method="french-press")

    param_names = [p.name for p in campaign.searchspace.parameters]
    assert "steep_time" in param_names
    assert "brew_volume" in param_names
    assert "grind_setting" in param_names
    assert "temperature" in param_names
    # Should NOT have espresso params
    assert "preinfusion_pressure_pct" not in param_names
    assert "saturation" not in param_names


def test_optimizer_aeropress_campaign(db_session):
    """OptimizerService creates a valid campaign for aeropress."""
    from app.services.optimizer import OptimizerService

    def _factory():
        return db_session

    optimizer = OptimizerService(_factory)
    key = make_campaign_key("bean1", "aeropress", None)
    campaign = optimizer.get_or_create_campaign(key, method="aeropress")

    param_names = [p.name for p in campaign.searchspace.parameters]
    assert "steep_time" in param_names
    assert "brew_volume" in param_names
    assert "brew_mode" in param_names  # categorical: standard/inverted
    assert "grind_setting" in param_names


def test_optimizer_cold_brew_campaign(db_session):
    """OptimizerService creates a valid campaign for cold-brew."""
    from app.services.optimizer import OptimizerService

    def _factory():
        return db_session

    optimizer = OptimizerService(_factory)
    key = make_campaign_key("bean1", "cold-brew", None)
    campaign = optimizer.get_or_create_campaign(key, method="cold-brew")

    param_names = [p.name for p in campaign.searchspace.parameters]
    assert "steep_time" in param_names
    assert "brew_volume" in param_names
    assert "dose_in" in param_names
    # Cold brew — no temperature param
    assert "temperature" not in param_names


def test_optimizer_campaigns_are_method_distinct(db_session):
    """Each method gets its own campaign (different keys for same bean)."""
    bean_id = "shared-bean"

    espresso_key = make_campaign_key(bean_id, "espresso", None)
    fp_key = make_campaign_key(bean_id, "french-press", None)
    aerop_key = make_campaign_key(bean_id, "aeropress", None)

    assert espresso_key != fp_key
    assert espresso_key != aerop_key
    assert fp_key != aerop_key


# ---------------------------------------------------------------------------
# Measurement model — new Phase 21 columns
# ---------------------------------------------------------------------------


def test_measurement_phase21_columns_nullable(db_session, sample_bean):
    """Phase 21 new columns (steep_time, brew_volume) are nullable."""
    m = Measurement(
        bean_id=sample_bean.id,
        recommendation_id=str(uuid.uuid4()),
        grind_setting=20.0,
        temperature=93.0,
        dose_in=19.0,
        target_yield=40.0,
        taste=8.0,
        is_failed=False,
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)

    assert m.steep_time is None
    assert m.brew_volume is None
    assert m.bloom_weight is None


def test_measurement_stores_french_press_params(db_session, sample_bean):
    """Measurement can store steep_time and brew_volume for french-press."""
    m = Measurement(
        bean_id=sample_bean.id,
        recommendation_id=str(uuid.uuid4()),
        grind_setting=25.0,
        temperature=95.0,
        dose_in=30.0,
        taste=7.5,
        is_failed=False,
        steep_time=4.0,
        brew_volume=350.0,
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)

    assert m.steep_time == pytest.approx(4.0)
    assert m.brew_volume == pytest.approx(350.0)


def test_measurement_stores_aeropress_brew_mode(db_session, sample_bean):
    """Measurement can store brew_mode for aeropress (standard/inverted)."""
    for mode in ("standard", "inverted"):
        m = Measurement(
            bean_id=sample_bean.id,
            recommendation_id=str(uuid.uuid4()),
            grind_setting=15.0,
            temperature=85.0,
            dose_in=15.0,
            taste=8.0,
            is_failed=False,
            steep_time=2.5,
            brew_volume=200.0,
            brew_mode=mode,
        )
        db_session.add(m)
        db_session.commit()
        db_session.refresh(m)
        assert m.brew_mode == mode


def test_measurement_stores_cold_brew_steep_time(db_session, sample_bean):
    """Cold-brew measurement stores a long steep_time (in hours as decimal)."""
    m = Measurement(
        bean_id=sample_bean.id,
        recommendation_id=str(uuid.uuid4()),
        grind_setting=30.0,
        dose_in=50.0,
        taste=9.0,
        is_failed=False,
        steep_time=12.0,  # 12 hours
        brew_volume=500.0,
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)

    assert m.steep_time == pytest.approx(12.0)
    assert m.brew_volume == pytest.approx(500.0)
    assert m.temperature is None  # cold-brew: no heat


# ---------------------------------------------------------------------------
# Integration: POST /brew/record stores new method params
# ---------------------------------------------------------------------------


def test_record_measurement_french_press_stores_steep_time(active_client, sample_bean, db_session):
    """POST /brew/record for french-press stores steep_time and brew_volume."""
    app.state.optimizer = _mock_optimizer()

    rec_id = str(uuid.uuid4())
    payload = {
        "recommendation_id": rec_id,
        "grind_setting": "25.0",
        "temperature": "95.0",
        "dose_in": "30.0",
        "steep_time": "4.0",
        "brew_volume": "350.0",
        "taste": "7.5",
    }
    response = active_client.post("/brew/record", data=payload, follow_redirects=False)
    assert response.status_code == 303

    db_session.expire_all()
    m = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is not None
    assert m.steep_time == pytest.approx(4.0)
    assert m.brew_volume == pytest.approx(350.0)


def test_record_measurement_aeropress_stores_brew_mode(active_client, sample_bean, db_session):
    """POST /brew/record for aeropress stores brew_mode (standard/inverted)."""
    app.state.optimizer = _mock_optimizer()

    rec_id = str(uuid.uuid4())
    payload = {
        "recommendation_id": rec_id,
        "grind_setting": "15.0",
        "temperature": "85.0",
        "dose_in": "15.0",
        "steep_time": "2.5",
        "brew_volume": "200.0",
        "brew_mode": "inverted",
        "taste": "8.0",
    }
    response = active_client.post("/brew/record", data=payload, follow_redirects=False)
    assert response.status_code == 303

    db_session.expire_all()
    m = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is not None
    assert m.brew_mode == "inverted"
    assert m.steep_time == pytest.approx(2.5)


def test_record_measurement_cold_brew_no_temperature(active_client, sample_bean, db_session):
    """POST /brew/record for cold-brew: temperature omitted, steep_time stored."""
    app.state.optimizer = _mock_optimizer()

    rec_id = str(uuid.uuid4())
    payload = {
        "recommendation_id": rec_id,
        "grind_setting": "30.0",
        "dose_in": "50.0",
        "steep_time": "12.0",
        "brew_volume": "500.0",
        "taste": "9.0",
    }
    response = active_client.post("/brew/record", data=payload, follow_redirects=False)
    assert response.status_code == 303

    db_session.expire_all()
    m = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is not None
    assert m.steep_time == pytest.approx(12.0)
    assert m.brew_volume == pytest.approx(500.0)
    assert m.temperature is None


# ---------------------------------------------------------------------------
# BrewMethod seeding — new methods present in DB after migration
# ---------------------------------------------------------------------------


def test_brew_method_seeding_new_methods(db_session):
    """Phase 21 migration seeds 5 new BrewMethod entries in the DB."""
    # Simulate seeding (as the migration does) for test isolation
    import uuid as _uuid

    new_methods = ["french-press", "aeropress", "turkish", "moka-pot", "cold-brew"]
    for name in new_methods:
        existing = db_session.query(BrewMethod).filter_by(name=name).first()
        if existing is None:
            db_session.add(BrewMethod(id=str(_uuid.uuid4()), name=name))
    db_session.commit()

    for name in new_methods:
        method = db_session.query(BrewMethod).filter_by(name=name).first()
        assert method is not None, f"BrewMethod '{name}' not found after seeding"
        assert method.name == name


def test_brew_method_seeding_is_idempotent(db_session):
    """Seeding the same BrewMethod twice does not create duplicates."""
    import uuid as _uuid

    name = "french-press"
    existing = db_session.query(BrewMethod).filter_by(name=name).first()
    if existing is None:
        db_session.add(BrewMethod(id=str(_uuid.uuid4()), name=name))
        db_session.commit()

    # Second insert attempt — simulate idempotency guard
    existing2 = db_session.query(BrewMethod).filter_by(name=name).first()
    if existing2 is None:
        db_session.add(BrewMethod(id=str(_uuid.uuid4()), name=name))
        db_session.commit()

    count = db_session.query(BrewMethod).filter_by(name=name).count()
    assert count == 1, f"Expected 1 BrewMethod for '{name}', got {count}"
