"""Integration tests for BayBE OptimizerService."""

from pathlib import Path

import pandas as pd
import pytest

from app.services.optimizer import OptimizerService, BAYBE_PARAM_COLUMNS


pytestmark = pytest.mark.slow


async def test_create_campaign(optimizer_service, tmp_campaigns_dir):
    """get_or_create_campaign creates and persists a campaign."""
    campaign = optimizer_service.get_or_create_campaign("test-bean")
    assert campaign is not None

    campaign_file = tmp_campaigns_dir / "test-bean.json"
    assert campaign_file.exists()


async def test_recommend_returns_all_params(optimizer_service):
    """recommend() returns all 6 params + recommendation_id within bounds."""
    rec = await optimizer_service.recommend("test-bean")

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
    rec = await optimizer_service.recommend("rounding-bean")

    assert rec["grind_setting"] % 0.5 == 0, f"grind not rounded: {rec['grind_setting']}"
    assert rec["temperature"] % 1.0 == 0, f"temp not rounded: {rec['temperature']}"
    assert rec["preinfusion_pct"] % 5.0 == 0, f"preinfusion not rounded: {rec['preinfusion_pct']}"
    assert rec["dose_in"] % 0.5 == 0, f"dose not rounded: {rec['dose_in']}"
    assert rec["target_yield"] % 1.0 == 0, f"yield not rounded: {rec['target_yield']}"


async def test_add_measurement_and_recommend_again(optimizer_service, tmp_campaigns_dir):
    """Full cycle: recommend -> add measurement -> recommend again."""
    rec1 = await optimizer_service.recommend("cycle-bean")

    # Add measurement with recommended params
    params = {k: rec1[k] for k in BAYBE_PARAM_COLUMNS}
    optimizer_service.add_measurement("cycle-bean", {**params, "taste": 7.5})

    # Second recommendation should work
    rec2 = await optimizer_service.recommend("cycle-bean")
    assert all(p in rec2 for p in BAYBE_PARAM_COLUMNS)

    # Campaign file was updated
    campaign_file = tmp_campaigns_dir / "cycle-bean.json"
    assert campaign_file.exists()


async def test_campaign_persistence_across_restart(optimizer_service, tmp_campaigns_dir):
    """Campaign state survives service restart (new instance, same dir)."""
    # Create campaign and add measurement
    rec = await optimizer_service.recommend("persist-bean")
    params = {k: rec[k] for k in BAYBE_PARAM_COLUMNS}
    optimizer_service.add_measurement("persist-bean", {**params, "taste": 8.0})

    # Create new service instance (simulates restart)
    new_service = OptimizerService(tmp_campaigns_dir)
    campaign = new_service.get_or_create_campaign("persist-bean")

    # Campaign should have the measurement
    assert len(campaign.measurements) > 0

    # Should be able to recommend
    rec2 = await new_service.recommend("persist-bean")
    assert all(p in rec2 for p in BAYBE_PARAM_COLUMNS)


async def test_campaign_file_size_hybrid(optimizer_service, tmp_campaigns_dir):
    """Hybrid campaign JSON is <500KB (vs 20MB with discrete)."""
    rec = await optimizer_service.recommend("size-bean")
    params = {k: rec[k] for k in BAYBE_PARAM_COLUMNS}
    optimizer_service.add_measurement("size-bean", {**params, "taste": 7.0})

    campaign_file = tmp_campaigns_dir / "size-bean.json"
    file_size = campaign_file.stat().st_size
    assert file_size < 500_000, f"Campaign file too large: {file_size} bytes"


async def test_rebuild_campaign(optimizer_service, tmp_campaigns_dir):
    """rebuild_campaign creates a fresh campaign from measurement data."""
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

    campaign = optimizer_service.rebuild_campaign("rebuild-bean", df)
    assert campaign is not None
    assert len(campaign.measurements) == 2

    # Should be able to recommend from rebuilt campaign
    rec = await optimizer_service.recommend("rebuild-bean")
    assert all(p in rec for p in BAYBE_PARAM_COLUMNS)
