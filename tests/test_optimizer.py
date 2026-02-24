"""Integration tests for BayBE OptimizerService."""

import pandas as pd
import pytest

from app.models.campaign_state import CampaignState
from app.services.optimizer import (
    DEFAULT_BOUNDS,
    BAYBE_PARAM_COLUMNS,
    OptimizerService,
    _bounds_fingerprint,
    _resolve_bounds,
)
from app.services.optimizer_key import make_campaign_key


pytestmark = pytest.mark.slow


async def test_create_campaign(optimizer_service, db_session):
    """get_or_create_campaign creates and persists a campaign."""
    key = make_campaign_key("test-bean", "espresso", None)
    campaign = optimizer_service.get_or_create_campaign(key)
    assert campaign is not None

    # Verify persisted to DB
    row = (
        db_session.query(CampaignState).filter_by(campaign_key="test-bean__espresso__none").first()
    )
    assert row is not None
    assert row.campaign_json  # non-empty


async def test_recommend_returns_all_params(optimizer_service):
    """recommend() returns all 6 params + recommendation_id within bounds."""
    key = make_campaign_key("test-bean", "espresso", None)
    rec = await optimizer_service.recommend(key)

    assert isinstance(rec, dict)
    for param in BAYBE_PARAM_COLUMNS:
        assert param in rec, f"Missing param: {param}"

    assert "recommendation_id" in rec
    assert rec["recommendation_id"]  # non-empty

    # Check bounds
    assert 15.0 <= rec["grind_setting"] <= 25.0
    assert 86.0 <= rec["temperature"] <= 96.0
    assert 55.0 <= rec["preinfusion_pct"] <= 100.0
    assert 18.5 <= rec["dose_in"] <= 20.0
    assert 36.0 <= rec["target_yield"] <= 50.0
    assert rec["saturation"] in ("yes", "no")


async def test_recommend_rounding(optimizer_service):
    """Recommendations are rounded to practical precision."""
    key = make_campaign_key("rounding-bean", "espresso", None)
    rec = await optimizer_service.recommend(key)

    assert rec["grind_setting"] % 0.5 == 0, f"grind not rounded: {rec['grind_setting']}"
    assert rec["temperature"] % 1.0 == 0, f"temp not rounded: {rec['temperature']}"
    assert rec["preinfusion_pct"] % 5.0 == 0, f"preinfusion not rounded: {rec['preinfusion_pct']}"
    assert rec["dose_in"] % 0.5 == 0, f"dose not rounded: {rec['dose_in']}"
    assert rec["target_yield"] % 1.0 == 0, f"yield not rounded: {rec['target_yield']}"


async def test_add_measurement_and_recommend_again(optimizer_service, db_session):
    """Full cycle: recommend -> add measurement -> recommend again."""
    key = make_campaign_key("cycle-bean", "espresso", None)
    rec1 = await optimizer_service.recommend(key)

    # Add measurement with recommended params
    params = {k: rec1[k] for k in BAYBE_PARAM_COLUMNS}
    optimizer_service.add_measurement(key, {**params, "taste": 7.5})

    # Second recommendation should work
    rec2 = await optimizer_service.recommend(key)
    assert all(p in rec2 for p in BAYBE_PARAM_COLUMNS)

    # Campaign row was updated in DB
    row = (
        db_session.query(CampaignState).filter_by(campaign_key="cycle-bean__espresso__none").first()
    )
    assert row is not None
    assert row.campaign_json  # non-empty


async def test_campaign_persistence_across_restart(optimizer_service, db_session):
    """Campaign state survives service restart (new instance, same DB)."""
    key = make_campaign_key("persist-bean", "espresso", None)

    # Create campaign and add measurement
    rec = await optimizer_service.recommend(key)
    params = {k: rec[k] for k in BAYBE_PARAM_COLUMNS}
    optimizer_service.add_measurement(key, {**params, "taste": 8.0})

    # Create new service instance (simulates restart — empty cache, same DB)
    def _factory():
        return db_session

    new_service = OptimizerService(_factory)
    campaign = new_service.get_or_create_campaign(key)

    # Campaign should have the measurement
    assert len(campaign.measurements) > 0

    # Should be able to recommend
    rec2 = await new_service.recommend(key)
    assert all(p in rec2 for p in BAYBE_PARAM_COLUMNS)


async def test_campaign_json_size_hybrid(optimizer_service, db_session):
    """Hybrid campaign JSON is <500KB (vs 20MB with discrete)."""
    key = make_campaign_key("size-bean", "espresso", None)
    rec = await optimizer_service.recommend(key)
    params = {k: rec[k] for k in BAYBE_PARAM_COLUMNS}
    optimizer_service.add_measurement(key, {**params, "taste": 7.0})

    row = (
        db_session.query(CampaignState).filter_by(campaign_key="size-bean__espresso__none").first()
    )
    json_size = len(row.campaign_json)
    assert json_size < 500_000, f"Campaign JSON too large: {json_size} bytes"


async def test_rebuild_campaign(optimizer_service):
    """rebuild_campaign creates a fresh campaign from measurement data."""
    key = make_campaign_key("rebuild-bean", "espresso", None)

    # Add some measurements manually
    measurements = [
        {
            "grind_setting": 20.0,
            "temperature": 93.0,
            "preinfusion_pct": 75.0,
            "dose_in": 19.0,
            "target_yield": 40.0,
            "saturation": "yes",
            "taste": 7.0,
        },
        {
            "grind_setting": 21.0,
            "temperature": 94.0,
            "preinfusion_pct": 80.0,
            "dose_in": 19.5,
            "target_yield": 42.0,
            "saturation": "no",
            "taste": 8.5,
        },
    ]
    df = pd.DataFrame(measurements)

    campaign = optimizer_service.rebuild_campaign(key, df)
    assert campaign is not None
    assert len(campaign.measurements) == 2

    # Should be able to recommend from rebuilt campaign
    rec = await optimizer_service.recommend(key)
    assert all(p in rec for p in BAYBE_PARAM_COLUMNS)


# --- Parameter override tests ---


def test_resolve_bounds_defaults():
    """_resolve_bounds with no overrides returns DEFAULT_BOUNDS."""
    assert _resolve_bounds(None) == DEFAULT_BOUNDS
    assert _resolve_bounds({}) == DEFAULT_BOUNDS


def test_resolve_bounds_partial_override():
    """_resolve_bounds merges partial overrides onto defaults."""
    overrides = {"grind_setting": {"min": 18.0, "max": 22.0}}
    bounds = _resolve_bounds(overrides)
    assert bounds["grind_setting"] == (18.0, 22.0)
    # Other params unchanged
    assert bounds["temperature"] == DEFAULT_BOUNDS["temperature"]
    assert bounds["dose_in"] == DEFAULT_BOUNDS["dose_in"]


def test_resolve_bounds_partial_min_only():
    """_resolve_bounds can override just min, keeping default max."""
    overrides = {"temperature": {"min": 90.0}}
    bounds = _resolve_bounds(overrides)
    assert bounds["temperature"] == (90.0, 96.0)  # max stays default


def test_resolve_bounds_ignores_unknown_params():
    """_resolve_bounds ignores parameters not in DEFAULT_BOUNDS."""
    overrides = {"unknown_param": {"min": 1.0, "max": 10.0}}
    bounds = _resolve_bounds(overrides)
    assert bounds == DEFAULT_BOUNDS


def test_bounds_fingerprint_stable():
    """Same bounds produce the same fingerprint."""
    b1 = _resolve_bounds(None)
    b2 = _resolve_bounds({})
    assert _bounds_fingerprint(b1) == _bounds_fingerprint(b2)


def test_bounds_fingerprint_changes_with_overrides():
    """Different overrides produce different fingerprints."""
    fp_default = _bounds_fingerprint(_resolve_bounds(None))
    fp_custom = _bounds_fingerprint(_resolve_bounds({"grind_setting": {"min": 18.0, "max": 22.0}}))
    assert fp_default != fp_custom


async def test_recommend_with_overrides(optimizer_service):
    """Recommendations with custom bounds respect the narrowed range."""
    key = make_campaign_key("override-bean", "espresso", None)
    overrides = {
        "grind_setting": {"min": 20.0, "max": 22.0},
        "temperature": {"min": 92.0, "max": 94.0},
    }
    rec = await optimizer_service.recommend(key, overrides)

    assert 20.0 <= rec["grind_setting"] <= 22.0
    assert 92.0 <= rec["temperature"] <= 94.0
    # Non-overridden params use defaults
    assert 55.0 <= rec["preinfusion_pct"] <= 100.0
    assert 18.5 <= rec["dose_in"] <= 20.0
    assert 36.0 <= rec["target_yield"] <= 50.0
    assert rec["saturation"] in ("yes", "no")


async def test_campaign_invalidation_on_override_change(optimizer_service):
    """Changing overrides rebuilds the campaign with new bounds."""
    key = make_campaign_key("invalidate-bean", "espresso", None)

    # Create campaign with default bounds and add a measurement
    rec1 = await optimizer_service.recommend(key)
    params = {k: rec1[k] for k in BAYBE_PARAM_COLUMNS}
    optimizer_service.add_measurement(key, {**params, "taste": 7.0})

    campaign_before = optimizer_service.get_or_create_campaign(key)
    assert len(campaign_before.measurements) == 1

    # Now change overrides — campaign should rebuild with measurements preserved
    new_overrides = {"grind_setting": {"min": 20.0, "max": 22.0}}
    campaign_after = optimizer_service.get_or_create_campaign(key, new_overrides)

    # Measurements should be preserved after rebuild
    assert len(campaign_after.measurements) == 1

    # New recommendation should respect new bounds
    rec2 = await optimizer_service.recommend(key, new_overrides)
    assert 20.0 <= rec2["grind_setting"] <= 22.0


async def test_rebuild_campaign_with_overrides(optimizer_service):
    """rebuild_campaign respects custom overrides."""
    key = make_campaign_key("rebuild-override-bean", "espresso", None)
    overrides = {"temperature": {"min": 90.0, "max": 92.0}}
    measurements = [
        {
            "grind_setting": 20.0,
            "temperature": 91.0,
            "preinfusion_pct": 75.0,
            "dose_in": 19.0,
            "target_yield": 40.0,
            "saturation": "yes",
            "taste": 7.0,
        },
    ]
    df = pd.DataFrame(measurements)
    campaign = optimizer_service.rebuild_campaign(key, df, overrides)
    assert len(campaign.measurements) == 1

    rec = await optimizer_service.recommend(key, overrides)
    assert 90.0 <= rec["temperature"] <= 92.0


# --- get_recommendation_insights tests ---


async def test_insights_random_phase(optimizer_service):
    """Fresh campaign (no measurements) returns phase='random' with no predictions."""
    key = make_campaign_key("insights-random-bean", "espresso", None)
    rec = await optimizer_service.recommend(key)
    insights = optimizer_service.get_recommendation_insights(key, rec)

    assert insights["phase"] == "random"
    assert insights["phase_label"] == "Random exploration"
    assert "Exploring randomly" in insights["explanation"]
    assert insights["predicted_mean"] is None
    assert insights["predicted_std"] is None
    assert insights["predicted_range"] is None
    assert insights["shot_count"] == 0


async def test_insights_bayesian_phase(optimizer_service):
    """After 5+ measurements (switch_after=5), insights return phase='bayesian_early' with predictions."""
    key = make_campaign_key("insights-bayesian-bean", "espresso", None)

    # Get a recommendation first to establish the bean
    rec = await optimizer_service.recommend(key)

    # Add 5 measurements so campaign switches to Bayesian phase
    params = {k: rec[k] for k in BAYBE_PARAM_COLUMNS}
    for taste in [6.0, 7.0, 7.5, 8.0, 8.5]:
        optimizer_service.add_measurement(key, {**params, "taste": taste})

    rec2 = await optimizer_service.recommend(key)
    insights = optimizer_service.get_recommendation_insights(key, rec2)

    # With switch_after=5 and 5 measurements, we're in Bayesian mode
    # shot_count=5 < 8, so phase is bayesian_early
    assert insights["phase"] == "bayesian_early"
    assert insights["phase_label"] == "Learning"
    assert insights["shot_count"] == 5
    assert insights["predicted_mean"] is not None
    assert insights["predicted_std"] is not None
    assert insights["predicted_range"] is not None
    # Range string should contain the em dash separator
    assert "\u2013" in insights["predicted_range"]


async def test_insights_with_improvement(optimizer_service):
    """When latest shots show improvement and shot_count>=8, phase='bayesian' explanation mentions 'Zeroing in'."""
    bean_id = "insights-improve-bean"
    key = make_campaign_key(bean_id, "espresso", None)
    rec = await optimizer_service.recommend(key)

    # Add 9 measurements — early ones low taste, last 3 higher (shows improvement)
    # 9 shots → shot_count=9 >= 8 → phase="bayesian"
    base_params = {k: rec[k] for k in BAYBE_PARAM_COLUMNS}
    for taste in [5.0, 6.0, 5.5, 6.0, 5.5, 6.0, 7.0, 8.0, 8.5]:
        optimizer_service.add_measurement(key, {**base_params, "taste": taste})

    rec2 = await optimizer_service.recommend(key)
    insights = optimizer_service.get_recommendation_insights(key, rec2)

    assert insights["phase"] == "bayesian"
    assert insights["shot_count"] == 9
    # Last 3 best (8.0, 8.5) improved over previous best (max of first 6: 6.0)
    assert "Zeroing in" in insights["explanation"] or "improving" in insights["explanation"]


async def test_recommend_no_crash_on_second_call(optimizer_service):
    """recommend() twice for the same bean (with measurement in between) must not crash."""
    bean_id = "no-crash-bean"
    key = make_campaign_key(bean_id, "espresso", None)

    # First call
    rec1 = await optimizer_service.recommend(key)
    assert isinstance(rec1, dict)
    for param in BAYBE_PARAM_COLUMNS:
        assert param in rec1

    # Add a measurement between calls
    params = {k: rec1[k] for k in BAYBE_PARAM_COLUMNS}
    optimizer_service.add_measurement(key, {**params, "taste": 7.0})

    # Second call must NOT raise NotImplementedError (BayBE cache guard bug)
    rec2 = await optimizer_service.recommend(key)
    assert isinstance(rec2, dict)
    for param in BAYBE_PARAM_COLUMNS:
        assert param in rec2
    assert "recommendation_id" in rec2


async def test_insights_bayesian_early_phase(optimizer_service):
    """With exactly 6 measurements (switch_after=5, so Bayesian), phase='bayesian_early', label='Learning'."""
    bean_id = "bayesian-early-bean"
    key = make_campaign_key(bean_id, "espresso", None)
    rec = await optimizer_service.recommend(key)

    # Add 6 measurements → shot_count=6, which is >= 5 (Bayesian mode) but < 8 (bayesian_early)
    base_params = {k: rec[k] for k in BAYBE_PARAM_COLUMNS}
    for taste in [6.0, 6.5, 7.0, 7.0, 7.5, 7.5]:
        optimizer_service.add_measurement(key, {**base_params, "taste": taste})

    rec2 = await optimizer_service.recommend(key)
    insights = optimizer_service.get_recommendation_insights(key, rec2)

    assert insights["phase"] == "bayesian_early"
    assert insights["phase_label"] == "Learning"
    assert "learning" in insights["explanation"].lower()
    assert insights["shot_count"] == 6
