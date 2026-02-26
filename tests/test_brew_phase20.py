"""Phase 20 tests: Espresso Parameter Evolution.

Covers:
  - New Phase 20 columns present and nullable on Measurement
  - record_measurement stores new espresso params (brew_pressure, flow_rate, etc.)
  - Legacy param (preinfusion_pressure_pct) stored on historical measurements (backward-compat reads)
  - Tier 1 active params exclude legacy preinfusion_pressure_pct / saturation
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.main import app
from app.models.bean import Bean
from app.models.measurement import Measurement
from app.services.parameter_registry import (
    get_default_bounds,
    get_legacy_param_columns,
    get_param_columns,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_bean(db_session):
    bean = Bean(name="Phase20 Bean", roaster="Test Roaster", origin="Colombia")
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
# Parameter registry — Phase 20 tier structure
# ---------------------------------------------------------------------------


def test_espresso_tier1_active_params():
    """Phase 20 Tier 1: 4 active params, no legacy ones."""
    params = get_param_columns("espresso")
    assert "grind_setting" in params
    assert "temperature" in params
    assert "dose_in" in params
    assert "target_yield" in params
    # Legacy excluded from new campaigns
    assert "preinfusion_pressure_pct" not in params
    assert "saturation" not in params


def test_espresso_legacy_params_identified():
    """get_legacy_param_columns returns preinfusion_pressure_pct and saturation for espresso."""
    legacy = get_legacy_param_columns("espresso")
    assert "preinfusion_pressure_pct" in legacy
    assert "saturation" in legacy


def test_espresso_tier2_with_timed_preinfusion_brewer():
    """Phase 20 Tier 2: brewer with timed preinfusion unlocks preinfusion_time."""
    brewer_mock = MagicMock()
    brewer_mock.preinfusion_type = "timed"
    params = get_param_columns("espresso", brewer=brewer_mock)
    assert "preinfusion_time" in params


def test_espresso_tier1_without_capable_brewer():
    """Phase 20 Tier 1 (basic brewer): preinfusion_time not included."""
    brewer_mock = MagicMock()
    brewer_mock.preinfusion_type = "none"
    params = get_param_columns("espresso", brewer=brewer_mock)
    assert "preinfusion_time" not in params


def test_espresso_default_bounds_include_new_params():
    """get_default_bounds includes Phase 20 params (preinfusion_time, brew_pressure, flow_rate)."""
    bounds = get_default_bounds("espresso")
    assert "preinfusion_time" in bounds
    assert "brew_pressure" in bounds
    assert "flow_rate" in bounds
    # Legacy param bounds still present (for backward compat display)
    assert "preinfusion_pressure_pct" in bounds


# ---------------------------------------------------------------------------
# Measurement model — new Phase 20 columns exist and are nullable
# ---------------------------------------------------------------------------


def test_measurement_phase20_columns_nullable(db_session, sample_bean):
    """Phase 20 new columns are nullable — can insert measurement without them."""
    m = Measurement(
        bean_id=sample_bean.id,
        recommendation_id=str(uuid.uuid4()),
        grind_setting=20.0,
        temperature=93.0,
        dose_in=19.0,
        target_yield=40.0,
        taste=8.0,
        is_failed=False,
        # Phase 20 new cols — all omitted (should default to None)
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)

    assert m.preinfusion_time is None
    assert m.preinfusion_pressure is None
    assert m.brew_pressure is None
    assert m.pressure_profile is None
    assert m.bloom_pause is None
    assert m.flow_rate is None
    assert m.temp_profile is None
    assert m.brew_mode is None


def test_measurement_stores_phase20_new_params(db_session, sample_bean):
    """Phase 20 new columns can be written and read back."""
    m = Measurement(
        bean_id=sample_bean.id,
        recommendation_id=str(uuid.uuid4()),
        grind_setting=20.0,
        temperature=93.0,
        dose_in=19.0,
        target_yield=40.0,
        taste=8.0,
        is_failed=False,
        brew_pressure=9.0,
        flow_rate=2.5,
        preinfusion_time=4.0,
        pressure_profile="flat",
        temp_profile="ramp_up",
        brew_mode="standard",
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)

    assert m.brew_pressure == pytest.approx(9.0)
    assert m.flow_rate == pytest.approx(2.5)
    assert m.preinfusion_time == pytest.approx(4.0)
    assert m.pressure_profile == "flat"
    assert m.temp_profile == "ramp_up"
    assert m.brew_mode == "standard"


def test_measurement_legacy_preinfusion_pressure_pct_nullable(db_session, sample_bean):
    """Phase 20: preinfusion_pressure_pct and saturation are nullable (relaxed NOT NULL)."""
    m = Measurement(
        bean_id=sample_bean.id,
        recommendation_id=str(uuid.uuid4()),
        grind_setting=20.0,
        temperature=93.0,
        dose_in=19.0,
        target_yield=40.0,
        taste=8.0,
        is_failed=False,
        preinfusion_pressure_pct=None,
        saturation=None,
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)

    assert m.preinfusion_pressure_pct is None
    assert m.saturation is None


# ---------------------------------------------------------------------------
# Integration: record_measurement stores Phase 20 params via POST /brew/record
# ---------------------------------------------------------------------------


def test_record_measurement_stores_brew_pressure(active_client, sample_bean, db_session):
    """POST /brew/record with brew_pressure saves it on the Measurement row."""
    app.state.optimizer = _mock_optimizer()

    rec_id = str(uuid.uuid4())
    payload = {
        "recommendation_id": rec_id,
        "grind_setting": "20.0",
        "temperature": "93.0",
        "dose_in": "19.0",
        "target_yield": "40.0",
        "brew_pressure": "9.0",
        "taste": "8.5",
    }
    response = active_client.post("/brew/record", data=payload, follow_redirects=False)
    assert response.status_code == 303

    db_session.expire_all()
    m = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is not None
    assert m.brew_pressure == pytest.approx(9.0)


def test_record_measurement_stores_flow_rate(active_client, sample_bean, db_session):
    """POST /brew/record with flow_rate saves it on the Measurement row."""
    app.state.optimizer = _mock_optimizer()

    rec_id = str(uuid.uuid4())
    payload = {
        "recommendation_id": rec_id,
        "grind_setting": "19.0",
        "temperature": "94.0",
        "dose_in": "18.5",
        "target_yield": "38.0",
        "flow_rate": "2.5",
        "taste": "7.0",
    }
    response = active_client.post("/brew/record", data=payload, follow_redirects=False)
    assert response.status_code == 303

    db_session.expire_all()
    m = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is not None
    assert m.flow_rate == pytest.approx(2.5)


def test_record_measurement_stores_preinfusion_time(active_client, sample_bean, db_session):
    """POST /brew/record with preinfusion_time saves it on the Measurement row."""
    app.state.optimizer = _mock_optimizer()

    rec_id = str(uuid.uuid4())
    payload = {
        "recommendation_id": rec_id,
        "grind_setting": "20.0",
        "temperature": "93.0",
        "dose_in": "19.0",
        "target_yield": "40.0",
        "preinfusion_time": "5.0",
        "taste": "8.0",
    }
    response = active_client.post("/brew/record", data=payload, follow_redirects=False)
    assert response.status_code == 303

    db_session.expire_all()
    m = db_session.query(Measurement).filter(Measurement.recommendation_id == rec_id).first()
    assert m is not None
    assert m.preinfusion_time == pytest.approx(5.0)
