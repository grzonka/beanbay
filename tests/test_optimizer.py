"""Integration tests for BayBE OptimizerService."""

import pandas as pd
import pytest

from app.models.campaign_state import CampaignState
from app.services.optimizer import (
    OptimizerService,
    _bounds_fingerprint,
    _param_set_fingerprint,
    _resolve_bounds,
)
from app.services.optimizer_key import make_campaign_key
from app.services.parameter_registry import get_default_bounds, get_param_columns

ESPRESSO_PARAMS = get_param_columns("espresso")
ESPRESSO_BOUNDS = get_default_bounds("espresso")


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
    """recommend() returns all Phase-20 Tier-1 params + recommendation_id within bounds."""
    key = make_campaign_key("test-bean", "espresso", None)
    rec = await optimizer_service.recommend(key)

    assert isinstance(rec, dict)
    for param in ESPRESSO_PARAMS:
        assert param in rec, f"Missing param: {param}"

    assert "recommendation_id" in rec
    assert rec["recommendation_id"]  # non-empty

    # Check bounds — Phase 20 Tier 1: grind_setting, temperature, dose_in, target_yield
    # preinfusion_pressure_pct and saturation are legacy params excluded from new campaigns
    assert 15.0 <= rec["grind_setting"] <= 25.0
    assert 86.0 <= rec["temperature"] <= 96.0
    assert 18.5 <= rec["dose_in"] <= 20.0
    assert 36.0 <= rec["target_yield"] <= 50.0


async def test_recommend_rounding(optimizer_service):
    """Recommendations are rounded to practical precision."""
    key = make_campaign_key("rounding-bean", "espresso", None)
    rec = await optimizer_service.recommend(key)

    assert rec["grind_setting"] % 0.5 == 0, f"grind not rounded: {rec['grind_setting']}"
    assert rec["temperature"] % 1.0 == 0, f"temp not rounded: {rec['temperature']}"
    assert rec["dose_in"] % 0.5 == 0, f"dose not rounded: {rec['dose_in']}"
    assert rec["target_yield"] % 1.0 == 0, f"yield not rounded: {rec['target_yield']}"
    # preinfusion_pressure_pct is a legacy param excluded from new Phase-20 campaigns


async def test_add_measurement_and_recommend_again(optimizer_service, db_session):
    """Full cycle: recommend -> add measurement -> recommend again."""
    key = make_campaign_key("cycle-bean", "espresso", None)
    rec1 = await optimizer_service.recommend(key)

    # Add measurement with recommended params
    params = {k: rec1[k] for k in ESPRESSO_PARAMS}
    optimizer_service.add_measurement(key, {**params, "taste": 7.5})

    # Second recommendation should work
    rec2 = await optimizer_service.recommend(key)
    assert all(p in rec2 for p in ESPRESSO_PARAMS)

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
    params = {k: rec[k] for k in ESPRESSO_PARAMS}
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
    assert all(p in rec2 for p in ESPRESSO_PARAMS)


async def test_campaign_json_size_hybrid(optimizer_service, db_session):
    """Hybrid campaign JSON is <500KB (vs 20MB with discrete)."""
    key = make_campaign_key("size-bean", "espresso", None)
    rec = await optimizer_service.recommend(key)
    params = {k: rec[k] for k in ESPRESSO_PARAMS}
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
            "preinfusion_pressure_pct": 75.0,
            "dose_in": 19.0,
            "target_yield": 40.0,
            "saturation": "yes",
            "taste": 7.0,
        },
        {
            "grind_setting": 21.0,
            "temperature": 94.0,
            "preinfusion_pressure_pct": 80.0,
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
    assert all(p in rec for p in ESPRESSO_PARAMS)


# --- Parameter override tests ---


def test_resolve_bounds_defaults():
    """_resolve_bounds with no overrides returns ESPRESSO_BOUNDS."""
    assert _resolve_bounds(None) == ESPRESSO_BOUNDS
    assert _resolve_bounds({}) == ESPRESSO_BOUNDS


def test_resolve_bounds_partial_override():
    """_resolve_bounds merges partial overrides onto defaults."""
    overrides = {"grind_setting": {"min": 18.0, "max": 22.0}}
    bounds = _resolve_bounds(overrides)
    assert bounds["grind_setting"] == (18.0, 22.0)
    # Other params unchanged
    assert bounds["temperature"] == ESPRESSO_BOUNDS["temperature"]
    assert bounds["dose_in"] == ESPRESSO_BOUNDS["dose_in"]


def test_resolve_bounds_partial_min_only():
    """_resolve_bounds can override just min, keeping default max."""
    overrides = {"temperature": {"min": 90.0}}
    bounds = _resolve_bounds(overrides)
    assert bounds["temperature"] == (90.0, 96.0)  # max stays default


def test_resolve_bounds_ignores_unknown_params():
    """_resolve_bounds ignores parameters not in ESPRESSO_BOUNDS."""
    overrides = {"unknown_param": {"min": 1.0, "max": 10.0}}
    bounds = _resolve_bounds(overrides)
    assert bounds == ESPRESSO_BOUNDS


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
    # Non-overridden Phase-20 Tier-1 params use defaults
    # preinfusion_pressure_pct and saturation are legacy params excluded from new campaigns
    assert 18.5 <= rec["dose_in"] <= 20.0
    assert 36.0 <= rec["target_yield"] <= 50.0


async def test_campaign_invalidation_on_override_change(optimizer_service):
    """Changing overrides rebuilds the campaign with new bounds."""
    key = make_campaign_key("invalidate-bean", "espresso", None)

    # Create campaign with default bounds and add a measurement
    rec1 = await optimizer_service.recommend(key)
    params = {k: rec1[k] for k in ESPRESSO_PARAMS}
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
            "preinfusion_pressure_pct": 75.0,
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
    params = {k: rec[k] for k in ESPRESSO_PARAMS}
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
    base_params = {k: rec[k] for k in ESPRESSO_PARAMS}
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
    for param in ESPRESSO_PARAMS:
        assert param in rec1

    # Add a measurement between calls
    params = {k: rec1[k] for k in ESPRESSO_PARAMS}
    optimizer_service.add_measurement(key, {**params, "taste": 7.0})

    # Second call must NOT raise NotImplementedError (BayBE cache guard bug)
    rec2 = await optimizer_service.recommend(key)
    assert isinstance(rec2, dict)
    for param in ESPRESSO_PARAMS:
        assert param in rec2
    assert "recommendation_id" in rec2


async def test_insights_bayesian_early_phase(optimizer_service):
    """With exactly 6 measurements (switch_after=5, so Bayesian), phase='bayesian_early', label='Learning'."""
    bean_id = "bayesian-early-bean"
    key = make_campaign_key(bean_id, "espresso", None)
    rec = await optimizer_service.recommend(key)

    # Add 6 measurements → shot_count=6, which is >= 5 (Bayesian mode) but < 8 (bayesian_early)
    base_params = {k: rec[k] for k in ESPRESSO_PARAMS}
    for taste in [6.0, 6.5, 7.0, 7.0, 7.5, 7.5]:
        optimizer_service.add_measurement(key, {**base_params, "taste": taste})

    rec2 = await optimizer_service.recommend(key)
    insights = optimizer_service.get_recommendation_insights(key, rec2)

    assert insights["phase"] == "bayesian_early"
    assert insights["phase_label"] == "Learning"
    assert "learning" in insights["explanation"].lower()
    assert insights["shot_count"] == 6


# --- _param_set_fingerprint tests ---


def test_param_set_fingerprint_stable():
    """Same method + brewer produces the same fingerprint."""
    fp1 = _param_set_fingerprint("espresso", None)
    fp2 = _param_set_fingerprint("espresso", None)
    assert fp1 == fp2
    assert len(fp1) == 16


def test_param_set_fingerprint_changes_with_brewer():
    """Different brewer capability configs produce different fingerprints."""

    class MockBrewer:
        """Minimal mock simulating a brewer with extra capability flags."""

        preinfusion_type = "timed"
        pressure_control_type = "none"
        flow_control_type = "none"
        temp_control_type = "fixed"
        has_bloom = False

    fp_no_brewer = _param_set_fingerprint("espresso", None)
    fp_with_brewer = _param_set_fingerprint("espresso", MockBrewer())
    # preinfusion_type=timed unlocks preinfusion_time → different param set
    assert fp_no_brewer != fp_with_brewer


def test_param_set_fingerprint_none_brewer_gives_tier1():
    """brewer=None gives only Tier 1 params (no capability-gated params)."""
    params = get_param_columns("espresso", None)
    # Tier 1 espresso: grind_setting, temperature, dose_in, target_yield
    assert set(params) == {"grind_setting", "temperature", "dose_in", "target_yield"}


# --- Campaign outdated detection tests ---


async def test_param_set_fingerprint_stored_on_creation(optimizer_service, db_session):
    """New campaigns store param_set_fingerprint in DB."""
    key = make_campaign_key("fp-store-bean", "espresso", None)
    optimizer_service.get_or_create_campaign(key)

    row = db_session.query(CampaignState).filter_by(campaign_key=key).first()
    assert row is not None
    assert row.param_set_fingerprint is not None
    assert row.param_set_fingerprint == _param_set_fingerprint("espresso", None)


async def test_is_campaign_outdated_returns_false_for_matching_brewer(
    optimizer_service, db_session
):
    """is_campaign_outdated returns False when brewer has same capabilities."""
    key = make_campaign_key("not-outdated-bean", "espresso", None)
    optimizer_service.get_or_create_campaign(key, brewer=None)

    result = optimizer_service.is_campaign_outdated(key, "espresso", None)
    assert result is False


async def test_is_campaign_outdated_returns_true_when_brewer_changes(optimizer_service, db_session):
    """is_campaign_outdated returns True when brewer unlocks new params."""

    class MockBrewerWithPreinfusion:
        preinfusion_type = "timed"
        pressure_control_type = "none"
        flow_control_type = "none"
        temp_control_type = "fixed"
        has_bloom = False

    key = make_campaign_key("outdated-bean", "espresso", None)
    # Create campaign with brewer=None (Tier 1 only)
    optimizer_service.get_or_create_campaign(key, brewer=None)

    # Now check with a brewer that has preinfusion (unlocks preinfusion_time)
    result = optimizer_service.is_campaign_outdated(key, "espresso", MockBrewerWithPreinfusion())
    assert result is True


async def test_is_campaign_outdated_false_for_no_stored_fingerprint(optimizer_service, db_session):
    """is_campaign_outdated returns False for legacy campaigns with no fingerprint."""
    key = make_campaign_key("legacy-bean", "espresso", None)
    # Create campaign without fingerprint (simulating legacy campaign)
    optimizer_service.get_or_create_campaign(key, brewer=None)

    # Manually clear the fingerprint to simulate legacy
    row = db_session.query(CampaignState).filter_by(campaign_key=key).first()
    row.param_set_fingerprint = None
    db_session.commit()
    # Clear the in-memory cache so it re-reads from DB
    optimizer_service._cache.pop(key, None)
    optimizer_service._fingerprints.pop(key, None)

    # Should not nag about outdated
    result = optimizer_service.is_campaign_outdated(key, "espresso", None)
    assert result is False


async def test_decline_rebuild_increments_counter(optimizer_service, db_session):
    """decline_rebuild increments the rebuild_declined counter (0→1→2)."""
    key = make_campaign_key("decline-bean", "espresso", None)
    optimizer_service.get_or_create_campaign(key, brewer=None)

    # Initially not declined
    assert not optimizer_service.was_rebuild_declined(key)

    # First decline: 0 → 1
    optimizer_service.decline_rebuild(key)
    row = db_session.query(CampaignState).filter_by(campaign_key=key).first()
    db_session.refresh(row)
    assert row.rebuild_declined == 1

    # was_rebuild_declined is False at level 1 (still shows reminder)
    assert not optimizer_service.was_rebuild_declined(key)

    # Second decline: 1 → 2 (permanently silenced)
    optimizer_service.decline_rebuild(key)
    row = db_session.query(CampaignState).filter_by(campaign_key=key).first()
    db_session.refresh(row)
    assert row.rebuild_declined == 2
    assert optimizer_service.was_rebuild_declined(key)


async def test_decline_rebuild_caps_at_2(optimizer_service, db_session):
    """decline_rebuild never exceeds 2 (calling more times is idempotent at 2)."""
    key = make_campaign_key("cap-decline-bean", "espresso", None)
    optimizer_service.get_or_create_campaign(key, brewer=None)

    for _ in range(5):
        optimizer_service.decline_rebuild(key)

    row = db_session.query(CampaignState).filter_by(campaign_key=key).first()
    db_session.refresh(row)
    assert row.rebuild_declined == 2


async def test_accept_rebuild_resets_declined_and_updates_fingerprint(
    optimizer_service, db_session
):
    """accept_rebuild rebuilds campaign, clears rebuild_declined, updates fingerprint."""
    key = make_campaign_key("accept-rebuild-bean", "espresso", None)

    # Create initial campaign (brewer=None, Tier 1)
    optimizer_service.get_or_create_campaign(key, brewer=None)

    # Decline once
    optimizer_service.decline_rebuild(key)
    row = db_session.query(CampaignState).filter_by(campaign_key=key).first()
    db_session.refresh(row)
    assert row.rebuild_declined == 1

    # Accept rebuild with same brewer (no param change, just resetting)
    new_campaign = optimizer_service.accept_rebuild(key, "espresso", None)
    assert new_campaign is not None

    # rebuild_declined should be reset to 0
    row = db_session.query(CampaignState).filter_by(campaign_key=key).first()
    db_session.refresh(row)
    assert row.rebuild_declined == 0

    # param_set_fingerprint should match current config
    assert row.param_set_fingerprint == _param_set_fingerprint("espresso", None)
